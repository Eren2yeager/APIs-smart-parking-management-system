"""
Frame utility functions for video stream processing
Handles conversions between different image formats
"""

import base64
import numpy as np
from io import BytesIO
from PIL import Image
import cv2


def base64_to_bytes(base64_str):
    """Convert base64 string to image bytes"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        image_bytes = base64.b64decode(base64_str)
        return image_bytes
    except Exception as e:
        raise ValueError(f"Failed to decode base64: {str(e)}")


def bytes_to_numpy(image_bytes):
    """Convert image bytes to numpy array"""
    try:
        image = Image.open(BytesIO(image_bytes))
        return np.array(image)
    except Exception as e:
        raise ValueError(f"Failed to convert bytes to numpy: {str(e)}")


def numpy_to_bytes(numpy_array, format='JPEG'):
    """Convert numpy array to image bytes"""
    try:
        image = Image.fromarray(numpy_array)
        buffer = BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to convert numpy to bytes: {str(e)}")


def resize_frame(frame, max_width=1280, max_height=720):
    """Resize frame while maintaining aspect ratio"""
    height, width = frame.shape[:2]
    
    if width <= max_width and height <= max_height:
        return frame
    
    scale = min(max_width / width, max_height / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
