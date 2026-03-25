# AI Smart Parking — Backend

FastAPI service for license plate detection, parking slot occupancy, and real-time WebSockets. Event routing (dedupe, capacity aggregation, Next.js webhooks) runs in-process in `ai_event_pipeline.py` — no Pathway dependency.

## Stack

- FastAPI, WebSockets (`/ws/gate-monitor`, `/ws/lot-monitor`)
- Roboflow / EasyOCR / OpenCV for detection
- HTTP webhooks to Next.js: `POST /api/ai/webhook/entry|exit|capacity` with header `X-AI-Secret`

## Layout

```
ai-work/
├── main.py
├── ai_event_pipeline.py
├── connectors/nextjs_output.py
├── config/settings.py
├── models/
└── requirements.txt
```

## Run (no Docker)

```bash
cd ai-work
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env   # edit AI_* and Roboflow keys
python main.py
```

Server: `AI_BACKEND_HOST` / `AI_BACKEND_PORT` (default `0.0.0.0:8000`).

## Env sync with Next.js

- Set `AI_WEBHOOK_SECRET` here and in `next.js-work/.env.local` (same value).
- Set `NEXTJS_API_URL` to your Next.js origin so webhooks hit the right host.
- Default webhook paths use `/api/ai/webhook/...` (see `.env.example`).

Use **`AI_*` variables** in `.env` (e.g. `AI_BACKEND_HOST`, `AI_WEBHOOK_SECRET`) — see `.env.example`.
