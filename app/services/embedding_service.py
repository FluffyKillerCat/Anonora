from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import numpy as np
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model_name = settings.sentence_transformer_model
        self.model = None
        self.dimension = settings.vector_dimension
        self._load_model()
    
    def _load_model(self):
        try:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            # Force CPU usage to avoid MPS issues on macOS
            self.model = SentenceTransformer(self.model_name, device="cpu")
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {e}")
            raise
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        try:
            if not self.model:
                raise Exception("Model not loaded")
            
            embedding = self.model.encode(text)
            embedding_list = embedding.tolist()
            
            logger.debug(f"Created embedding with dimension: {len(embedding_list)}")
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return None
    
    def create_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        try:
            if not self.model:
                raise Exception("Model not loaded")
            
            embeddings = self.model.encode(texts)
            embeddings_list = [embedding.tolist() for embedding in embeddings]
            
            logger.info(f"Created embeddings for {len(texts)} texts")
            return embeddings_list
            
        except Exception as e:
            logger.error(f"Failed to create batch embeddings: {e}")
            return [None] * len(texts)
    
    def create_chunk_embeddings(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[Dict[str, Any]]:
        try:
            chunks = self._split_text_into_chunks(text, chunk_size, overlap)
            embeddings = self.create_embeddings_batch(chunks)
            
            chunk_embeddings = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding:
                    chunk_embeddings.append({
                        'chunk_id': i,
                        'text': chunk,
                        'embedding': embedding,
                        'start_pos': i * (chunk_size - overlap),
                        'end_pos': (i + 1) * chunk_size
                    })
            
            logger.info(f"Created {len(chunk_embeddings)} chunk embeddings")
            return chunk_embeddings
            
        except Exception as e:
            logger.error(f"Failed to create chunk embeddings: {e}")
            return []
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        chunks = []
        words = text.split()
        
        if len(words) <= chunk_size:
            return [text]
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)
        
        return chunks
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            cosine_similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            return float(cosine_similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def find_similar_chunks(self, query_embedding: List[float], chunk_embeddings: List[Dict[str, Any]], 
                           threshold: float = None) -> List[Dict[str, Any]]:
        try:
            similar_chunks = []
            
            for chunk_data in chunk_embeddings:
                similarity = self.calculate_similarity(query_embedding, chunk_data['embedding'])
                
                if threshold is None or similarity >= threshold:
                    chunk_data['similarity'] = similarity
                    similar_chunks.append(chunk_data)
            
            similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Failed to find similar chunks: {e}")
            return []
    
    def get_embedding_dimension(self) -> int:
        return self.dimension 