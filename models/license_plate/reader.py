import os
from dotenv import load_dotenv
import sys
import warnings

# Load environment variables FIRST
load_dotenv()

from utils.config import Config
import numpy as np
from io import BytesIO
from PIL import Image
import re
import cv2
import logging


class PlateReader:
    def __init__(self):
        self.ocr_engine = Config.get_ocr_engine()
        self.min_confidence = float(os.getenv("DETECTION_CONFIDENCE", "0.5"))
        self.debug = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        if self.ocr_engine == "paddleocr":
            self._init_paddleocr()
        else:
            self._init_easyocr()
    
    def _init_paddleocr(self):
        """Initialize PaddleOCR (development mode)"""
        print("Loading PaddleOCR (development mode)...")
        
        # Suppress output during initialization
        import io
        _stderr = sys.stderr
        sys.stderr = io.StringIO()
        
        try:
            from paddleocr import PaddleOCR
            logging.getLogger('ppocr').setLevel(logging.ERROR)
            logging.getLogger('paddlex').setLevel(logging.ERROR)
            self.reader = PaddleOCR(lang='en', use_angle_cls=False)
            self.reader_type = "paddleocr"
        finally:
            sys.stderr = _stderr
        
        print("PaddleOCR ready!")
    
    def _init_easyocr(self):
        """Initialize EasyOCR (production mode)"""
        print("Loading EasyOCR (production mode)...")
        
        try:
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=True)
            self.reader_type = "easyocr"
        except Exception as e:
            print(f"⚠️  EasyOCR GPU failed, falling back to CPU: {e}")
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=False)
            self.reader_type = "easyocr"
        
        print("EasyOCR ready!")
    
    def read_from_cropped(self, cropped_image_np):
        """Read text from a cropped license plate image (numpy array)"""
        try:
            if self.reader_type == "paddleocr":
                return self._read_paddleocr(cropped_image_np)
            else:
                return self._read_easyocr(cropped_image_np)
        except Exception as e:
            if self.debug:
                print(f"OCR Error: {e}")
            return None
    
    def _read_paddleocr(self, cropped_image_np):
        """Read text using PaddleOCR"""
        results = self.reader.ocr(cropped_image_np)
        
        if not results or not results[0]:
            return None
        
        result_dict = results[0]
        
        if 'rec_texts' not in result_dict or not result_dict['rec_texts']:
            return None
        
        texts = result_dict['rec_texts']
        scores = result_dict.get('rec_scores', [1.0] * len(texts))
        
        # Collect valid results (at least 3 alphanumeric characters)
        all_texts = []
        for text, confidence in zip(texts, scores):
            cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
            if len(cleaned) >= 3:
                all_texts.append({
                    "text": cleaned,
                    "raw": text,
                    "conf": confidence
                })
        
        if not all_texts:
            return None
        
        # Get best result by confidence
        best = max(all_texts, key=lambda x: x["conf"])
        
        # If multiple results, combine them
        if len(all_texts) > 1:
            combined_text = ''.join([t["text"] for t in all_texts])
            combined_raw = ' '.join([t["raw"] for t in all_texts])
            avg_conf = sum([t["conf"] for t in all_texts]) / len(all_texts)
            
            if len(combined_text) > len(best["text"]) and avg_conf > 0.3:
                best = {
                    "text": combined_text,
                    "raw": combined_raw,
                    "conf": avg_conf
                }

        return {
            "text": best["text"],
            "raw_text": best["raw"],
            "confidence": round(best["conf"], 2)
        }
    
    def _read_easyocr(self, cropped_image_np):
        """Read text using EasyOCR"""
        results = self.reader.readtext(cropped_image_np)
        
        if not results:
            return None
        
        # Collect valid results (at least 3 alphanumeric characters)
        all_texts = []
        for (bbox, text, confidence) in results:
            cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
            if len(cleaned) >= 3:
                all_texts.append({
                    "text": cleaned,
                    "raw": text,
                    "conf": confidence
                })
        
        if not all_texts:
            return None
        
        # Get best result by confidence
        best = max(all_texts, key=lambda x: x["conf"])
        
        # If multiple results, combine them
        if len(all_texts) > 1:
            combined_text = ''.join([t["text"] for t in all_texts])
            combined_raw = ' '.join([t["raw"] for t in all_texts])
            avg_conf = sum([t["conf"] for t in all_texts]) / len(all_texts)
            
            if len(combined_text) > len(best["text"]) and avg_conf > 0.3:
                best = {
                    "text": combined_text,
                    "raw": combined_raw,
                    "conf": avg_conf
                }

        return {
            "text": best["text"],
            "raw_text": best["raw"],
            "confidence": round(best["conf"], 2)
        }
