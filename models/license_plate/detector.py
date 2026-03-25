from roboflow import Roboflow
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv
import tempfile
import time

load_dotenv()


class LicensePlateDetector:
    def __init__(self):
        """Initialize Roboflow license plate detection model"""
        api_key = os.getenv("ROBOFLOW_API_KEY", "iFFDE6mLuRtrRR8tspsE")
        
        try:
            rf = Roboflow(api_key=api_key)
            project = rf.workspace().project("license-plate-recognition-rxg4e")
            self.model = project.version(11).model
            
            # Get confidence
            conf_str = os.getenv("PLATE_DETECTION_CONFIDENCE", "40")
            try:
                conf_val = float(conf_str)
                self.confidence = int(conf_val * 100) if conf_val <= 1.0 else int(conf_val)
            except ValueError:
                self.confidence = 40
            
            self.overlap = int(os.getenv("PLATE_DETECTION_OVERLAP", "30"))
            
            # Performance tracking
            self.api_call_times = []
            self.max_tracked_times = 20
            
            print("✓ Using Roboflow API for license plate detection")
        except Exception as e:
            print(f"✗ Failed to initialize Roboflow: {str(e)}")
            raise
    
    def detect_plates(self, image_bytes):
        """Detect license plates in image and return bounding boxes using Roboflow API (optimized)"""
        api_start = time.time()
        temp_fd = None
        temp_path = None
        
        try:
            # Convert bytes to image and resize aggressively for faster API calls
            image = Image.open(BytesIO(image_bytes))
            
            # More aggressive resizing for faster API calls (640px is sufficient for plate detection)
            max_dimension = 640  # Reduced from 1280
            scale_factor = 1.0
            if max(image.size) > max_dimension:
                scale_factor = max_dimension / max(image.size)
                new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
                image = image.resize(new_size, Image.LANCZOS)
            
            # Get original dimensions for response
            image_shape = (image.height, image.width, 3)
            
            # Use temporary file with context manager for automatic cleanup
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix='plate_')
            
            # Save with lower quality for faster I/O (quality=75 is good enough for detection)
            image.save(temp_path, quality=75, optimize=False)
            
            # Close file descriptor immediately
            os.close(temp_fd)
            temp_fd = None
            
            # Run detection via Roboflow API
            result = self.model.predict(
                temp_path,
                confidence=self.confidence,
                overlap=self.overlap
            ).json()
            
            # Track API call time
            api_time = time.time() - api_start
            self.api_call_times.append(api_time)
            if len(self.api_call_times) > self.max_tracked_times:
                self.api_call_times.pop(0)
            
            # Parse results
            plates = []
            for prediction in result.get('predictions', []):
                confidence = prediction['confidence']
                
                # Extract bounding box (convert from center to corners)
                # Scale back to original coordinates
                x = int(prediction['x'] / scale_factor)
                y = int(prediction['y'] / scale_factor)
                width = int(prediction['width'] / scale_factor)
                height = int(prediction['height'] / scale_factor)
                
                x1 = x - width // 2
                y1 = y - height // 2
                x2 = x + width // 2
                y2 = y + height // 2
                
                plates.append({
                    "confidence": round(confidence, 2),
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2
                    }
                })
            
            return {
                "success": True,
                "plate_count": len(plates),
                "plates": plates,
                "image_shape": image_shape,
                "api_time_ms": int(api_time * 1000)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            # Ensure cleanup even on error
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except:
                    pass
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    def get_avg_api_time(self):
        """Get average API call time in milliseconds"""
        if not self.api_call_times:
            return 0
        return int(sum(self.api_call_times) / len(self.api_call_times) * 1000)
    
    def crop_plates(self, image_bytes, bboxes):
        """Crop license plate regions from image (memory optimized)"""
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # Resize image if too large (saves memory during cropping)
            max_dimension = 1280
            scale_factor = 1.0
            if max(image.size) > max_dimension:
                scale_factor = max_dimension / max(image.size)
                new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
                image = image.resize(new_size, Image.LANCZOS)
            
            image_np = np.array(image)
            
            cropped_plates = []
            for bbox in bboxes:
                # Scale bbox coordinates if image was resized
                x1 = int(bbox["x1"] * scale_factor)
                y1 = int(bbox["y1"] * scale_factor)
                x2 = int(bbox["x2"] * scale_factor)
                y2 = int(bbox["y2"] * scale_factor)
                
                # Add padding (10% on each side for better OCR)
                height, width = image_np.shape[:2]
                padding_x = int((x2 - x1) * 0.1)
                padding_y = int((y2 - y1) * 0.1)
                
                x1 = max(0, x1 - padding_x)
                y1 = max(0, y1 - padding_y)
                x2 = min(width, x2 + padding_x)
                y2 = min(height, y2 + padding_y)
                
                # Crop the region (creates a copy, not a view)
                cropped = image_np[y1:y2, x1:x2].copy()
                
                # Ensure minimum size for OCR
                crop_height, crop_width = cropped.shape[:2]
                if crop_height < 30 or crop_width < 80:
                    # Resize to minimum size
                    scale = max(30 / crop_height, 80 / crop_width)
                    new_width = int(crop_width * scale)
                    new_height = int(crop_height * scale)
                    cropped = cv2.resize(cropped, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                
                cropped_plates.append(cropped)
            
            # Delete original image array to free memory
            del image_np
            del image
            
            return cropped_plates
        
        except Exception as e:
            print(f"Cropping error: {str(e)}")
            return []
