"""
Local parking slot detector using YOLOv8 (for development mode)
Faster and doesn't require API calls
"""

import os
from io import BytesIO
from PIL import Image
import numpy as np


class LocalParkingSlotDetector:
    """
    Local YOLO-based parking slot detector
    Uses pre-trained YOLOv8 model for fast local detection
    """
    
    def __init__(self):
        """Initialize local YOLO detector"""
        try:
            from ultralytics import YOLO
            
            # Try to load a pre-trained parking slot model
            model_path = "models/parking_space_detector/yolov8_parking.pt"
            
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                print("✓ Loaded custom YOLOv8 parking detection model")
            else:
                # Fallback to YOLOv8n
                self.model = YOLO('yolov8n.pt')
                print("⚠️  Using YOLOv8n base model (download custom parking model for better results)")
            
            self.confidence = 0.4
            
        except Exception as e:
            print(f"✗ Failed to initialize local parking detector: {str(e)}")
            raise
    
    def detect_slots(self, image_bytes):
        """
        Detect parking slots in image
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            dict: Detection results with slot statuses and bounding boxes
        """
        try:
            # Convert bytes to image
            image = Image.open(BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Run detection
            results = self.model(image_np, conf=self.confidence, verbose=False)
            
            # Parse results
            occupied_count = 0
            empty_count = 0
            slots = []
            
            for result in results:
                boxes = result.boxes
                for idx, box in enumerate(boxes):
                    # Get coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    
                    # Map class to status (adjust based on your model)
                    # Assuming: 0 = empty, 1 = occupied
                    status = "occupied" if class_id == 1 else "empty"
                    
                    if status == "occupied":
                        occupied_count += 1
                    else:
                        empty_count += 1
                    
                    slots.append({
                        "slot_id": idx + 1,
                        "status": status,
                        "confidence": round(confidence, 2),
                        "bbox": {
                            "x1": int(x1),
                            "y1": int(y1),
                            "x2": int(x2),
                            "y2": int(y2)
                        }
                    })
            
            total_slots = occupied_count + empty_count
            occupancy_rate = occupied_count / total_slots if total_slots > 0 else 0
            
            return {
                "success": True,
                "total_slots": total_slots,
                "occupied": occupied_count,
                "empty": empty_count,
                "occupancy_rate": round(occupancy_rate, 2),
                "slots": slots
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
