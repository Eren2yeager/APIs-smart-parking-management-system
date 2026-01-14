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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.post("/api/recognize-plate")
async def recognize_plate(file: UploadFile = File(...)):
    """Recognize license plate using two-stage pipeline"""
    contents = await file.read()
    pipeline = get_plate_pipeline()
    result = pipeline.process(contents)
    return result


@app.post("/api/detect-parking-slots")
async def detect_parking_slots(file: UploadFile = File(...)):
    """
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


@app.websocket("/ws/webrtc-signaling")
async def webrtc_signaling_endpoint(websocket: WebSocket):
    """
    WebRTC signaling server for camera streaming
    Handles offer/answer/ICE candidate exchange between camera and backend
    """
    await manager.connect(websocket)
    client_id = id(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "clientId": client_id,
            "message": "WebRTC signaling server ready"
        })
        
        print(f"✓ WebRTC client connected: {client_id}")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
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

