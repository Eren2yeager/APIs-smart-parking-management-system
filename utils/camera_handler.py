import cv2
import time
import os
from dotenv import load_dotenv

load_dotenv()


class CameraHandler:
    def __init__(self, source=None):
        """
        Initialize camera handler
        source: 0 for webcam, or RTSP URL for IP camera
        Example: 'rtsp://username:password@ip_address:port/stream'
        If source is None, reads from CAMERA_SOURCE env variable
        """
        if source is None:
            source = os.getenv("CAMERA_SOURCE", "0")
            # Convert to int if it's a numeric string (webcam index)
            try:
                source = int(source)
            except ValueError:
                pass  # Keep as string (RTSP URL)
        
        self.source = source
        self.cap = None

    
    
    def start(self):
        """Start camera capture"""
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise Exception(f"Failed to open camera source: {self.source}")
        return True
    
    def read_frame(self):
        """Read a single frame from camera"""
        if self.cap is None:
            raise Exception("Camera not started. Call start() first.")
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame
    
    def frame_to_bytes(self, frame):
    # Convert numpy array to JPEG bytes
        pass
     
    def release(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def __del__(self):
        self.release()
