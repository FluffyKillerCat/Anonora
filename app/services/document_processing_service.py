from app.services.ocr_service import OCRService
from app.services.pdf_service import PDFService
from app.services.anonymization_service import AnonymizationService
from app.services.embedding_service import EmbeddingService
from app.services.tagging_service import TaggingService
from app.models.document import DocumentType, DocumentStatus
from typing import Dict, Any, Optional, List
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    def __init__(self):
        self.ocr_service = OCRService()
        self.pdf_service = PDFService()
        self.anonymization_service = AnonymizationService()
        self.embedding_service = EmbeddingService()
        self.tagging_service = TaggingService()
    
    def process_document(self, file_path: str, document_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"Starting document processing for: {file_path}")
            
            document_type = self._determine_document_type(file_path)
            extracted_text = self._extract_text(file_path, document_type)
            
            if not extracted_text.strip():
                raise Exception("No text could be extracted from the document")
            
            anonymization_result = self.anonymization_service.anonymize_text(extracted_text)
            anonymized_text = anonymization_result['anonymized_text']
            
            embedding = self.embedding_service.create_embedding(anonymized_text)
            suggested_tags = self.tagging_service.suggest_tags(extracted_text)
            
            result = {
                'document_id': document_id,
                'document_type': document_type.value,
                'extracted_text': extracted_text,
                'anonymized_text': anonymized_text,
                'embedding': embedding,
                'suggested_tags': suggested_tags,
                'pii_summary': self.anonymization_service.get_pii_summary(extracted_text),
                'processing_status': 'completed',
                'processed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Document processing completed successfully for: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed for {file_path}: {e}")
            return {
                'document_id': document_id,
                'processing_status': 'failed',
                'error_message': str(e),
                'processed_at': datetime.utcnow().isoformat()
            }
    
    def _determine_document_type(self, file_path: str) -> DocumentType:
        try:
            if self.pdf_service.is_digital_pdf(file_path):
                return DocumentType.PDF
            
            if self.ocr_service.is_scanned_pdf(file_path):
                return DocumentType.SCANNED_PDF
            
            return DocumentType.PDF
            
        except Exception as e:
            logger.error(f"Error determining document type: {e}")
            return DocumentType.PDF
    
    def _extract_text(self, file_path: str, document_type: DocumentType) -> str:
        try:
            if document_type == DocumentType.SCANNED_PDF:
                logger.info("Using OCR for scanned PDF")
                return self.ocr_service.extract_text_from_pdf(file_path)
            else:
                logger.info("Using direct text extraction for digital PDF")
                return self.pdf_service.extract_text_from_pdf(file_path)
                
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    def process_document_async(self, file_path: str, document_id: str) -> str:
        try:
            from app.celery_app import process_document_task
            task = process_document_task.delay(file_path, document_id)
            return task.id
        except Exception as e:
            logger.error(f"Failed to start async processing: {e}")
            raise
    
    def get_processing_status(self, task_id: str) -> Dict[str, Any]:
        try:
            from app.celery_app import process_document_task
            task = process_document_task.AsyncResult(task_id)
            return {
                'task_id': task_id,
                'status': task.status,
                'result': task.result if task.ready() else None
            }
        except Exception as e:
            logger.error(f"Failed to get processing status: {e}")
            return {'task_id': task_id, 'status': 'unknown', 'result': None}
    
    def extract_text_only(self, file_path: str) -> Dict[str, Any]:
        try:
            document_type = self._determine_document_type(file_path)
            extracted_text = self._extract_text(file_path, document_type)
            
            return {
                'extracted_text': extracted_text,
                'document_type': document_type.value,
                'success': bool(extracted_text.strip())
            }
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                'extracted_text': '',
                'document_type': DocumentType.PDF.value,
                'success': False,
                'error': str(e)
            }
    
    def anonymize_text_only(self, text: str) -> Dict[str, Any]:
        try:
            result = self.anonymization_service.anonymize_text(text)
            return {
                'anonymized_text': result['anonymized_text'],
                'entities_found': result['entities_found'],
                'success': True
            }
        except Exception as e:
            logger.error(f"Text anonymization failed: {e}")
            return {
                'anonymized_text': text,
                'entities_found': 0,
                'success': False,
                'error': str(e)
            }
    
    def create_embeddings_only(self, text: str) -> Optional[List[float]]:
        try:
            return self.embedding_service.create_embedding(text)
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")
            return None
    
    def suggest_tags_only(self, text: str) -> List[str]:
        try:
            return self.tagging_service.suggest_tags(text)
        except Exception as e:
            logger.error(f"Tag suggestion failed: {e}")
            return []
    
    def search_similar_documents(self, query: str, document_embeddings: List[Dict[str, Any]], 
                                threshold: float = None) -> List[Dict[str, Any]]:
        try:
            query_embedding = self.embedding_service.create_embedding(query)
            if not query_embedding:
                return []
            
            similar_documents = []
            for doc in document_embeddings:
                if 'embedding' in doc and doc['embedding']:
                    similarity = self.embedding_service.calculate_similarity(
                        query_embedding, doc['embedding']
                    )
                    
                    if threshold is None or similarity >= threshold:
                        doc_copy = doc.copy()
                        doc_copy['similarity_score'] = similarity
                        similar_documents.append(doc_copy)
            
            similar_documents.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_documents
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []
    
    def get_processing_services_status(self) -> Dict[str, bool]:
        try:
            return {
                'ocr_service': True,
                'pdf_service': True,
                'anonymization_service': True,
                'embedding_service': self.embedding_service.model is not None,
                'tagging_service': self.tagging_service.classifier is not None
            }
        except Exception as e:
            logger.error(f"Failed to get services status: {e}")
            return {
                'ocr_service': False,
                'pdf_service': False,
                'anonymization_service': False,
                'embedding_service': False,
                'tagging_service': False
            } 