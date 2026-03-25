# Smart Parking API Documentation

Complete API reference for integrating with the Smart Parking backend.

---

## Configuration

The system supports two operational modes controlled by environment variables:

### Environment Modes

**Development Mode** (`ENVIRONMENT=development`):
- Uses local YOLOv8 models for detection
- Uses PaddleOCR for text recognition
- Faster processing, no API costs
- Works offline

**Production Mode** (`ENVIRONMENT=production`):
- Uses Roboflow API for detection
- Uses EasyOCR for text recognition
- Higher accuracy
- Requires internet connection

### Frame Skipping

**Fixed Skipping** (`DYNAMIC_FRAME_SKIPPING=false`):
- Processes every Nth frame (configured by env variables)
- Predictable behavior

**Dynamic Skipping** (`DYNAMIC_FRAME_SKIPPING=true`):
- Automatically adjusts skip rate based on performance
- Maintains target FPS
- Optimal for varying hardware

See `ENVIRONMENT_CONFIG.md` for detailed configuration guide.

---

## Base URL

```
http://localhost:8000
```

For production, replace with your deployed URL (e.g., Render).

---

## REST API Endpoints

### 1. Health Check

**Endpoint:** `GET /api/health`

**Description:** Check if the API is running.

**Request:** None

**Response:**
```json
{
  "status": "healthy",
  "service": "smart-parking-backend"
}
```

---

### 2. Recognize License Plate

**Endpoint:** `POST /api/recognize-plate`

**Description:** Detect and recognize license plates in an uploaded image.

