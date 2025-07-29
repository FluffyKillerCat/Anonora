from transformers import pipeline
from typing import List, Dict, Any, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class TaggingService:
    def __init__(self):
        self.model_name = settings.zero_shot_model
        self.classifier = None
        self._load_model()
        
        self.document_categories = [
            "legal document",
            "financial report",
            "medical record",
            "contract",
            "invoice",
            "receipt",
            "resume",
            "academic paper",
            "technical manual",
            "policy document",
            "news article",
            "research paper",
            "business plan",
            "proposal",
            "certificate",
            "license",
            "identification",
            "insurance document",
            "tax document",
            "employment contract"
        ]
    
    def _load_model(self):
        try:
            logger.info(f"Loading zero-shot classification model: {self.model_name}")
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=-1
            )
            logger.info("Zero-shot classification model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load zero-shot classification model: {e}")
            raise
    
    def classify_document(self, text: str, candidate_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if not self.classifier:
                raise Exception("Model not loaded")
            
            if candidate_labels is None:
                candidate_labels = self.document_categories
            
            max_length = 1000
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            result = self.classifier(
                sequences=text,
                candidate_labels=candidate_labels,
                hypothesis_template="This document is about {}."
            )
            
            classification_result = {
                'labels': result['labels'],
                'scores': result['scores'],
                'top_label': result['labels'][0] if result['labels'] else None,
                'top_score': result['scores'][0] if result['scores'] else 0.0
            }
            
            logger.info(f"Document classified as: {classification_result['top_label']} (score: {classification_result['top_score']:.3f})")
            return classification_result
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return {
                'labels': [],
                'scores': [],
                'top_label': None,
                'top_score': 0.0
            }
    
    def suggest_tags(self, text: str, max_tags: int = 5, confidence_threshold: float = 0.3) -> List[str]:
        try:
            classification = self.classify_document(text)
            
            suggested_tags = []
            for label, score in zip(classification['labels'], classification['scores']):
                if score >= confidence_threshold and len(suggested_tags) < max_tags:
                    suggested_tags.append(label)
            
            logger.info(f"Suggested {len(suggested_tags)} tags for document")
            return suggested_tags
            
        except Exception as e:
            logger.error(f"Tag suggestion failed: {e}")
            return []
    
    def classify_by_sections(self, text: str, section_size: int = 1000) -> Dict[str, Any]:
        try:
            sections = self._split_text_into_sections(text, section_size)
            
            section_classifications = []
            for i, section in enumerate(sections):
                classification = self.classify_document(section)
                section_classifications.append({
                    'section_id': i,
                    'text': section,
                    'classification': classification
                })
            
            overall_classification = self._aggregate_classifications(section_classifications)
            
            result = {
                'overall_classification': overall_classification,
                'section_classifications': section_classifications,
                'total_sections': len(sections)
            }
            
            logger.info(f"Classified document with {len(sections)} sections")
            return result
            
        except Exception as e:
            logger.error(f"Section-based classification failed: {e}")
            return {
                'overall_classification': {},
                'section_classifications': [],
                'total_sections': 0
            }
    
    def _aggregate_classifications(self, section_classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            all_scores = {}
            total_sections = len(section_classifications)
            
            for section in section_classifications:
                classification = section['classification']
                for label, score in zip(classification['labels'], classification['scores']):
                    if label not in all_scores:
                        all_scores[label] = []
                    all_scores[label].append(score)
            
            aggregated_scores = {}
            for label, scores in all_scores.items():
                avg_score = sum(scores) / len(scores)
                aggregated_scores[label] = avg_score
            
            sorted_labels = sorted(aggregated_scores.items(), key=lambda x: x[1], reverse=True)
            
            return {
                'labels': [label for label, _ in sorted_labels],
                'scores': [score for _, score in sorted_labels],
                'top_label': sorted_labels[0][0] if sorted_labels else None,
                'top_score': sorted_labels[0][1] if sorted_labels else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to aggregate classifications: {e}")
            return {
                'labels': [],
                'scores': [],
                'top_label': None,
                'top_score': 0.0
            }
    
    def _split_text_into_sections(self, text: str, section_size: int) -> List[str]:
        words = text.split()
        sections = []
        
        for i in range(0, len(words), section_size):
            section_words = words[i:i + section_size]
            section_text = " ".join(section_words)
            if section_text.strip():
                sections.append(section_text)
        
        return sections
    
    def get_document_categories(self) -> List[str]:
        return self.document_categories.copy()
    
    def add_custom_category(self, category: str):
        if category not in self.document_categories:
            self.document_categories.append(category)
            logger.info(f"Added custom category: {category}")
    
    def remove_category(self, category: str):
        if category in self.document_categories:
            self.document_categories.remove(category)
            logger.info(f"Removed category: {category}") 