"""
License Plate Detection Model
Uses Roboflow Workflow API for license plate detection and OCR
"""

from inference_sdk import InferenceHTTPClient
import cv2
import numpy as np
import tempfile
import os
import time
from typing import Dict, List, Optional
from PIL import Image

from config.settings import settings
from utils.logger import logger
from schemas.detection_result import LicensePlateDetection, BoundingBox


class LicensePlateDetectorModel:
    """License plate detection and OCR model using Roboflow Workflow API"""
    
    def __init__(self):
        """Initialize Roboflow Workflow client"""
        self.client = None
        self._init_workflow_client()
        
        # Performance tracking
        self.api_call_times = []
        self.max_tracked_times = 20
        
        if self.client:
            logger.info("License Plate Detector initialized successfully (Workflow API)")
        else:
            logger.warning("License Plate Detector initialized WITHOUT client (will retry on first request)")
    
    def _init_workflow_client(self):
        """Initialize Roboflow Workflow HTTP client"""
        try:
            self.client = InferenceHTTPClient(
                api_url="https://serverless.roboflow.com",
                api_key=settings.roboflow_api_key
            )
            
            # Store workflow configuration from environment variables
            self.workspace_name = settings.roboflow_workspace
            self.workflow_id = settings.roboflow_license_plate_workflow_id
            
            if not self.workspace_name:
                raise ValueError("ROBOFLOW_WORKSPACE environment variable is required")
            if not settings.roboflow_api_key:
                raise ValueError("ROBOFLOW_API_KEY environment variable is required")
            
            # Convert confidence threshold (0-100 to 0-1 for comparison)
            self.confidence_threshold = settings.plate_detection_confidence / 100.0
            
            logger.info(f"Roboflow Workflow client initialized (workspace: {self.workspace_name}, workflow: {self.workflow_id})")
        except Exception as e:
            logger.error(f"Failed to initialize Roboflow Workflow client: {e}")
            logger.warning("License plate detector will not be available")
            self.client = None
    
    def detect_and_recognize(
        self,
        image: np.ndarray,
        camera_id: str,
        parking_lot_id: str
    ) -> List[LicensePlateDetection]:
        """
        Detect license plates and recognize text using Roboflow Workflow
        
        Args:
            image: OpenCV image (numpy array)
            camera_id: Camera identifier
            parking_lot_id: Parking lot identifier
            
        Returns:
            List of license plate detections with recognized text
        """
        start_time = time.time()
        temp_path = None
        
        try:
            # Lazy retry: if client failed to load at startup, try again now
            if self.client is None:
                logger.info("Retrying Roboflow Workflow client initialization...")
                self._init_workflow_client()
                if self.client is None:
                    raise RuntimeError("Roboflow Workflow client not available — check API key and network")
            
            # Convert to PIL Image and save to temporary file
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # Resize to max 640px for faster processing (workflow optimized for this size)
            max_dimension = 640
            scale_factor = 1.0
            if max(pil_image.size) > max_dimension:
                scale_factor = max_dimension / max(pil_image.size)
                new_size = (int(pil_image.width * scale_factor), int(pil_image.height * scale_factor))
                pil_image = pil_image.resize(new_size, Image.LANCZOS)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                pil_image.save(temp_path, quality=85)
            
            # Track API call time
            api_start = time.time()
            
            # Run workflow
            result = self.client.run_workflow(
                workspace_name=self.workspace_name,
                workflow_id=self.workflow_id,
                images={"image": temp_path},
                use_cache=True
            )
            
            # Track API time
            api_time = time.time() - api_start
            self.api_call_times.append(api_time)
            if len(self.api_call_times) > self.max_tracked_times:
                self.api_call_times.pop(0)
            
            # Parse workflow output
            detections = self._parse_workflow_output(result, scale_factor, camera_id, parking_lot_id, start_time)
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"Detected {len(detections)} plates in {processing_time:.2f}ms")
            
            return detections
            
        except Exception as e:
            logger.error(f"License plate detection failed: {e}")
            return []
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    def _parse_workflow_output(
        self,
        result: List[Dict],
        scale_factor: float,
        camera_id: str,
        parking_lot_id: str,
        start_time: float
    ) -> List[LicensePlateDetection]:
        """
        Parse workflow output and convert to LicensePlateDetection objects
        
        Args:
            result: Workflow API response
            scale_factor: Image scaling factor applied before detection
            camera_id: Camera identifier
            parking_lot_id: Parking lot identifier
            start_time: Detection start time
            
        Returns:
            List of LicensePlateDetection objects
        """
        detections = []
        
        try:
            if not result or len(result) == 0:
                return detections
            
            # Extract predictions and OCR text from workflow output
            workflow_output = result[0]
            predictions = workflow_output.get("predictions", {}).get("predictions", [])
            ocr_texts = workflow_output.get("ocr_text", [])
            
            # Match predictions with OCR text (workflow returns them in order)
            for idx, prediction in enumerate(predictions):
                # Filter by confidence threshold
                confidence = prediction.get("confidence", 0.0)
                if confidence < self.confidence_threshold:
                    continue
                
                # Get OCR text for this detection (if available)
                plate_text = ocr_texts[idx] if idx < len(ocr_texts) else ""
                
                # Skip if no text recognized
                if not plate_text or len(plate_text.strip()) < 3:
                    continue
                
                # Extract bounding box (convert from center coordinates to corner coordinates)
                x = int(prediction["x"] / scale_factor)
                y = int(prediction["y"] / scale_factor)
                width = int(prediction["width"] / scale_factor)
                height = int(prediction["height"] / scale_factor)
                
                x1 = x - width // 2
                y1 = y - height // 2
                x2 = x + width // 2
                y2 = y + height // 2
                
                # Create detection object
                detections.append(LicensePlateDetection(
                    plate_number=plate_text.strip().upper(),
                    confidence=confidence,
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    camera_id=camera_id,
                    parking_lot_id=parking_lot_id,
                    processing_time_ms=(time.time() - start_time) * 1000
                ))
            
        except Exception as e:
            logger.error(f"Failed to parse workflow output: {e}")
        
        return detections
    
    def get_avg_api_time(self) -> float:
        """Get average API call time in milliseconds"""
        if not self.api_call_times:
            return 0.0
        return sum(self.api_call_times) / len(self.api_call_times) * 1000
