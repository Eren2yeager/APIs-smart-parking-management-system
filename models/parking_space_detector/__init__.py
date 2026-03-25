"""
Parking Space Detection Module

Detects and monitors parking slot occupancy
- parking_detector.py: Roboflow-based slot detection
- stream_processor.py: Real-time capacity monitoring
"""

from .parking_detector import ParkingSlotDetector
from .stream_processor import ParkingStreamProcessor

__all__ = ['ParkingSlotDetector', 'ParkingStreamProcessor']
