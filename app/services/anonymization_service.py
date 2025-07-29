from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AnonymizationService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.language = "en"
        
        self.operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[PERSON]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CREDIT_CARD]"}),
            "IBAN_CODE": OperatorConfig("replace", {"new_value": "[IBAN]"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[IP_ADDRESS]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "[DATE]"}),
            "NRP": OperatorConfig("replace", {"new_value": "[NRP]"}),
            "MEDICAL_LICENSE": OperatorConfig("replace", {"new_value": "[MEDICAL_LICENSE]"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "[SSN]"}),
            "US_PASSPORT": OperatorConfig("replace", {"new_value": "[PASSPORT]"}),
            "CRYPTO": OperatorConfig("replace", {"new_value": "[CRYPTO]"}),
            "US_DRIVER_LICENSE": OperatorConfig("replace", {"new_value": "[DRIVER_LICENSE]"}),
            "UK_NHS": OperatorConfig("replace", {"new_value": "[NHS]"}),
            "CANADA_SIN": OperatorConfig("replace", {"new_value": "[SIN]"}),
            "AUSTRALIA_TAX_FILE_NUMBER": OperatorConfig("replace", {"new_value": "[TAX_FILE_NUMBER]"}),
            "AUSTRALIA_MEDICARE": OperatorConfig("replace", {"new_value": "[MEDICARE]"}),
            "INDIA_PAN": OperatorConfig("replace", {"new_value": "[PAN]"}),
            "INDIA_AADHAAR": OperatorConfig("replace", {"new_value": "[AADHAAR]"}),
        }
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        try:
            analyzer_results = self.analyzer.analyze(
                text=text,
                entities=[],
                language=self.language
            )
            
            pii_entities = []
            for result in analyzer_results:
                pii_entities.append({
                    'entity_type': result.entity_type,
                    'start': result.start,
                    'end': result.end,
                    'score': result.score,
                    'text': text[result.start:result.end]
                })
            
            logger.info(f"Detected {len(pii_entities)} PII entities")
            return pii_entities
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            return []
    
    def anonymize_text(self, text: str) -> Dict[str, Any]:
        try:
            analyzer_results = self.analyzer.analyze(
                text=text,
                entities=[],
                language=self.language
            )
            
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators=self.operators
            )
            
            anonymized_text = anonymized_result.text
            anonymized_entities = []
            
            for item in anonymized_result.items:
                anonymized_entities.append({
                    'entity_type': item.entity_type,
                    'start': item.start,
                    'end': item.end,
                    'original_text': item.original_text,
                    'anonymized_text': item.text
                })
            
            result = {
                'anonymized_text': anonymized_text,
                'entities_found': len(anonymized_entities),
                'entities': anonymized_entities
            }
            
            logger.info(f"Anonymized text with {len(anonymized_entities)} entities")
            return result
            
        except Exception as e:
            logger.error(f"Text anonymization failed: {e}")
            return {
                'anonymized_text': text,
                'entities_found': 0,
                'entities': []
            }
    
    def get_pii_summary(self, text: str) -> Dict[str, int]:
        try:
            pii_entities = self.detect_pii(text)
            
            summary = {}
            for entity in pii_entities:
                entity_type = entity['entity_type']
                summary[entity_type] = summary.get(entity_type, 0) + 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get PII summary: {e}")
            return {}
    
    def is_sensitive_document(self, text: str, threshold: int = 5) -> bool:
        try:
            pii_entities = self.detect_pii(text)
            return len(pii_entities) >= threshold
            
        except Exception as e:
            logger.error(f"Failed to determine document sensitivity: {e}")
            return False 