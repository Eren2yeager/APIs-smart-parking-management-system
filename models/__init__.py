<<<<<<< HEAD
from .license_plate_detector import LicensePlateDetectorModel
from .parking_slot_detector import ParkingSlotDetectorModel
from .vehicle_detector import VehicleDetectorModel

__all__ = [
    "LicensePlateDetectorModel",
    "ParkingSlotDetectorModel",
    "VehicleDetectorModel"
=======
# Models package
from .license_plate import PlateReader, LicensePlateDetector, PlateRecognitionPipeline

__all__ = [
    'PlateReader',
    'LicensePlateDetector',
    'PlateRecognitionPipeline'
>>>>>>> main
]
