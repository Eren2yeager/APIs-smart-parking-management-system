from .detector import LicensePlateDetector
from .reader import PlateReader
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
import os
import gc
from datetime import datetime


class PlateRecognitionPipeline:
    """
    Two-stage pipeline for license plate recognition:
    1. Detect license plate regions using YOLO
    2. Run OCR only on detected plate regions
    """
    
    def __init__(self, debug=False):
        self.plate_detector = LicensePlateDetector()
        self.plate_reader = PlateReader()
        self.debug = debug or os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        if self.debug:
            os.makedirs("debug_crops", exist_ok=True)
    
    def process(self, image_bytes):
        """Process image: Detect plates -> Crop regions -> OCR (memory optimized)"""
        try:
            # Stage 1: Detect license plate regions
            detection_result = self.plate_detector.detect_plates(image_bytes)
            
            if not detection_result["success"]:
                gc.collect()  # Clean up on error
                return {
                    "success": False,
                    "error": f"Detection failed: {detection_result.get('error', 'Unknown error')}"
                }
            
            if detection_result["plate_count"] == 0:
                gc.collect()  # Clean up
                return {
                    "success": True,
                    "plates_found": 0,
                    "plates": [],
                    "message": "No license plates detected"
                }
            
            # Stage 2: Crop detected plate regions
            bboxes = [plate["bbox"] for plate in detection_result["plates"]]
            cropped_plates = self.plate_detector.crop_plates(image_bytes, bboxes)
            
            # Delete image_bytes immediately after cropping to free memory
            del image_bytes
            del bboxes
            gc.collect()
            
            if not cropped_plates:
                return {
                    "success": False,
                    "error": "Failed to crop detected plates"
                }
            
            # Stage 3: Run OCR on each cropped plate (process sequentially to save memory)
            recognized_plates = []
            
            if self.debug:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for i, (cropped_plate, detection_info) in enumerate(zip(cropped_plates, detection_result["plates"])):
                if self.debug:
                    # Save debug images
                    debug_path = f"debug_crops/plate_{timestamp}_{i}_original.jpg"
                    cv2.imwrite(debug_path, cv2.cvtColor(cropped_plate, cv2.COLOR_RGB2BGR))
                    print(f"Debug: Saved {debug_path}")
                
                ocr_result = self.plate_reader.read_from_cropped(cropped_plate)
                
                # Delete cropped plate immediately after OCR to free memory
                del cropped_plate
                
                if ocr_result:
                    recognized_plates.append({
                        "plate_number": ocr_result["text"],
                        "raw_text": ocr_result["raw_text"],
                        "ocr_confidence": ocr_result["confidence"],
                        "detection_confidence": detection_info["confidence"],
                        "bbox": detection_info["bbox"]
                    })
                elif self.debug:
                    print(f"  OCR failed for plate {i}")
            
            # Clean up remaining arrays
            del cropped_plates
            gc.collect()
            
            return {
                "success": True,
                "plates_detected": detection_result["plate_count"],
                "plates_recognized": len(recognized_plates),
                "plates": recognized_plates
            }
        
        except Exception as e:
            # Force garbage collection on error
            gc.collect()
            return {
                "success": False,
                "error": str(e)
            }
