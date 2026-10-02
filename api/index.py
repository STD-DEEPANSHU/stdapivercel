import os
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(
    title="StdAPI Vercel Master Gateway",
    description="Permanent Vercel Gateway routing traffic dynamically to Heroku stdapibackend and microservices.",
    version="1.0.0"
)

# Global CORS for all web apps & bots
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upstream Backend URL (Set in Vercel Environment Variables: STDAPIBACKEND_URL)
# If Heroku URL changes, only change it in Vercel dashboard!
DEFAULT_BACKEND = "https://stdapi-12b4906a1ffd.herokuapp.com"
BACKEND_URL = os.getenv("STDAPIBACKEND_URL", DEFAULT_BACKEND).rstrip("/")

# Client with connection pooling
timeout_config = httpx.Timeout(connect=10.0, read=45.0, write=45.0, pool=10.0)


@app.get("/")
async def gateway_status():
    """Permanent gateway index showing routing target."""
    return {
        "gateway": "stdapivercel",
        "status": "online",
        "version": "1.0.0",
        "author": "STD DEEPANSHU",
        "network": "TeamStdNetwork",
        "upstream_backend": BACKEND_URL,
        "docs": f"{BACKEND_URL}/docs",
        "info": "This gateway permanently routes to stdapibackend. Change STDAPIBACKEND_URL in Vercel settings without modifying client code."
    }


@app.get("/health")
async def health_check():
    """Check connectivity to the upstream Heroku backend."""
    try:
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            resp = await client.get(f"{BACKEND_URL}/health")
            return {
                "gateway": "online",
                "upstream_status": resp.status_code,
                "upstream_target": BACKEND_URL,
                "upstream_healthy": resp.status_code == 200
            }
    except Exception as e:
        return {
            "gateway": "online",
            "upstream_status": "unreachable",
            "upstream_target": BACKEND_URL,
            "error": str(e),
            "hint": "Heroku dyno might be sleeping or waking up."
        }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def reverse_proxy(request: Request, path: str):
    """
    Transparent Reverse Proxy forwarding every request, parameter,
    header, and body payload directly to the upstream stdapibackend on Heroku.
    """
    from urllib.parse import urlencode

    # Extract original path captured by Vercel rewrite (__vpath=$1)
    vpath = request.query_params.get("__vpath")
    if vpath is not None:
        clean_path = vpath.lstrip("/")
    else:
        clean_path = path.lstrip("/")
        orig_header = request.headers.get("x-matched-path") or request.headers.get("x-forwarded-uri")
        if orig_header and orig_header not in ("/api/index", "/api/index.py"):
            clean_path = orig_header.lstrip("/")

        if clean_path in ("api/index", "api/index.py", "api"):
            clean_path = ""
        elif clean_path.startswith("api/index/"):
            clean_path = clean_path[len("api/index/"):]
        elif clean_path.startswith("api/index.py/"):
            clean_path = clean_path[len("api/index.py/"):]

    # Remove internal __vpath from forwarded query parameters
    forward_params = dict(request.query_params)
    forward_params.pop("__vpath", None)
    query_str = urlencode(forward_params) if forward_params else ""

    target_url = f"{BACKEND_URL}/{clean_path}"
    if query_str:
        target_url = f"{target_url}?{query_str}"

    # Extract headers (excluding hop-by-hop headers)
    excluded_headers = {"host", "content-length", "connection"}
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in excluded_headers
    }
    forward_headers["X-Forwarded-Host"] = request.headers.get("host", "stdapivercel.vercel.app")
    forward_headers["X-Gateway-Proxy"] = "stdapivercel-v1"

    # Read body for POST/PUT/PATCH
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=False) as client:
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body if body else None
            )
            # Read full upstream response before context manager closes
            content = await upstream_resp.aread()

            # Strip upstream hop-by-hop headers
            response_headers = {
                k: v for k, v in upstream_resp.headers.items()
                if k.lower() not in {"content-encoding", "transfer-encoding", "connection", "content-length"}
            }

            return Response(
                content=content,
                status_code=upstream_resp.status_code,
                headers=response_headers,
                media_type=upstream_resp.headers.get("content-type")
            )

    except httpx.ConnectTimeout:
        return JSONResponse(
            status_code=504,
            content={
                "error": "Upstream Gateway Timeout",
                "message": "The upstream Heroku backend is taking too long to respond or is waking up.",
                "upstream": BACKEND_URL
            }
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=502,
            content={
                "error": "Bad Gateway",
                "message": "Cannot establish connection to upstream backend. Please verify STDAPIBACKEND_URL in Vercel environment variables.",
                "upstream": BACKEND_URL
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Proxy Error",
                "details": str(e),
                "upstream": BACKEND_URL
            }
        )
