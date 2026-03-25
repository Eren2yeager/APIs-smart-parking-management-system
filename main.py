<<<<<<< HEAD
"""
AI Smart Parking Management System — main entry for the AI/ML processing layer.
"""

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
from typing import Dict, List
import base64
import cv2
import numpy as np
import json

from config.settings import settings
from utils.logger import logger
from utils.frame_processor import FrameProcessor
from models.license_plate_detector import LicensePlateDetectorModel
from models.parking_slot_detector import ParkingSlotDetectorModel
from models.vehicle_detector import VehicleDetectorModel
from schemas.camera_frame import CameraFrameSchema, FrameType
from schemas.detection_result import DetectionResult

from ai_event_pipeline import get_ai_event_pipeline

# Global model instances
license_plate_detector = None
parking_slot_detector = None
vehicle_detector = None
frame_processor = FrameProcessor()

# AI event pipeline (webhooks, dedupe, capacity aggregation)
ai_event_pipeline = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info(f"Client connected to {channel}")
    
    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            try:
                self.active_connections[channel].remove(websocket)
            except ValueError:
                pass
        logger.info(f"Client disconnected from {channel}")
    
    async def broadcast(self, message: dict, channel: str):
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    @staticmethod
    async def safe_send(websocket: WebSocket, message: dict) -> bool:
        """Send JSON to websocket only if still connected. Return True if sent."""
        try:
            if websocket.client_state.name != "CONNECTED":
                return False
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.debug(f"WebSocket send failed (client may have disconnected): {e}")
            return False

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    # Startup
    global license_plate_detector, parking_slot_detector, vehicle_detector, ai_event_pipeline

    logger.info("Starting AI Smart Parking System...")
    logger.info(f"Host: {settings.ai_backend_host}:{settings.ai_backend_port}")
    
    # Initialize AI models
    try:
        logger.info("Loading AI models...")
        license_plate_detector = LicensePlateDetectorModel()
        parking_slot_detector = ParkingSlotDetectorModel()
        vehicle_detector = VehicleDetectorModel()
        logger.info("Models initialization complete!")
        
        # Check which models are available
        models_status = []
        if license_plate_detector and hasattr(license_plate_detector, 'detection_model') and license_plate_detector.detection_model:
            models_status.append("✓ License Plate Detector")
        else:
            models_status.append("✗ License Plate Detector (unavailable)")
            
        if parking_slot_detector and hasattr(parking_slot_detector, 'detection_model') and parking_slot_detector.detection_model:
            models_status.append("✓ Parking Slot Detector")
        else:
            models_status.append("✗ Parking Slot Detector (unavailable)")
            
        models_status.append("✓ Vehicle Detector (placeholder)")
        
        for status in models_status:
            logger.info(status)
            
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        logger.warning("Server will start but some features may not work")
        # Don't raise - allow server to start anyway
    
    try:
        logger.info("Initializing AI event pipeline...")
        ai_event_pipeline = get_ai_event_pipeline()
        ai_event_pipeline.start()
        logger.info("✓ AI event pipeline started")
    except Exception as e:
        logger.error(f"Failed to start AI event pipeline: {e}")
        logger.warning("Continuing without AI event routing")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Smart Parking System...")
    if ai_event_pipeline:
        ai_event_pipeline.stop()


