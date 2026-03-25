# License Plate Recognition Module

This module provides a complete two-stage pipeline for license plate detection and recognition.

## Structure

```
models/license_plate/
├── __init__.py          # Module exports
├── detector.py          # YOLO-based plate detection
├── reader.py            # PaddleOCR-based text recognition
├── pipeline.py          # End-to-end recognition pipeline
└── README.md            # This file
```

## Components

### 1. LicensePlateDetector (`detector.py`)
- Uses YOLOv8 for license plate detection
- Auto-downloads model from Hugging Face if not present
- Provides plate detection and cropping functionality

### 2. PlateReader (`reader.py`)
- Uses PaddleOCR for text recognition
- Optimized for license plate text extraction
- Handles text cleaning and confidence scoring

### 3. PlateRecognitionPipeline (`pipeline.py`)
- Combines detection and recognition
- Two-stage process: detect → crop → OCR
- Debug mode for saving intermediate results

## Usage

```python
from models.license_plate import PlateRecognitionPipeline

# Initialize pipeline
pipeline = PlateRecognitionPipeline(debug=False)

# Process image
with open('image.jpg', 'rb') as f:
    image_bytes = f.read()
    result = pipeline.process(image_bytes)

print(result)
```

## Configuration

Environment variables (in `.env`):
- `LICENSE_PLATE_MODEL`: Path to YOLO model (default: `license_plate_detector.pt`)
- `PLATE_DETECTION_CONFIDENCE`: Detection threshold (default: `0.3`)
- `DETECTION_CONFIDENCE`: OCR confidence threshold (default: `0.5`)
- `DEBUG_MODE`: Enable debug output (default: `false`)
