# ⚡ StdAPI Vercel — Permanent Master Gateway

Permanent Vercel Serverless Gateway for the **StdAPI** ecosystem.

## 🚀 Purpose

1. **Permanent Base URL for PyPI Package (`stdapi`):**
   - The `stdapi` Python package (and bots) will connect to `https://stdapivercel.vercel.app` (or your custom domain).
   - The package code NEVER needs to change.

2. **Zero-Downtime Backend Swapping:**
   - This gateway forwards all incoming traffic to `STDAPIBACKEND_URL` on Heroku.
   - If your Heroku URL changes, or if you migrate from Heroku to Render/Koyeb/VPS:
     - Just update `STDAPIBACKEND_URL` in the Vercel Dashboard!
     - 0 code changes in `stdapi`. 0 PyPI version releases needed.

## 🛠️ Deploy to Vercel (1-Click)

1. Push this folder to GitHub: `STD-DEEPANSHU/stdapivercel`.
2. Import repository into **Vercel**.
3. Under **Project Settings ➔ Environment Variables**, add:
   - `STDAPIBACKEND_URL` = `https://your-heroku-backend.herokuapp.com`
4. Click **Deploy**!

## 🧪 Local Testing

```bash
uvicorn api.index:app --reload --port 8000
```