# Create FastAPI app
app = FastAPI(
    title="AI Smart Parking System",
    description="AI/ML processing layer for smart parking management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware — restrict to configured Next.js origin
_cors_origins = [
    settings.nextjs_api_url.rstrip("/"),
]
if settings.nextjs_api_url != "http://localhost:3000":
    _cors_origins.append("http://localhost:3000")  # always allow localhost for dev

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
=======
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from websocket.connection_manager import ConnectionManager
from models.license_plate import PlateRecognitionPipeline
from models.license_plate.stream_processor import PlateStreamProcessor
from models.parking_space_detector import ParkingSlotDetector
from models.parking_space_detector.stream_processor import ParkingStreamProcessor
from utils.frame_utils import base64_to_bytes
from utils.config import Config
import uvicorn
import json

app = FastAPI(title="Smart Parking API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
>>>>>>> main
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD

@app.get("/api/health")
async def health_check():
    """Health check endpoint - for Next.js and load balancers"""
    gate_count = len(manager.active_connections.get("gate-monitor", []))
    lot_count = len(manager.active_connections.get("lot-monitor", []))
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "backend": "ai",
        "models": {
            "license_plate": license_plate_detector is not None,
            "parking_slot": parking_slot_detector is not None,
            "vehicle": vehicle_detector is not None
        },
        "active_streams": gate_count + lot_count,
        "gate_monitor_connections": gate_count,
        "lot_monitor_connections": lot_count,
    }
=======
# Initialize managers (lazy loading to avoid double init with reload=True)
manager = ConnectionManager()
plate_pipeline = None
parking_detector = None


def get_plate_pipeline():
    global plate_pipeline
    if plate_pipeline is None:
        plate_pipeline = PlateRecognitionPipeline()
    return plate_pipeline


def get_parking_detector():
    global parking_detector
    if parking_detector is None:
        parking_detector = ParkingSlotDetector()
    return parking_detector



@app.get("/")
async def root():
    return {"message": "Smart Parking API is running"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "smart-parking-backend"}
>>>>>>> main


@app.post("/api/recognize-plate")
async def recognize_plate(file: UploadFile = File(...)):
<<<<<<< HEAD
    """
    Detect and recognize license plates in uploaded image
    Compatible with existing python-work API
    """
    try:
        # Read image
        image_bytes = await file.read()
        image = frame_processor.decode_base64_image(
            base64.b64encode(image_bytes).decode('utf-8')
        )
        
        # Detect and recognize plates
        detections = license_plate_detector.detect_and_recognize(
            image,
            camera_id="upload",
            parking_lot_id="unknown"
        )
        
        # Format response to match python-work format
        plates = []
        for detection in detections:
            plates.append({
                "plate_number": detection.plate_number,
                "confidence": detection.confidence,
                "bbox": {
                    "x1": detection.bbox.x1,
                    "y1": detection.bbox.y1,
                    "x2": detection.bbox.x2,
                    "y2": detection.bbox.y2
                }
            })
        
        return {
            "success": True,
            "plates_detected": len(plates),
            "plates_recognized": len(plates),
            "plates": plates
        }
    
    except Exception as e:
        logger.error(f"License plate recognition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
=======
    """Recognize license plate using two-stage pipeline"""
    contents = await file.read()
    pipeline = get_plate_pipeline()
    result = pipeline.process(contents)
    return result
>>>>>>> main


@app.post("/api/detect-parking-slots")
async def detect_parking_slots(file: UploadFile = File(...)):
    """
<<<<<<< HEAD
    Detect parking slot occupancy in uploaded image
    Compatible with existing python-work API
    """
    try:
        # Read image
        image_bytes = await file.read()
        image = frame_processor.decode_base64_image(
            base64.b64encode(image_bytes).decode('utf-8')
        )
        
        # Detect parking slots
        result = parking_slot_detector.detect_slots(
            image,
            camera_id="upload",
            parking_lot_id="unknown"
        )
        
        # Format response to match python-work format
        slots = []
        for slot in result.slots:
            slots.append({
                "slot_id": slot.slot_id,
                "status": slot.status,
                "confidence": slot.confidence,
                "bbox": {
                    "x1": slot.bbox.x1,
                    "y1": slot.bbox.y1,
                    "x2": slot.bbox.x2,
                    "y2": slot.bbox.y2
                }
            })
        
        return {
            "success": True,
            "total_slots": result.total_slots,
            "occupied": result.occupied,
            "empty": result.empty,
            "occupancy_rate": result.occupancy_rate,
            "slots": slots
        }
    
    except Exception as e:
        logger.error(f"Parking slot detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/gate-monitor")
async def gate_monitor_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time license plate detection.
    Expects: { data: base64_image, parking_lot_id or parkingLotId or gate_id, camera_id or gate_id, optional event_type: "entry"|"exit" }
    """
    await manager.connect(websocket, "gate-monitor")
    logger.info("[GATE] Client connected to /ws/gate-monitor")
    frame_count = 0  # frame skip counter
    
    try:
        while True:
            data = await websocket.receive_json()
            image_data = data.get("data") or data.get("image", "")
            if not image_data:
                logger.warning("[GATE] Frame skipped: no 'data' or 'image' in payload")
                continue
            
            # Frame skip: only process every Nth frame
            frame_count += 1
            if frame_count % settings.gate_frame_skip != 0:
                continue
            
            try:
                image = frame_processor.decode_base64_image(image_data)
                camera_id = (data.get("camera_id") or data.get("gate_id") or data.get("lot_id") or "unknown")
                parking_lot_id = (data.get("parking_lot_id") or data.get("parkingLotId") or data.get("gate_id") or data.get("lot_id") or "unknown")
                event_type = data.get("event_type", "entry")
                logger.debug(f"[GATE] Frame received (#{frame_count}): lot={parking_lot_id}, camera={camera_id}, event_type={event_type}, image_len={len(image_data)}")
                
                detections = license_plate_detector.detect_and_recognize(
                    image,
                    camera_id=camera_id,
                    parking_lot_id=parking_lot_id
                )
                
                if ai_event_pipeline and detections:
                    for detection in detections:
                        ai_event_pipeline.add_vehicle_detection(
                            plate_number=detection.plate_number,
                            parking_lot_id=parking_lot_id,
                            camera_id=camera_id,
                            event_type=event_type,
                            confidence=detection.confidence,
                            timestamp=int(detection.timestamp.timestamp() * 1000)
                        )
                    logger.info(f"[GATE] Pipeline fed {len(detections)} plate(s) for lot={parking_lot_id}, event_type={event_type}")
                
                for detection in detections:
                    await manager.safe_send(websocket, {
                        "event_type": "plate_detected",
                        "plate_number": detection.plate_number,
                        "confidence": detection.confidence,
                        "timestamp": detection.timestamp.isoformat(),
                        "parking_lot_id": parking_lot_id,
                        "camera_id": camera_id,
                        "bbox": {
                            "x1": detection.bbox.x1,
                            "y1": detection.bbox.y1,
                            "x2": detection.bbox.x2,
                            "y2": detection.bbox.y2
                        }
                    })
                        
            except Exception as decode_error:
                logger.error(f"[GATE] Frame processing error: {decode_error}")
                await manager.safe_send(websocket, {"event_type": "error", "error": str(decode_error)})
    
    except WebSocketDisconnect:
        logger.info("[GATE] Client disconnected from gate-monitor")
        manager.disconnect(websocket, "gate-monitor")
    except Exception as e:
        logger.error(f"[GATE] WebSocket error: {e}")
        manager.disconnect(websocket, "gate-monitor")


@app.websocket("/ws/lot-monitor")
async def lot_monitor_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time parking capacity monitoring.
    Expects: { data: base64_image, parking_lot_id or parkingLotId or lot_id, camera_id or lot_id }
    """
    await manager.connect(websocket, "lot-monitor")
    logger.info("[LOT] Client connected to /ws/lot-monitor")
    frame_count = 0  # frame skip counter
    
    try:
        while True:
            data = await websocket.receive_json()
            image_data = data.get("data") or data.get("image", "")
            if not image_data:
                logger.warning("[LOT] Frame skipped: no 'data' or 'image' in payload")
                continue
            
            # Frame skip: only process every Nth frame
            frame_count += 1
            if frame_count % settings.lot_frame_skip != 0:
                continue
            
            try:
                image = frame_processor.decode_base64_image(image_data)
                camera_id = (data.get("camera_id") or data.get("gate_id") or data.get("lot_id") or "unknown")
                parking_lot_id = (data.get("parking_lot_id") or data.get("parkingLotId") or data.get("lot_id") or "unknown")
                logger.debug(f"[LOT] Frame received (#{frame_count}): lot={parking_lot_id}, camera={camera_id}, image_len={len(image_data)}")
                
                result = parking_slot_detector.detect_slots(
                    image,
                    camera_id=camera_id,
                    parking_lot_id=parking_lot_id
                )
                
                if ai_event_pipeline and result.slots:
                    timestamp = int(result.timestamp.timestamp() * 1000)
                    for slot in result.slots:
                        ai_event_pipeline.add_capacity_update(
                            parking_lot_id=parking_lot_id,
                            camera_id=camera_id,
                            slot_id=slot.slot_id,
                            status=slot.status,
                            confidence=slot.confidence,
                            timestamp=timestamp
                        )
                    logger.info(f"[LOT] Pipeline fed {len(result.slots)} slot(s) for lot={parking_lot_id}, occupied={result.occupied}/{result.total_slots}")
                
                # Format slots for frontend
                slots = []
                for slot in result.slots:
                    slots.append({
                        "slot_id": slot.slot_id,
                        "status": slot.status,
                        "confidence": slot.confidence,
                        "bbox": {
                            "x1": slot.bbox.x1,
                            "y1": slot.bbox.y1,
                            "x2": slot.bbox.x2,
                            "y2": slot.bbox.y2
                        }
                    })
                
                # Send results back to frontend (real-time feedback)
                await manager.safe_send(websocket, {
                    "event_type": "capacity_update",
                    "parking_lot_id": parking_lot_id,
                    "camera_id": camera_id,
                    "total_slots": result.total_slots,
                    "occupied": result.occupied,
                    "empty": result.empty,
                    "occupancy_rate": result.occupancy_rate,
                    "slots": slots,
                    "timestamp": result.timestamp.isoformat(),
                    "processing_time_ms": result.processing_time_ms
                })
                    
            except Exception as decode_error:
                logger.error(f"[LOT] Frame processing error: {decode_error}")
                await manager.safe_send(websocket, {"event_type": "error", "error": str(decode_error)})
    
    except WebSocketDisconnect:
        logger.info("[LOT] Client disconnected from lot-monitor")
        manager.disconnect(websocket, "lot-monitor")
    except Exception as e:
        logger.error(f"[LOT] WebSocket error: {e}")
        manager.disconnect(websocket, "lot-monitor")
=======
    Detect parking slot occupancy in parking lot image
    Returns: empty slots, occupied slots, and occupancy rate with bounding boxes
    """
    contents = await file.read()
    detector = get_parking_detector()
    result = detector.detect_slots(contents)
    return result



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
>>>>>>> main


@app.websocket("/ws/webrtc-signaling")
async def webrtc_signaling_endpoint(websocket: WebSocket):
    """
    WebRTC signaling server for camera streaming
    Handles offer/answer/ICE candidate exchange between camera and backend
<<<<<<< HEAD
    Compatible with existing python-work WebSocket
    """
    await websocket.accept()
    client_id = id(websocket)

    # Store connection in a simple list (not using manager channels for signaling)
    if not hasattr(app.state, 'webrtc_connections'):
        app.state.webrtc_connections = []

    app.state.webrtc_connections.append(websocket)

=======
    """
    await manager.connect(websocket)
    client_id = id(websocket)
    
>>>>>>> main
    try:
        await websocket.send_json({
            "type": "connected",
            "clientId": client_id,
            "message": "WebRTC signaling server ready"
        })
<<<<<<< HEAD

        logger.info(f"WebRTC client connected: {client_id}")

=======
        
        print(f"✓ WebRTC client connected: {client_id}")
        
>>>>>>> main
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
<<<<<<< HEAD

            logger.debug(f"Signaling [{client_id}]: {msg_type}")

            # Broadcast signaling messages to all other clients
            for connection in app.state.webrtc_connections:
                if connection != websocket:
                    try:
                        await connection.send_text(data)
                    except Exception as e:
                        logger.error(f"Failed to broadcast to client: {e}")

    except WebSocketDisconnect:
        if websocket in app.state.webrtc_connections:
            app.state.webrtc_connections.remove(websocket)
        logger.info(f"WebRTC client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebRTC signaling error: {e}")
        if websocket in app.state.webrtc_connections:
            app.state.webrtc_connections.remove(websocket)



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.ai_backend_host,
        port=settings.ai_backend_port,
        reload=False,
        log_level=settings.ai_backend_log_level.lower()
    )
=======
            
            print(f"📡 Signaling [{client_id}]: {msg_type}")
            
            # Broadcast signaling messages to all other clients
            for connection in manager.active_connections:
                if connection != websocket:
                    await connection.send_text(data)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"✗ WebRTC client disconnected: {client_id}")
    except Exception as e:
        print(f"✗ WebRTC signaling error: {str(e)}")
        manager.disconnect(websocket)


