"""
Configuration utility for environment-based settings
Handles development vs production mode configurations
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration manager"""
    
    @staticmethod
    def get_environment():
        """Get current environment (development or production)"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        return env if env in ["development", "production"] else "development"
    
    @staticmethod
    def is_development():
        """Check if running in development mode"""
        return Config.get_environment() == "development"
    
    @staticmethod
    def is_production():
        """Check if running in production mode"""
        return Config.get_environment() == "production"
    
    @staticmethod
    def use_dynamic_frame_skipping():
        """Check if dynamic frame skipping is enabled"""
        return os.getenv("DYNAMIC_FRAME_SKIPPING", "false").lower() == "true"
    
    @staticmethod
    def get_ocr_engine():
        """Get OCR engine based on environment"""
        # Development: PaddleOCR (faster)
        # Production: EasyOCR (more accurate)
        return "paddleocr" if Config.is_development() else "easyocr"
    
    @staticmethod
    def get_config_summary():
        """Get configuration summary for logging"""
        return {
            "environment": Config.get_environment(),
            "ocr_engine": Config.get_ocr_engine(),
            "detection": "Roboflow API",  # Always Roboflow now
            "dynamic_frame_skipping": Config.use_dynamic_frame_skipping()
        }
