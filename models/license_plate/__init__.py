"""
License Plate Recognition Module

This module provides a complete pipeline for license plate detection and recognition:
- detector.py: YOLO-based license plate detection
- reader.py: PaddleOCR-based text recognition
- pipeline.py: End-to-end recognition pipeline
- stream_processor.py: Real-time stream processing with deduplication
"""

from .detector import LicensePlateDetector
from .reader import PlateReader
from .pipeline import PlateRecognitionPipeline
from .stream_processor import PlateStreamProcessor

__all__ = [
    'LicensePlateDetector',
    'PlateReader',
    'PlateRecognitionPipeline',
    'PlateStreamProcessor'
]
