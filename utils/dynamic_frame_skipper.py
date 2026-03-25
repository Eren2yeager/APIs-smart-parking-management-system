"""
Dynamic frame skipping utility
Adjusts frame skip rate based on processing time to maintain real-time performance
"""

import time
from collections import deque


class DynamicFrameSkipper:
    """
    Dynamically adjusts frame skip rate based on processing performance
    
    Strategy:
    - If processing is fast, reduce skip rate (process more frames)
    - If processing is slow, increase skip rate (process fewer frames)
    - Maintains a target processing time per frame
    """
    
    def __init__(self, initial_skip=5, min_skip=1, max_skip=50, target_fps=10):
        """
        Initialize dynamic frame skipper
        
        Args:
            initial_skip: Starting frame skip value
            min_skip: Minimum skip value (1 = process every frame)
            max_skip: Maximum skip value (increased to 50 for slow processing)
            target_fps: Target processing rate (frames per second)
        """
        self.skip_frames = initial_skip
        self.min_skip = min_skip
        self.max_skip = max_skip
        self.target_frame_time = 1.0 / target_fps  # Target time per processed frame
        
        # Track recent processing times
        self.processing_times = deque(maxlen=10)  # Last 10 processing times
        self.frame_count = 0
        self.last_adjustment_frame = 0
        self.adjustment_interval = 10  # Adjust every 10 frames (more responsive)
    
    def should_process_frame(self):
        """Determine if current frame should be processed"""
        self.frame_count += 1
        return self.frame_count % self.skip_frames == 0
    
    def record_processing_time(self, processing_time_seconds):
        """
        Record processing time and adjust skip rate if needed
        
        Args:
            processing_time_seconds: Time taken to process the frame
        """
        self.processing_times.append(processing_time_seconds)
        
        # Only adjust periodically
        if self.frame_count - self.last_adjustment_frame >= self.adjustment_interval:
            self._adjust_skip_rate()
            self.last_adjustment_frame = self.frame_count
    
    def _adjust_skip_rate(self):
        """Adjust frame skip rate based on recent performance"""
        if len(self.processing_times) < 5:
            return  # Need enough samples
        
        # Calculate average processing time
        avg_time = sum(self.processing_times) / len(self.processing_times)
        
        # Calculate how much time we have per frame at current skip rate
        available_time = self.target_frame_time * self.skip_frames
        
        # Adjust skip rate
        if avg_time < available_time * 0.6:
            # Processing is fast, can process more frames
            new_skip = max(self.min_skip, self.skip_frames - 1)
            if new_skip != self.skip_frames:
                self.skip_frames = new_skip
                # print(f"⚡ Dynamic skip: {self.skip_frames} (faster processing)")
        
        elif avg_time > available_time * 0.9:
            # Processing is slow, need to skip more frames
            new_skip = min(self.max_skip, self.skip_frames + 2)
            if new_skip != self.skip_frames:
                self.skip_frames = new_skip
                # print(f"🐌 Dynamic skip: {self.skip_frames} (slower processing)")
    
    def get_current_skip(self):
        """Get current frame skip value"""
        return self.skip_frames
    
    def reset(self):
        """Reset state"""
        self.processing_times.clear()
        self.frame_count = 0
        self.last_adjustment_frame = 0
