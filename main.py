from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from websocket.connection_manager import ConnectionManager
from models.vehicle_detector import VehicleDetector
from models.plate_reader import PlateReader
from dotenv import load_dotenv
import os
import uvicorn

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Smart Parking API")

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
manager = ConnectionManager()
vehicle_detector = VehicleDetector()
plate_reader = PlateReader()


@app.get("/")
async def root():
    return {"message": "Smart Parking API is running"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "smart-parking-backend"}


@app.post("/api/detect-vehicle")
async def detect_vehicle(file: UploadFile = File(...)):
    """Detect vehicles in uploaded image"""
    contents = await file.read()
    result = vehicle_detector.detect(contents)
    return result


@app.post("/api/read-plate")
async def read_plate(file: UploadFile = File(...)):
    """Read license plate from uploaded image"""
    contents = await file.read()
    result = plate_reader.read(contents)
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now, will handle real messages later
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
