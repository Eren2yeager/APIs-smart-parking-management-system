"""
Parking Slot Detection Model
Uses Roboflow Workflow API for parking slot occupancy detection
"""

from inference_sdk import InferenceHTTPClient
import cv2
import numpy as np
import tempfile
import os
import time
from typing import List
from PIL import Image

from config.settings import settings
from utils.logger import logger
from utils.slot_sorter import assign_sorted_slot_ids
from schemas.detection_result import ParkingSlotDetection, ParkingSlotDetectionResult, BoundingBox


class ParkingSlotDetectorModel:
    """Parking slot occupancy detection model using Roboflow Workflow API"""
    
    def __init__(self):
        """Initialize Roboflow Workflow client"""
        self.client = None
        self._init_workflow_client()
        
        if self.client:
            logger.info("Parking Slot Detector initialized successfully (Workflow API)")
        else:
            logger.warning("Parking Slot Detector initialized WITHOUT client (will retry on first request)")
    
    def _init_workflow_client(self):
        """Initialize Roboflow Workflow HTTP client"""
        try:
            self.client = InferenceHTTPClient(
                api_url="https://serverless.roboflow.com",
                api_key=settings.roboflow_api_key
            )
            
            # Store workflow configuration from environment variables
            self.workspace_name = settings.roboflow_workspace
            self.workflow_id = settings.roboflow_parking_slot_workflow_id
            
            if not self.workspace_name:
                raise ValueError("ROBOFLOW_WORKSPACE environment variable is required")
            if not settings.roboflow_api_key:
                raise ValueError("ROBOFLOW_API_KEY environment variable is required")
            
            # Convert confidence threshold (0-100 to 0-1 for comparison)
            self.confidence_threshold = settings.parking_slot_confidence / 100.0
            
            logger.info(f"Roboflow Workflow client initialized (workspace: {self.workspace_name}, workflow: {self.workflow_id})")
        except Exception as e:
            logger.error(f"Failed to initialize Roboflow Workflow client: {e}")
            logger.warning("Parking slot detector will not be available")
            self.client = None
    
    def detect_slots(
        self,
        image: np.ndarray,
        camera_id: str,
        parking_lot_id: str
    ) -> ParkingSlotDetectionResult:
        """
        Detect parking slot occupancy using Roboflow Workflow
        
        Args:
            image: OpenCV image (numpy array)
            camera_id: Camera identifier
            parking_lot_id: Parking lot identifier
            
        Returns:
            ParkingSlotDetectionResult with all slot statuses
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
            
            # Save to temporary file (workflow handles optimal sizing)
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                pil_image.save(temp_path, quality=85)
            
            # Run workflow
            result = self.client.run_workflow(
                workspace_name=self.workspace_name,
                workflow_id=self.workflow_id,
                images={"image": temp_path},
                use_cache=True
            )
            
            # Parse workflow output
            return self._parse_workflow_output(result, camera_id, parking_lot_id, start_time)
            
        except Exception as e:
            logger.error(f"Parking slot detection failed: {e}")
            # Return empty result on error
            return ParkingSlotDetectionResult(
                parking_lot_id=parking_lot_id,
                camera_id=camera_id,
                total_slots=0,
                occupied=0,
                empty=0,
                occupancy_rate=0.0,
                slots=[],
                processing_time_ms=(time.time() - start_time) * 1000
            )
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    def _parse_workflow_output(
        self,
        result: List,
        camera_id: str,
        parking_lot_id: str,
        start_time: float
    ) -> ParkingSlotDetectionResult:
        """
        Parse workflow output and convert to ParkingSlotDetectionResult
        
        Args:
            result: Workflow API response
            camera_id: Camera identifier
            parking_lot_id: Parking lot identifier
            start_time: Detection start time
            
        Returns:
            ParkingSlotDetectionResult object
        """
        occupied_count = 0
        empty_count = 0
        slots = []
        
        try:
            if not result or len(result) == 0:
                return ParkingSlotDetectionResult(
                    parking_lot_id=parking_lot_id,
                    camera_id=camera_id,
                    total_slots=0,
                    occupied=0,
                    empty=0,
                    occupancy_rate=0.0,
                    slots=[],
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Extract predictions from workflow output
            workflow_output = result[0]
            predictions = workflow_output.get("predictions", {}).get("predictions", [])
            
            # Sort predictions by position (left to right, row by row) and assign sorted slot IDs
            # This ensures consistent slot ordering regardless of how Roboflow groups them
            predictions = assign_sorted_slot_ids(predictions, row_threshold=50)
            
            # Process each prediction
            for prediction in predictions:
                # Filter by confidence threshold
                confidence = prediction.get("confidence", 0.0)
                if confidence < self.confidence_threshold:
                    continue
                
                # Get class (parked-vehicle = occupied, empty-parking-slot = empty)
                predicted_class = prediction.get("class", "")
                
                # Map workflow classes to our status format
                if predicted_class == "parked-vehicle":
                    status = "occupied"
                    occupied_count += 1
                elif predicted_class == "empty-parking-slot":
                    status = "empty"
                    empty_count += 1
                else:
                    # Unknown class, skip
                    continue
                
                # Extract bounding box (convert from center coordinates to corner coordinates)
                x = int(prediction["x"])
                y = int(prediction["y"])
                width = int(prediction["width"])
                height = int(prediction["height"])
                
                x1 = x - width // 2
                y1 = y - height // 2
                x2 = x + width // 2
                y2 = y + height // 2
                
                # Create slot detection object
                # Use the sorted_slot_id assigned by the sorting utility
                slot_id = prediction.get('sorted_slot_id', len(slots) + 1)
                
                slots.append(ParkingSlotDetection(
                    slot_id=slot_id,
                    status=status,
                    confidence=confidence,
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                ))
            
            total_slots = occupied_count + empty_count
            occupancy_rate = occupied_count / total_slots if total_slots > 0 else 0.0
            processing_time = (time.time() - start_time) * 1000
            
            logger.debug(f"Detected {total_slots} slots ({occupied_count} occupied, {empty_count} empty) in {processing_time:.2f}ms")
            
            return ParkingSlotDetectionResult(
                parking_lot_id=parking_lot_id,
                camera_id=camera_id,
                total_slots=total_slots,
                occupied=occupied_count,
                empty=empty_count,
                occupancy_rate=occupancy_rate,
                slots=slots,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to parse workflow output: {e}")
            return ParkingSlotDetectionResult(
                parking_lot_id=parking_lot_id,
                camera_id=camera_id,
                total_slots=0,
                occupied=0,
                empty=0,
                occupancy_rate=0.0,
                slots=[],
                processing_time_ms=(time.time() - start_time) * 1000
            )
