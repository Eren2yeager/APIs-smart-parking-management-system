import easyocr
import numpy as np
from io import BytesIO
from PIL import Image
import re
import cv2
import os
from dotenv import load_dotenv

load_dotenv()


class PlateReader:
    def __init__(self):
        # Initialize EasyOCR reader for English
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.min_confidence = float(os.getenv("DETECTION_CONFIDENCE", "0.5"))
    
    def read(self, image_bytes):
        """Read license plate from image"""
        try:
            # Convert bytes to image
            image = Image.open(BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Read text from image
            results = self.reader.readtext(image_np)
            
            plates = []
            for (bbox, text, confidence) in results:
                # Filter by confidence threshold
                if confidence < self.min_confidence:
                    continue
                
                # Clean up text (remove spaces, special chars)
                cleaned_text = re.sub(r'[^A-Z0-9]', '', text.upper())
                
                # Basic validation: plate should have alphanumeric chars (4-15 chars typical)
                if 4 <= len(cleaned_text) <= 15:
                    plates.append({
                        "text": cleaned_text,
                        "raw_text": text,
                        "confidence": round(confidence, 2),
                        "bbox": [[int(coord) for coord in point] for point in bbox]
                    })
            
            return {
                "success": True,
                "plates_found": len(plates),
                "plates": plates
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
