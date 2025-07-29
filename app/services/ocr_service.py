import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np

import logging


logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        self.languages = ['eng']
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        try:
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            processed_image = self._preprocess_image(opencv_image)
            
            pil_image = Image.fromarray(processed_image)
            
            text = pytesseract.image_to_string(
                pil_image,
                lang='+'.join(self.languages),
                config='--psm 6'
            )
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            denoised = cv2.fastNlMeansDenoising(gray)
            
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return processed
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=300,
                fmt='PNG'
            )
            
            extracted_texts = []
            
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}")
                page_text = self.extract_text_from_image(image)
                if page_text.strip():
                    extracted_texts.append(page_text)
            
            full_text = "\n\n".join(extracted_texts)
            
            logger.info(f"Successfully extracted text from {len(images)} pages")
            return full_text
            
        except Exception as e:
            logger.error(f"PDF OCR extraction failed: {e}")
            return ""
    
    def is_scanned_pdf(self, pdf_path: str) -> bool:
        try:
            images = pdf2image.convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
            if not images:
                return False
            
            sample_image = images[0]
            text = self.extract_text_from_image(sample_image)
            
            return len(text.strip()) > 10
            
        except Exception as e:
            logger.error(f"Failed to determine if PDF is scanned: {e}")
            return False 