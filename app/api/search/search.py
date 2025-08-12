from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.document import DocumentSearchResult
from app.services.document_processing_service import DocumentProcessingService
from app.core.database import db_manager
from app.api.auth.auth import get_current_user_id
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])
security = HTTPBearer()
processing_service = DocumentProcessingService()


@router.post("/query")
async def search_documents(
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        accessible_documents = await _get_accessible_documents(current_user_id)

        if not accessible_documents:
            return {
                "query": query,
                "results": [],
                "total_found": 0
            }

        query_embedding = processing_service.create_embeddings_only(query)

        if not query_embedding:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process query"
            )

        similar_docs = []
        for doc in accessible_documents:
            if doc.get("vector_embedding"):
                similarity = processing_service.embedding_service.calculate_similarity(
                    query_embedding, doc["vector_embedding"]
                )

                if similarity >= threshold:
                    similar_docs.append({
                        "document": doc,
                        "similarity_score": similarity
                    })

        similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = similar_docs[:limit]

        formatted_results = []
        for result in results:
            doc = result["document"]
            formatted_results.append({
                "document_id": doc["id"],
                "title": doc["title"],
                "description": doc["description"],
                "similarity_score": result["similarity_score"],
                "tags": doc.get("tags", []),
                "created_at": doc["created_at"]
            })

        return {
            "query": query,
            "results": formatted_results,
            "total_found": len(formatted_results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.post("/semantic")
async def semantic_search(
        query: str,
        document_ids: Optional[List[str]] = None,
        limit: int = 10,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        if document_ids:
            accessible_docs = []
            for doc_id in document_ids:
                doc = await _get_document_if_accessible(doc_id, current_user_id)
                if doc:
                    accessible_docs.append(doc)
        else:
            accessible_docs = await _get_accessible_documents(current_user_id)

        if not accessible_docs:
            return {
                "query": query,
                "results": [],
                "total_found": 0
            }

        query_embedding = processing_service.create_embeddings_only(query)

        if not query_embedding:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process query"
            )

        results = []
        for doc in accessible_docs:
            if doc.get("vector_embedding"):
                similarity = processing_service.calculate_similarity(
                    query_embedding, doc["vector_embedding"]
                )

                results.append({
                    "document_id": doc["id"],
                    "title": doc["title"],
                    "description": doc["description"],
                    "similarity_score": similarity,
                    "tags": doc.get("tags", []),
                    "created_at": doc["created_at"]
                })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:limit]

        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Semantic search failed"
        )


@router.post("/question-answering")
async def question_answering(
        question: str,
        document_ids: List[str],
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        accessible_docs = []
        for doc_id in document_ids:
            print(doc_id)
            doc = await _get_document_if_accessible(doc_id, current_user_id)
            if doc:
                accessible_docs.append(doc)

        if not accessible_docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No accessible documents found"
            )

        question_embedding = processing_service.create_embeddings_only(question)

        if not question_embedding:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process question"
            )

        relevant_docs = []
        for doc in accessible_docs:
            if doc.get("vector_embedding"):
                similarity = processing_service.calculate_similarity(
                    question_embedding, doc["vector_embedding"]
                )

                relevant_docs.append({
                    "document": doc,
                    "similarity_score": similarity
                })

        relevant_docs.sort(key=lambda x: x["similarity_score"], reverse=True)

        top_docs = relevant_docs[:3]

        answer = _generate_answer_from_documents(question, top_docs)

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "document_id": doc["document"]["id"],
                    "title": doc["document"]["title"],
                    "similarity_score": doc["similarity_score"]
                }
                for doc in top_docs
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question answering failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question answering failed"
        )


@router.get("/suggestions")
async def get_search_suggestions(
        query: str,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("tags").eq("owner_id", current_user_id).execute()

        all_tags = []
        for doc in result.data:
            if doc.get("tags"):
                all_tags.extend(doc["tags"])

        unique_tags = list(set(all_tags))

        suggestions = []

        for tag in unique_tags[:5]:
            if tag.lower() in query.lower():
                suggestions.append(f"Find documents tagged with '{tag}'")

        suggestions.extend([
            "Search for contracts and legal documents",
            "Find financial reports and invoices",
            "Look for technical documentation",
            "Search for policy documents"
        ])

        return {
            "query": query,
            "suggestions": suggestions[:5]
        }

    except Exception as e:
        logger.error(f"Failed to get search suggestions: {e}")
        return {
            "query": query,
            "suggestions": []
        }


async def _get_accessible_documents(user_id: str) -> List[Dict[str, Any]]:
    try:
        supabase = db_manager.get_supabase()

        owned_result = supabase.table("documents").select("*").eq("owner_id", user_id).execute()
        owned_docs = owned_result.data or []

        shared_result = supabase.table("document_shares").select("document_id").eq("shared_with_user_id",
                                                                                   user_id).execute()
        shared_doc_ids = [share["document_id"] for share in shared_result.data or []]

        shared_docs = []
        if shared_doc_ids:
            shared_result = supabase.table("documents").select("*").in_("id", shared_doc_ids).execute()
            shared_docs = shared_result.data or []

        all_docs = owned_docs + shared_docs
        accessible_docs = [doc for doc in all_docs if doc.get("status") == "completed"]

        return accessible_docs

    except Exception as e:
        logger.error(f"Failed to get accessible documents: {e}")
        return []


async def _get_document_if_accessible(doc_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("id", doc_id).execute()

        if not result.data:
            return None

        document = result.data[0]

        if document["owner_id"] == user_id:
            return document if document.get("status") == "completed" else None

        share_result = supabase.table("document_shares").select("*").eq("document_id", doc_id).eq("shared_with_user_id",
                                                                                                  user_id).execute()

        if share_result.data:
            return document if document.get("status") == "completed" else None

        return None

    except Exception as e:
        logger.error(f"Failed to check document access: {e}")
        return None


def _generate_answer_from_documents(question: str, relevant_docs: List[Dict[str, Any]]) -> str:
    try:
        if not relevant_docs:
            return "I couldn't find relevant information to answer your question."

        relevant_texts = []
        for doc_info in relevant_docs:
            doc = doc_info["document"]
            if doc.get("anonymized_text"):
                relevant_texts.append(doc["anonymized_text"][:1000])

        if not relevant_texts:
            return "I couldn't find relevant information to answer your question."

        combined_text = " ".join(relevant_texts)

        if "what" in question.lower():
            return f"Based on the documents, I found relevant information: {combined_text[:500]}..."
        elif "how" in question.lower():
            return f"The documents suggest the following approach: {combined_text[:500]}..."
        else:
            return f"Here's what I found in the documents: {combined_text[:500]}..."

    except Exception as e:
        logger.error(f"Failed to generate answer: {e}")
        return "I couldn't generate an answer based on the available documents."