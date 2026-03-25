"""
Parking slot detection using Roboflow API
Detects occupied and empty parking spaces
"""

import os
from dotenv import load_dotenv
from roboflow import Roboflow
from io import BytesIO
from PIL import Image
import numpy as np

load_dotenv()


class ParkingSlotDetector:
    """
    Detects parking slot occupancy using Roboflow API
    Used in both development and production modes
    """
    
    def __init__(self):
        """Initialize Roboflow parking detection model"""
        api_key = os.getenv("ROBOFLOW_API_KEY", "iFFDE6mLuRtrRR8tspsE")
        
        try:
            rf = Roboflow(api_key=api_key)
            project = rf.workspace().project("car-space-find")
            self.model = project.version(2).model
            
            self.confidence = int(os.getenv("PARKING_CONFIDENCE", "40"))
            self.overlap = int(os.getenv("PARKING_OVERLAP", "30"))
            
            print("✓ Using Roboflow API parking detector")
        except Exception as e:
            print(f"✗ Failed to initialize Roboflow: {str(e)}")
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
            # Convert bytes to temporary file (Roboflow needs file path)
            image = Image.open(BytesIO(image_bytes))
            temp_path = "temp_parking_frame.jpg"
            image.save(temp_path)
            
            # Run detection
            result = self.model.predict(
                temp_path,
                confidence=self.confidence,
                overlap=self.overlap
            ).json()
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Parse results
            occupied_count = 0
            empty_count = 0
            slots = []
            
            for idx, prediction in enumerate(result.get('predictions', [])):
                predicted_class = prediction['class']
                confidence = prediction['confidence']
                
                # Extract bounding box
                x = int(prediction['x'])
                y = int(prediction['y'])
                width = int(prediction['width'])
                height = int(prediction['height'])
                
                # Convert center coordinates to corner coordinates
                x1 = x - width // 2
                y1 = y - height // 2
                x2 = x + width // 2
                y2 = y + height // 2
                
                # Count and store slot info
                if predicted_class == 'occupied':
                    occupied_count += 1
                elif predicted_class == 'empty':
                    empty_count += 1
                
                slots.append({
                    "slot_id": idx + 1,
                    "status": predicted_class,
                    "confidence": round(confidence, 2),
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2
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
