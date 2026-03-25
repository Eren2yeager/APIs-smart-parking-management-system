"""
Real-time parking lot capacity monitoring stream processor
Handles frame skipping, capacity alerts, and state tracking
"""

import time
import os
import gc
from dotenv import load_dotenv
from .parking_detector import ParkingSlotDetector
from utils.config import Config
from utils.dynamic_frame_skipper import DynamicFrameSkipper

load_dotenv()


class ParkingStreamProcessor:
    """
    Processes video stream frames for parking lot capacity monitoring
    Features:
    - Frame skipping (parking status changes slowly)
    - Capacity alerts (near full)
    - State change detection
    """
    
    # Shared detector instance across all connections (saves memory)
    _shared_detector = None
    
    @classmethod
    def get_detector(cls):
        """Get or create shared detector instance"""
        if cls._shared_detector is None:
            cls._shared_detector = ParkingSlotDetector()
        return cls._shared_detector
    
    def __init__(self, skip_frames=None):
        """
        Initialize parking stream processor
        
        Args:
            skip_frames: Process every Nth frame (default from env or 10)
        """
        self.detector = self.get_detector()  # Use shared instance
        
        # Configuration
        self.use_dynamic_skipping = Config.use_dynamic_frame_skipping()
        
        if self.use_dynamic_skipping:
            # Use dynamic frame skipper
            initial_skip = skip_frames or int(os.getenv("LOT_FRAME_SKIP", "10"))
            self.frame_skipper = DynamicFrameSkipper(
                initial_skip=initial_skip,
                min_skip=2,
                max_skip=50,
                target_fps=5  # Parking changes slowly
            )
            self.skip_frames = initial_skip  # For reporting
        else:
            # Use fixed frame skipping
            self.skip_frames = skip_frames or int(os.getenv("LOT_FRAME_SKIP", "10"))
            self.frame_skipper = None
        
        # State
        self.frame_count = 0
        self.processed_count = 0
        self.last_occupancy = None
        
        # Removed verbose initialization log
    
    def should_process_frame(self):
        """Determine if current frame should be processed"""
        if self.use_dynamic_skipping:
            return self.frame_skipper.should_process_frame()
        else:
            return self.frame_count % self.skip_frames == 0
    
    def detect_state_change(self, current_occupancy):
        """
        Detect significant changes in parking occupancy
        
        Args:
            current_occupancy: Current number of occupied slots
            
        Returns:
            dict: Change information or None
        """
        if self.last_occupancy is None:
            self.last_occupancy = current_occupancy
            return None
        
        change = current_occupancy - self.last_occupancy
        
        if abs(change) >= 1:  # At least 1 slot changed
            change_info = {
                "previous": self.last_occupancy,
                "current": current_occupancy,
                "change": change,
                "direction": "increased" if change > 0 else "decreased"
            }
            self.last_occupancy = current_occupancy
            return change_info
        
        return None
    
    def process_frame(self, frame_bytes):
        """
        Process a single frame from video stream
        
        Args:
            frame_bytes: Image data as bytes
            
        Returns:
            dict: Processing result with slot statuses and metadata, or None if frame skipped
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
        
        # Detect parking slots
        result = self.detector.detect_slots(frame_bytes)
        
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
        
        # Extract data
        total_slots = result["total_slots"]
        occupied = result["occupied"]
        empty = result["empty"]
        occupancy_rate = result["occupancy_rate"]
        
        # Detect state changes
        state_change = self.detect_state_change(occupied)
        
        # Periodic garbage collection
        if self.frame_count % 50 == 0:
            gc.collect()
        
        self.processed_count += 1
        processing_time_ms = int(processing_time * 1000)
        
        response = {
            "success": True,
            "type": "capacity_update",
            "timestamp": time.time(),
            "frame_number": self.frame_count,
            "processed_frame_number": self.processed_count,
            "total_slots": total_slots,
            "occupied": occupied,
            "empty": empty,
            "occupancy_rate": occupancy_rate,
            "slots": result["slots"],
            "processing_time_ms": processing_time_ms
        }
        
        # Add state change info if detected
        if state_change:
            response["state_change"] = state_change
        
        # Add dynamic skip info if enabled
        if self.use_dynamic_skipping:
            response["current_skip_rate"] = self.frame_skipper.get_current_skip()
        
        return response
    
    def reset_state(self):
        """Reset processor state (for new session)"""
        self.frame_count = 0
        self.processed_count = 0
        self.last_occupancy = None
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
            "current_occupancy": self.last_occupancy
        }
