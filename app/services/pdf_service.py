import PyPDF2
import pdfplumber
from typing import Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class PDFService:
    def __init__(self):
        self.extractors = {
            'pypdf2': self._extract_with_pypdf2,
            'pdfplumber': self._extract_with_pdfplumber
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            text = self._extract_with_pdfplumber(pdf_path)
            
            if text.strip():
                logger.info("Successfully extracted text using pdfplumber")
                return text
            
            text = self._extract_with_pypdf2(pdf_path)
            
            if text.strip():
                logger.info("Successfully extracted text using PyPDF2")
                return text
            
            logger.warning("No text extracted from PDF")
            return ""
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text)
                
                return "\n\n".join(texts)
                
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return ""
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                texts = []
                
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text)
                
                return "\n\n".join(texts)
                
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""
    
    def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        try:
            metadata = {}
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if pdf.metadata:
                        metadata.update(pdf.metadata)
            except:
                pass
            
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    if pdf_reader.metadata:
                        metadata.update(pdf_reader.metadata)
            except:
                pass
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {e}")
            return {}
    
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        try:
            info = {
                'file_size': os.path.getsize(pdf_path),
                'metadata': self.get_pdf_metadata(pdf_path)
            }
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    info['page_count'] = len(pdf.pages)
                    info['is_digital'] = True
            except:
                try:
                    with open(pdf_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        info['page_count'] = len(pdf_reader.pages)
                        info['is_digital'] = True
                except:
                    info['is_digital'] = False
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            return {}
    
    def is_digital_pdf(self, pdf_path: str) -> bool:
        try:
            text = self.extract_text_from_pdf(pdf_path)
            return len(text.strip()) > 50
        except Exception as e:
            logger.error(f"Failed to determine PDF type: {e}")
            return False 