@app.websocket("/ws/gate-monitor")
async def gate_monitor_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time license plate recognition at entry/exit gates
    
    Client sends frames, server responds with plate detections
    """
    await manager.connect(websocket)
    processor = PlateStreamProcessor()
    
    try:
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Gate monitor ready",
            "config": {
                "frame_skip": processor.skip_frames,
                "dedup_window": processor.dedup_window
            }
        })
        
        print(f"✓ Gate Monitor connected | Frame skip: {processor.skip_frames}")
        
        while True:
            # Receive frame data
            data = await websocket.receive()
            
            # Handle binary data (raw image bytes)
            if "bytes" in data:
                frame_bytes = data["bytes"]
            
            # Handle text data (JSON with base64 image)
            elif "text" in data:
                try:
                    message = json.loads(data["text"])
                    
                    # Handle control messages
                    if message.get("type") == "reset":
                        processor.reset_state()
                        await websocket.send_json({
                            "type": "reset_ack",
                            "message": "State reset successful"
                        })
                        print("⟳ Gate Monitor state reset")
                        continue
                    
                    if message.get("type") == "stats":
                        stats = processor.get_stats()
                        await websocket.send_json({
                            "type": "stats",
                            "data": stats
                        })
                        continue
                    
                    # Extract frame data
                    if "data" in message:
                        base64_data = message["data"]
                        frame_bytes = base64_to_bytes(base64_data)
                    else:
                        continue
                        
                except json.JSONDecodeError as e:
                    print(f"✗ Gate Monitor: Invalid JSON")
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid JSON format"
                    })
                    continue
                except Exception as e:
                    print(f"✗ Gate Monitor: Frame decode error - {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Failed to decode frame: {str(e)}"
                    })
                    continue
            else:
                continue
            
            # Process frame
            result = processor.process_frame(frame_bytes)
            
            # Send result (None if frame was skipped)
            if result:
                plates_count = result.get('plates_detected', 0)
                new_count = result.get('new_plates', 0)
                processing_time = result.get('processing_time_ms', 0)
                
                if plates_count > 0:
                    plates_str = ", ".join([p['plate_number'] for p in result.get('plates', [])])
                    print(f"🚗 Detected {plates_count} plate(s): {plates_str} | {processing_time}ms | New: {new_count}")
                else:
                    print(f"○ No plates detected | {processing_time}ms")
                
                await websocket.send_json(result)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        stats = processor.get_stats()
        print(f"✗ Gate Monitor disconnected | Processed: {stats['processed_frames']}/{stats['total_frames']} frames")
    except Exception as e:
        print(f"✗ Gate Monitor error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
        manager.disconnect(websocket)


@app.websocket("/ws/lot-monitor")
async def lot_monitor_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time parking lot capacity monitoring
    
    Client sends frames, server responds with slot occupancy status
    """
    await manager.connect(websocket)
    processor = ParkingStreamProcessor()
    
    try:
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Lot monitor ready",
            "config": {
                "frame_skip": processor.skip_frames
            }
        })
        
        print(f"✓ Lot Monitor connected | Frame skip: {processor.skip_frames}")
        
        while True:
            # Receive frame data
            data = await websocket.receive()
            
            # Handle binary data (raw image bytes)
            if "bytes" in data:
                frame_bytes = data["bytes"]
            
            # Handle text data (JSON with base64 image)
            elif "text" in data:
                try:
                    message = json.loads(data["text"])
                    
                    # Handle control messages
                    if message.get("type") == "reset":
                        processor.reset_state()
                        await websocket.send_json({
                            "type": "reset_ack",
                            "message": "State reset successful"
                        })
                        print("⟳ Lot Monitor state reset")
                        continue
                    
                    if message.get("type") == "stats":
                        stats = processor.get_stats()
                        await websocket.send_json({
                            "type": "stats",
                            "data": stats
                        })
                        continue
                    
                    # Extract frame data
                    if "data" in message:
                        base64_data = message["data"]
                        frame_bytes = base64_to_bytes(base64_data)
                    else:
                        continue
                        
                except json.JSONDecodeError as e:
                    print(f"✗ Lot Monitor: Invalid JSON")
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid JSON format"
                    })
                    continue
                except Exception as e:
                    print(f"✗ Lot Monitor: Frame decode error - {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Failed to decode frame: {str(e)}"
                    })
                    continue
            else:
                continue
            
            # Process frame
            result = processor.process_frame(frame_bytes)
            
            # Send result (None if frame was skipped)
            if result:
                total = result.get('total_slots', 0)
                occupied = result.get('occupied', 0)
                occupancy = result.get('occupancy_rate', 0)
                processing_time = result.get('processing_time_ms', 0)
                
                print(f"✓ Parking: {occupied}/{total} slots ({int(occupancy*100)}%) | {processing_time}ms")
                
                await websocket.send_json(result)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        stats = processor.get_stats()
        print(f"✗ Lot Monitor disconnected | Processed: {stats['processed_frames']}/{stats['total_frames']} frames")
    except Exception as e:
        print(f"✗ Lot Monitor error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
        manager.disconnect(websocket)


if __name__ == "__main__":
    # Set memory-efficient environment variables
    os.environ['OMP_NUM_THREADS'] = '1'  # Reduce OpenCV memory usage
    os.environ['MALLOC_TRIM_THRESHOLD_'] = '100000'  # Aggressive memory release
    
    # Get configuration
    config = Config.get_config_summary()
    
    print("=" * 60)
    print("🚗 Smart Parking Management System")
    print("=" * 60)
    print(f"\n⚙️  Environment: {config['environment'].upper()}")
    print(f"  • OCR Engine: {config['ocr_engine'].upper()}")
    print(f"  • Detection: {config['detection']}")
    print(f"  • Frame Skipping: {'Dynamic' if config['dynamic_frame_skipping'] else 'Fixed'}")
    
    print("\n📦 AI Models:")
    print(f"  • Roboflow API - License Plate Detection")
    print(f"  • {config['ocr_engine'].upper()} - Text Recognition")
    print(f"  • Roboflow API - Parking Slot Detection")
    
    print("\n🌐 API Endpoints:")
    print("  • POST /api/recognize-plate - License Plate Recognition")
    print("  • POST /api/detect-parking-slots - Parking Slot Detection")
    print("\n🌐 WebSocket Endpoints:")
    print("  • /ws/webrtc-signaling - WebRTC Signaling Server")
    print("  • /ws/gate-monitor - License Plate Recognition")
    print("  • /ws/lot-monitor - Parking Capacity Monitoring")
    print("\n📺 WebRTC Remote Streaming:")
    print("  • Camera: http://YOUR_IP:3000/camera")
    print("  • Backend: http://localhost:3000/test-backend")
    print("\n⚙️  Configuration:")
    print(f"  • Gate frame skip: {os.getenv('GATE_FRAME_SKIP', '50')}")
    print(f"  • Lot frame skip: {os.getenv('LOT_FRAME_SKIP', '50')}")
    
    print("\n💾 Optimizations:")
    print("  • Roboflow API (cloud-based detection)")
    print("  • Image resizing (max 1280px)")
    print("  • Aggressive garbage collection")
    
    print("=" * 60)
    print()
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run("main:app", host=host, port=port, reload=False)

>>>>>>> main
