"""
Real-time license plate recognition stream processor
Handles frame skipping, deduplication, and session state management
"""

import time
import os
import gc
from dotenv import load_dotenv
from .pipeline import PlateRecognitionPipeline
from utils.config import Config
from utils.dynamic_frame_skipper import DynamicFrameSkipper

load_dotenv()


class PlateStreamProcessor:
    """
    Processes video stream frames for license plate recognition
    Features:
    - Frame skipping for performance
    - Deduplication (ignore same plate for N seconds)
    - Session state management
    """
    
    # Shared pipeline instance across all connections (saves memory)
    _shared_pipeline = None
    
    @classmethod
    def get_pipeline(cls):
        """Get or create shared pipeline instance"""
        if cls._shared_pipeline is None:
            cls._shared_pipeline = PlateRecognitionPipeline()
        return cls._shared_pipeline
    
    def __init__(self, skip_frames=None, dedup_window=None):
        """
        Initialize stream processor
        
        Args:
            skip_frames: Process every Nth frame (default from env or 5)
            dedup_window: Ignore duplicate plates for N seconds (default from env or 10)
        """
        self.pipeline = self.get_pipeline()  # Use shared instance
        
        # Configuration
        self.use_dynamic_skipping = Config.use_dynamic_frame_skipping()
        
        if self.use_dynamic_skipping:
            # Use dynamic frame skipper
            initial_skip = skip_frames or int(os.getenv("GATE_FRAME_SKIP", "5"))
            self.frame_skipper = DynamicFrameSkipper(
                initial_skip=initial_skip,
                min_skip=1,
                max_skip=30,
                target_fps=10
            )
            self.skip_frames = initial_skip  # For reporting
        else:
            # Use fixed frame skipping
            self.skip_frames = skip_frames or int(os.getenv("GATE_FRAME_SKIP", "5"))
            self.frame_skipper = None
        
        self.dedup_window = dedup_window or int(os.getenv("GATE_DEDUP_WINDOW", "10"))
        
        # State
        self.frame_count = 0
        self.processed_count = 0
        self.seen_plates = {}  # {plate_number: last_seen_timestamp}
        self.max_tracked_plates = 100  # Limit memory usage
        
        # Removed verbose initialization log
    
    def should_process_frame(self):
        """Determine if current frame should be processed"""
        if self.use_dynamic_skipping:
            return self.frame_skipper.should_process_frame()
        else:
            return self.frame_count % self.skip_frames == 0
    
    def is_duplicate(self, plate_number):
        """
        Check if plate was recently seen
        
        Args:
            plate_number: License plate text
            
        Returns:
            bool: True if duplicate (seen within dedup_window)
        """
        current_time = time.time()
        
        if plate_number in self.seen_plates:
            last_seen = self.seen_plates[plate_number]
            time_diff = current_time - last_seen
            
            if time_diff < self.dedup_window:
                return True
        
        # Update last seen time
        self.seen_plates[plate_number] = current_time
        return False
    
    def cleanup_old_plates(self):
        """Remove plates older than dedup_window from memory"""
        current_time = time.time()
        plates_to_remove = []
        
        for plate_number, last_seen in self.seen_plates.items():
            if current_time - last_seen > self.dedup_window * 2:
                plates_to_remove.append(plate_number)
        
        for plate_number in plates_to_remove:
            del self.seen_plates[plate_number]
        
        # Hard limit: Keep only most recent plates if too many
        if len(self.seen_plates) > self.max_tracked_plates:
            # Sort by timestamp and keep only recent ones
            sorted_plates = sorted(self.seen_plates.items(), key=lambda x: x[1], reverse=True)
            self.seen_plates = dict(sorted_plates[:self.max_tracked_plates])
    
    def process_frame(self, frame_bytes):
        """
        Process a single frame from video stream
        
        Args:
            frame_bytes: Image data as bytes
            
        Returns:
            dict: Processing result with plates and metadata, or None if frame skipped
        """
        if self.use_dynamic_skipping:
            self.frame_count = self.frame_skipper.frame_count
        else:
            self.frame_count += 1
        
        start_time = time.time()
        
        # Frame skipping
        if not self.should_process_frame():
            # Delete frame immediately if skipped
            del frame_bytes
            return None
        
        # Process with pipeline
        result = self.pipeline.process(frame_bytes)
        
        # Delete frame_bytes immediately after processing
        del frame_bytes
        
        # Record processing time for dynamic skipping
        processing_time = time.time() - start_time
        if self.use_dynamic_skipping:
            self.frame_skipper.record_processing_time(processing_time)
        
        if not result.get("success"):
            gc.collect()  # Clean up on error
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "frame_number": self.frame_count,
                "timestamp": time.time()
            }
        
        # Mark new vs duplicate plates
        plates_with_status = []
        for plate in result.get("plates", []):
            plate_number = plate["plate_number"]
            is_new = not self.is_duplicate(plate_number)
            
            plates_with_status.append({
                "plate_number": plate_number,
                "raw_text": plate.get("raw_text", ""),
                "confidence": plate["ocr_confidence"],
                "detection_confidence": plate["detection_confidence"],
                "bbox": plate["bbox"],
                "is_new": is_new
            })
        
        # Cleanup old entries more frequently
        if self.frame_count % 50 == 0:  # Every 50 frames instead of 100
            self.cleanup_old_plates()
            gc.collect()  # Force garbage collection
        
        self.processed_count += 1
        processing_time_ms = int(processing_time * 1000)
        
        response = {
            "success": True,
            "type": "plate_detection",
            "timestamp": time.time(),
            "frame_number": self.frame_count,
            "processed_frame_number": self.processed_count,
            "plates": plates_with_status,
            "plates_detected": len(plates_with_status),
            "new_plates": sum(1 for p in plates_with_status if p["is_new"]),
            "processing_time_ms": processing_time_ms
        }
        
        # Add dynamic skip info if enabled
        if self.use_dynamic_skipping:
            response["current_skip_rate"] = self.frame_skipper.get_current_skip()
        
        return response
    
    def reset_state(self):
        """Reset processor state (for new session)"""
        self.frame_count = 0
        self.processed_count = 0
        self.seen_plates.clear()
        if self.use_dynamic_skipping:
            self.frame_skipper.reset()
        gc.collect()  # Clean up memory
        # State reset (silent)
    
    def get_stats(self):
        """Get processor statistics"""
        return {
            "total_frames": self.frame_count,
            "processed_frames": self.processed_count,
            "skip_rate": f"1/{self.skip_frames}",
            "tracked_plates": len(self.seen_plates)
        }
