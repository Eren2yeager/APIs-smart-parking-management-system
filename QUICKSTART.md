# Quick start — AI backend

## 1. Configure `.env`

Copy `.env.example` to `.env` in this folder. Set at least:

- `ROBOFLOW_*` keys for models
- `NEXTJS_API_URL` (e.g. `http://localhost:3000`)
- `AI_WEBHOOK_SECRET` — must match `AI_WEBHOOK_SECRET` in `next.js-work/.env.local`

## 2. Install and run

```bash
cd ai-work
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Listen on port **8000** by default (`AI_BACKEND_PORT`).

## 3. Connect Next.js

In `next.js-work/.env.local` use:

- `NEXT_PUBLIC_AI_BACKEND_URL=http://localhost:8000`
- `NEXT_PUBLIC_AI_BACKEND_WS_URL=ws://localhost:8000`
- Same `AI_WEBHOOK_SECRET` as this backend

## Troubleshooting

| Issue | Check |
|--------|--------|
| Webhook 401 | `X-AI-Secret` header and `AI_WEBHOOK_SECRET` match on both sides |
| Cannot reach Next.js | `NEXTJS_API_URL` is the URL the backend uses to POST webhooks |