**Request:**
- **Method:** POST
- **Content-Type:** `multipart/form-data`
- **Body:** 
  - `file`: Image file (JPEG, PNG, etc.)

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch('http://localhost:8000/api/recognize-plate', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

**Response (Success):**
```json
{
  "success": true,
  "plates_detected": 2,
  "plates_recognized": 2,
  "plates": [
    {
      "plate_number": "ABC1234",
      "raw_text": "ABC 1234",
      "ocr_confidence": 0.95,
      "detection_confidence": 0.87,
      "bbox": {
        "x1": 120,
        "y1": 200,
        "x2": 280,
        "y2": 250
      }
    }
  ]
}
```

**Response (No Plates Found):**
```json
{
  "success": true,
  "plates_found": 0,
  "plates": [],
  "message": "No license plates detected"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message here"
}
```

---

### 3. Detect Parking Slots

**Endpoint:** `POST /api/detect-parking-slots`

**Description:** Detect parking slot occupancy in a parking lot image.

**Request:**
- **Method:** POST
- **Content-Type:** `multipart/form-data`
- **Body:** 
  - `file`: Image file (JPEG, PNG, etc.)

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch('http://localhost:8000/api/detect-parking-slots', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

**Response (Success):**
```json
{
  "success": true,
  "total_slots": 50,
  "occupied": 35,
  "empty": 15,
  "occupancy_rate": 0.7,
  "slots": [
    {
      "slot_id": 1,
      "status": "occupied",
      "confidence": 0.92,
      "bbox": {
        "x1": 100,
        "y1": 150,
        "x2": 200,
        "y2": 250
      }
    },
    {
      "slot_id": 2,
      "status": "empty",
      "confidence": 0.88,
      "bbox": {
        "x1": 210,
        "y1": 150,
        "x2": 310,
        "y2": 250
      }
    }
  ]
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message here"
}
```

---

## WebSocket Endpoints

### 1. WebRTC Signaling

**Endpoint:** `ws://localhost:8000/ws/webrtc-signaling`

**Description:** WebRTC signaling server for camera streaming (offer/answer/ICE candidate exchange).

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/webrtc-signaling');

ws.onopen = () => {
  console.log('Connected to signaling server');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

**Messages Received:**

**Connection Confirmation:**
```json
{
  "type": "connected",
  "clientId": 12345,
  "message": "WebRTC signaling server ready"
}
```

**Signaling Messages:**
- Messages are broadcast to all other connected clients
- Used for WebRTC offer/answer/ICE candidate exchange

**Messages to Send:**
```javascript
// Send any WebRTC signaling message
ws.send(JSON.stringify({
  type: "offer",
  sdp: "...",
  // ... other WebRTC data
}));
```

---

### 2. Gate Monitor (License Plate Recognition)

**Endpoint:** `ws://localhost:8000/ws/gate-monitor`

**Description:** Real-time license plate recognition for entry/exit gates. Send video frames, receive plate detections.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/gate-monitor');

ws.onopen = () => {
  console.log('Gate monitor connected');
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  handlePlateDetection(result);
};
```

**Messages Received:**

**Connection Confirmation:**
```json
{
  "type": "connection",
  "status": "connected",
  "message": "Gate monitor ready",
  "config": {
    "frame_skip": 10,
    "dedup_window": 10
  }
}
```

**Plate Detection Result:**
```json
{
  "success": true,
  "type": "plate_detection",
  "timestamp": 1704844800.123,
  "frame_number": 150,
  "processed_frame_number": 15,
  "plates": [
    {
      "plate_number": "XYZ5678",
      "raw_text": "XYZ 5678",
      "confidence": 0.93,
      "detection_confidence": 0.89,
      "bbox": {
        "x1": 150,
        "y1": 220,
        "x2": 310,
        "y2": 270
      },
      "is_new": true
    }
  ],
  "plates_detected": 1,
  "new_plates": 1,
  "processing_time_ms": 450,
  "current_skip_rate": 5  // Only present if DYNAMIC_FRAME_SKIPPING=true
}
```

**Note:** When `DYNAMIC_FRAME_SKIPPING=true`, responses include `current_skip_rate` showing the adaptive skip rate.

**No Plates Detected:**
```json
{
  "success": true,
  "type": "plate_detection",
  "timestamp": 1704844800.123,
  "frame_number": 151,
  "processed_frame_number": 16,
  "plates": [],
  "plates_detected": 0,
  "new_plates": 0,
  "processing_time_ms": 320
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message here",
  "frame_number": 152,
  "timestamp": 1704844800.456
}
```

**Messages to Send:**

**Send Frame (Base64):**
```javascript
// Capture frame from video
const canvas = document.createElement('canvas');
canvas.width = video.videoWidth;
canvas.height = video.videoHeight;
const ctx = canvas.getContext('2d');
ctx.drawImage(video, 0, 0);

// Convert to base64
const base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];

// Send to server
ws.send(JSON.stringify({
  data: base64Image
}));
```

**Send Frame (Binary):**
```javascript
// Convert canvas to blob
canvas.toBlob((blob) => {
  ws.send(blob);
}, 'image/jpeg', 0.8);
```

**Reset State:**
```javascript
ws.send(JSON.stringify({
  type: "reset"
}));

// Response:
// {
//   "type": "reset_ack",
//   "message": "State reset successful"
// }
```

**Get Statistics:**
```javascript
ws.send(JSON.stringify({
  type: "stats"
}));

// Response:
// {
//   "type": "stats",
//   "data": {
//     "total_frames": 500,
//     "processed_frames": 50,
//     "skip_rate": "1/10",
//     "tracked_plates": 12
//   }
// }
```

---

### 3. Lot Monitor (Parking Capacity)

**Endpoint:** `ws://localhost:8000/ws/lot-monitor`

**Description:** Real-time parking lot capacity monitoring. Send video frames, receive slot occupancy status.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/lot-monitor');

ws.onopen = () => {
  console.log('Lot monitor connected');
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  handleCapacityUpdate(result);
};
```

**Messages Received:**

**Connection Confirmation:**
```json
{
  "type": "connection",
  "status": "connected",
  "message": "Lot monitor ready",
  "config": {
    "frame_skip": 20
  }
}
```

**Capacity Update:**
```json
{
  "success": true,
  "type": "capacity_update",
  "timestamp": 1704844800.123,
  "frame_number": 200,
  "processed_frame_number": 10,
  "total_slots": 50,
  "occupied": 35,
  "empty": 15,
  "occupancy_rate": 0.7,
  "slots": [
    {
      "slot_id": 1,
      "status": "occupied",
      "confidence": 0.92,
      "bbox": {
        "x1": 100,
        "y1": 150,
        "x2": 200,
        "y2": 250
      }
    },
    {
      "slot_id": 2,
      "status": "empty",
      "confidence": 0.88,
      "bbox": {
        "x1": 210,
        "y1": 150,
        "x2": 310,
        "y2": 250
      }
    }
  ],
  "processing_time_ms": 380,
  "current_skip_rate": 10  // Only present if DYNAMIC_FRAME_SKIPPING=true
}
```

**Note:** When `DYNAMIC_FRAME_SKIPPING=true`, responses include `current_skip_rate` showing the adaptive skip rate.

**Capacity Update with State Change:**
```json
{
  "success": true,
  "type": "capacity_update",
  "timestamp": 1704844800.456,
  "frame_number": 220,
  "processed_frame_number": 11,
  "total_slots": 50,
  "occupied": 36,
  "empty": 14,
  "occupancy_rate": 0.72,
  "state_change": {
    "previous": 35,
    "current": 36,
    "change": 1,
    "direction": "increased"
  },
  "slots": [...],
  "processing_time_ms": 390
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message here",
  "frame_number": 221,
  "timestamp": 1704844800.789
}
```

**Messages to Send:**

**Send Frame (Base64):**
```javascript
// Same as gate monitor
const base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];

ws.send(JSON.stringify({
  data: base64Image
}));
```

**Send Frame (Binary):**
```javascript
// Same as gate monitor
canvas.toBlob((blob) => {
  ws.send(blob);
}, 'image/jpeg', 0.8);
```

**Reset State:**
```javascript
ws.send(JSON.stringify({
  type: "reset"
}));

// Response:
// {
//   "type": "reset_ack",
//   "message": "State reset successful"
// }
```

**Get Statistics:**
```javascript
ws.send(JSON.stringify({
  type: "stats"
}));

// Response:
// {
//   "type": "stats",
//   "data": {
//     "total_frames": 400,
//     "processed_frames": 20,
//     "skip_rate": "1/20",
//     "current_occupancy": 36
//   }
// }
```

---

## Data Types Reference

### Bounding Box (bbox)
```typescript
{
  x1: number,  // Top-left X coordinate
  y1: number,  // Top-left Y coordinate
  x2: number,  // Bottom-right X coordinate
  y2: number   // Bottom-right Y coordinate
}
```

### Plate Object
```typescript
{
  plate_number: string,        // Cleaned plate text (e.g., "ABC1234")
  raw_text: string,            // Original OCR text (e.g., "ABC 1234")
  confidence: number,          // OCR confidence (0-1)
  detection_confidence: number, // Detection confidence (0-1)
  bbox: BoundingBox,
  is_new?: boolean             // Only in WebSocket responses
}
```

### Slot Object
```typescript
{
  slot_id: number,
  status: "occupied" | "empty",
  confidence: number,  // Detection confidence (0-1)
  bbox: BoundingBox
}
```

### State Change Object
```typescript
{
  previous: number,    // Previous occupancy count
  current: number,     // Current occupancy count
  change: number,      // Difference (positive or negative)
  direction: "increased" | "decreased"
}
```

---

## Environment Variables

Configure these in your `.env` file:

```bash
# Server
HOST=0.0.0.0
PORT=8000

# License Plate Detection (Roboflow)
PLATE_DETECTION_CONFIDENCE=40  # 0-100
PLATE_DETECTION_OVERLAP=30     # 0-100

# Parking Slot Detection (Roboflow)
ROBOFLOW_API_KEY=your_api_key
PARKING_CONFIDENCE=40          # 0-100
PARKING_OVERLAP=30             # 0-100

# Gate Monitor (WebSocket)
GATE_FRAME_SKIP=10             # Process every Nth frame
GATE_DEDUP_WINDOW=10           # Ignore duplicate plates for N seconds

# Lot Monitor (WebSocket)
LOT_FRAME_SKIP=20              # Process every Nth frame

# Debug
DEBUG_MODE=false               # Save cropped plates to debug_crops/
```

---

## Error Handling

All endpoints return a consistent error format:

```json
{
  "success": false,
  "error": "Descriptive error message"
}
```

**Common HTTP Status Codes:**
- `200 OK` - Request successful
- `422 Unprocessable Entity` - Invalid request (e.g., missing file)
- `500 Internal Server Error` - Server error

**WebSocket Errors:**
- Sent as JSON messages with `success: false`
- Connection closes on critical errors

---

## Performance Tips

### REST API
- Resize images before uploading (max 1280px recommended)
- Use JPEG format with 80% quality for best balance
- Process images in batches if needed

### WebSocket
- **Frame Skip:** Adjust `GATE_FRAME_SKIP` and `LOT_FRAME_SKIP` based on your needs
  - Higher values = less processing, lower latency
  - Lower values = more accurate, higher latency
- **Image Quality:** Send JPEG at 70-80% quality
- **Resolution:** 640x480 or 1280x720 recommended
- **Frame Rate:** 5-10 FPS is sufficient for most use cases

### Memory Management
- Close WebSocket connections when not in use
- Reset state periodically with `type: "reset"` message
- Multiple connections share the same AI models (memory efficient)

---

## Example Integration

### React Example (License Plate Recognition)

```javascript
import { useState, useRef } from 'react';

function LicensePlateScanner() {
  const [result, setResult] = useState(null);
  const wsRef = useRef(null);
  const videoRef = useRef(null);

  // Connect to WebSocket
  const connect = () => {
    wsRef.current = new WebSocket('ws://localhost:8000/ws/gate-monitor');
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.success && data.plates_detected > 0) {
        setResult(data);
      }
    };
  };

  // Send frame every second
  const startScanning = () => {
    setInterval(() => {
      if (!wsRef.current || !videoRef.current) return;
      
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0);
      
      canvas.toBlob((blob) => {
        wsRef.current.send(blob);
      }, 'image/jpeg', 0.8);
    }, 1000);
  };

  return (
    <div>
      <video ref={videoRef} autoPlay />
      <button onClick={connect}>Connect</button>
      <button onClick={startScanning}>Start Scanning</button>
      
      {result && (
        <div>
          <h3>Detected Plates:</h3>
          {result.plates.map((plate, i) => (
            <div key={i}>
              <p>{plate.plate_number}</p>
              <p>Confidence: {(plate.confidence * 100).toFixed(1)}%</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Support

For issues or questions:
1. Check server logs for detailed error messages
2. Verify environment variables are set correctly
3. Test with `/api/health` endpoint first
4. Enable `DEBUG_MODE=true` for detailed debugging

---

## Version

API Version: 1.0  
Last Updated: January 2026
