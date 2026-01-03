# Smart Parking - Python Backend

AI/ML processing and WebSocket server for real-time parking management.

## Features
- Vehicle detection using YOLOv8
- License plate recognition using EasyOCR
- WebSocket server for real-time updates
- Camera feed processing

## Setup

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python main.py
```

Server will start at `http://localhost:8000`

## API Endpoints

- `GET /` - Root endpoint
- `GET /api/health` - Health check
- `POST /api/detect-vehicle` - Detect vehicles in image
- `POST /api/read-plate` - Read license plate from image
- `WS /ws` - WebSocket connection for real-time updates

## Testing

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).
