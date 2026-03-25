"""
Local license plate detector using YOLO model (for development mode)
Faster and doesn't require API calls
Auto-downloads YOLOv8n model from Ultralytics (free, open source)
"""

import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import os


class LocalLicensePlateDetector:
    """
    Local YOLO-based license plate detector
    Automatically downloads YOLOv8n model from Ultralytics on first run
    """
    
    def __init__(self):
        """Initialize local YOLO detector with auto-download from Ultralytics"""
        try:
            from ultralytics import YOLO
            
            # Model path
            model_path = "models/license_plate/license_plate_detector.pt"
            
            # Check if model exists, if not download
            if not os.path.exists(model_path):
                print("📥 License plate detector model not found locally")
                print("   Downloading YOLOv8n model (first run only)...")
                self._download_yolov8_model(model_path)
            
            # Load the model
            self.model = YOLO(model_path)
            print("✓ Loaded license_plate_detector.pt model (development mode)")
            
            self.confidence = 0.4
            
        except Exception as e:
            print(f"✗ Failed to initialize local detector: {str(e)}")
            raise
    
    def _download_yolov8_model(self, model_path):
        """Download YOLOv8 model - tries multiple sources"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Method 1: Use Ultralytics YOLO auto-download
            print("   Method 1: Using Ultralytics auto-download...")
            try:
                from ultralytics import YOLO
                
                # This will auto-download yolov8n.pt to ultralytics cache
                temp_model = YOLO('yolov8n.pt')
                
                # Find the downloaded model in cache
                import torch
                cache_dir = torch.hub.get_dir()
                source_path = os.path.join(cache_dir, 'ultralytics', 'yolov8n.pt')
                
                if os.path.exists(source_path):
                    import shutil
                    shutil.copy(source_path, model_path)
                    print(f"✓ Model downloaded successfully to {model_path}")
                    return
                    
            except Exception as e:
                print(f"   ✗ Method 1 failed: {str(e)[:80]}")
            
            # Method 2: Direct download from GitHub
            print("   Method 2: Direct download from Ultralytics GitHub...")
            self._download_from_github(model_path)
            
        except Exception as e:
            print(f"❌ All download methods failed: {str(e)}")
            print("   You can manually download a YOLOv8 model:")
            print("   1. Visit: https://github.com/ultralytics/assets/releases")
            print("   2. Download yolov8n.pt")
            print("   3. Place at: models/license_plate/license_plate_detector.pt")
            raise
    
    def _download_from_github(self, model_path):
        """Download YOLOv8 model directly from GitHub releases"""
        try:
            import urllib.request
            import shutil
            
            # YOLOv8n model URL (free, open source)
            url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
            
            print(f"   Downloading from: {url}")
            
            # Download with progress
            def reporthook(count, block_size, total_size):
                if total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    if percent % 10 == 0 and percent > 0:
                        print(f"   Progress: {percent}%", end='\r')
            
            urllib.request.urlretrieve(url, model_path, reporthook)
            print(f"\n✓ Model downloaded successfully to {model_path}")
            
            # Verify file size
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            print(f"   Model size: {size_mb:.1f} MB")
            
        except Exception as e:
            print(f"❌ GitHub download failed: {str(e)}")
            raise
            
        except Exception as e:
            print(f"✗ Failed to initialize local detector: {str(e)}")
            raise
    
    def detect_plates(self, image_bytes):
        """Detect license plates in image and return bounding boxes"""
        try:
            # Convert bytes to image
            image = Image.open(BytesIO(image_bytes))
            
            # Resize if too large
            max_dimension = 1280
            if max(image.size) > max_dimension:
                scale = max_dimension / max(image.size)
                new_size = (int(image.width * scale), int(image.height * scale))
                image = image.resize(new_size, Image.LANCZOS)
            
            # Convert to numpy array
            image_np = np.array(image)
            image_shape = (image.height, image.width, 3)
            
            # Run detection
            results = self.model(image_np, conf=self.confidence, verbose=False)
            
            # Parse results
            plates = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0])
                    
                    plates.append({
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
                "plate_count": len(plates),
                "plates": plates,
                "image_shape": image_shape
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def crop_plates(self, image_bytes, bboxes):
        """Crop license plate regions from image"""
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # Resize if too large
            max_dimension = 1280
            scale_factor = 1.0
            if max(image.size) > max_dimension:
                scale_factor = max_dimension / max(image.size)
                new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
                image = image.resize(new_size, Image.LANCZOS)
            
            image_np = np.array(image)
            
            cropped_plates = []
            for bbox in bboxes:
                # Scale bbox coordinates
                x1 = int(bbox["x1"] * scale_factor)
                y1 = int(bbox["y1"] * scale_factor)
                x2 = int(bbox["x2"] * scale_factor)
                y2 = int(bbox["y2"] * scale_factor)
                
                # Add padding
                height, width = image_np.shape[:2]
                padding_x = int((x2 - x1) * 0.1)
                padding_y = int((y2 - y1) * 0.1)
                
                x1 = max(0, x1 - padding_x)
                y1 = max(0, y1 - padding_y)
                x2 = min(width, x2 + padding_x)
                y2 = min(height, y2 + padding_y)
                
                # Crop
                cropped = image_np[y1:y2, x1:x2].copy()
                
                # Ensure minimum size
                crop_height, crop_width = cropped.shape[:2]
                if crop_height < 30 or crop_width < 80:
                    scale = max(30 / crop_height, 80 / crop_width)
                    new_width = int(crop_width * scale)
                    new_height = int(crop_height * scale)
                    cropped = cv2.resize(cropped, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                
                cropped_plates.append(cropped)
            
            del image_np
            del image
            
            return cropped_plates
        
        except Exception as e:
            print(f"Cropping error: {str(e)}")
            return []
