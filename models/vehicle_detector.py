from ultralytics import YOLO
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv()


class VehicleDetector:
    def __init__(self):
        # Load pre-trained YOLOv8 model
        model_path = os.getenv("YOLO_MODEL", "yolov8n.pt")
        self.model = YOLO(model_path)  # Downloads automatically on first run
        self.confidence_threshold = float(os.getenv("DETECTION_CONFIDENCE", "0.5"))
        # Vehicle class IDs in COCO dataset
        self.vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
    
    def detect(self, image_bytes):
        """Detect vehicles in image"""
        try:
            # Convert bytes to image
            image = Image.open(BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Run detection
            results = self.model(image_np)
            
            vehicles = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    if class_id in self.vehicle_classes:
                        confidence = float(box.conf[0])
                        # Filter by confidence threshold
                        if confidence < self.confidence_threshold:
                            continue
                        
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        vehicles.append({
                            "type": self.model.names[class_id],
                            "confidence": round(confidence, 2),
                            "bbox": {
                                "x1": int(x1),
                                "y1": int(y1),
                                "x2": int(x2),
                                "y2": int(y2)
                            }
                        })
            
            return {
                "success": True,
                "vehicle_count": len(vehicles),
                "vehicles": vehicles
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
