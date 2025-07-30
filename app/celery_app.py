from celery import Celery
from app.core.config import settings
from app.services.document_processing_service import DocumentProcessingService
from app.core.database import db_manager
from app.models.document import DocumentStatus
import logging
from datetime import datetime
from app.utils.redis_client import get_redis_client

redis_client = get_redis_client()
redis_client.set("mykey", "myvalue")
value = redis_client.get("mykey")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "document_intelligence",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.celery_app"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(bind=True)
def process_document_task(self, file_path: str, document_id: str):
    """Process document asynchronously"""
    try:
        logger.info(f"Starting document processing task for document {document_id}")

        # Update task status
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Initializing processing"}
        )

        # Initialize processing service
        processing_service = DocumentProcessingService()

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 20, "total": 100, "status": "Extracting text"}
        )

        # Process document
        result = processing_service.process_document(file_path, document_id)

        if result["processing_status"] == "completed":
            # Update document in database
            supabase = db_manager.get_supabase()

            update_data = {
                "status": DocumentStatus.COMPLETED.value,
                "extracted_text": result["extracted_text"],
                "anonymized_text": result["anonymized_text"],
                "vector_embedding": result["embedding"],
                "tags": result["suggested_tags"],
                "metadata": {
                    "document_type": result["document_type"],
                    "pii_summary": result["pii_summary"],
                    "processed_at": result["processed_at"]
                },
                "updated_at": datetime.utcnow().isoformat()
            }

            supabase.table("documents").update(update_data).eq("id", document_id).execute()

            logger.info(f"Document processing completed successfully for {document_id}")

            return {
                "status": "completed",
                "document_id": document_id,
                "result": result
            }
        else:
            # Update document status to failed
            supabase = db_manager.get_supabase()
            supabase.table("documents").update({
                "status": DocumentStatus.FAILED.value,
                "metadata": {
                    "error_message": result.get("error_message", "Unknown error"),
                    "processed_at": result["processed_at"]
                },
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", document_id).execute()

            logger.error(f"Document processing failed for {document_id}: {result.get('error_message')}")

            return {
                "status": "failed",
                "document_id": document_id,
                "error": result.get("error_message", "Unknown error")
            }

    except Exception as e:
        logger.error(f"Document processing task failed for {document_id}: {e}")

        # Update document status to failed
        try:
            supabase = db_manager.get_supabase()
            supabase.table("documents").update({
                "status": DocumentStatus.FAILED.value,
                "metadata": {
                    "error_message": str(e),
                    "processed_at": datetime.utcnow().isoformat()
                },
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", document_id).execute()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")

        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def anonymize_text_task(self, text: str, document_id: str):
    """Anonymize text asynchronously"""
    try:
        logger.info(f"Starting text anonymization task for document {document_id}")

        processing_service = DocumentProcessingService()
        result = processing_service.anonymize_text_only(text)

        # Update document with anonymized text
        supabase = db_manager.get_supabase()
        supabase.table("documents").update({
            "anonymized_text": result["anonymized_text"],
            "metadata": {
                "pii_entities_found": result["entities_found"],
                "pii_entities": result["pii_entities"]
            },
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", document_id).execute()

        logger.info(f"Text anonymization completed for {document_id}")

        return {
            "status": "completed",
            "document_id": document_id,
            "entities_found": result["entities_found"]
        }

    except Exception as e:
        logger.error(f"Text anonymization failed for {document_id}: {e}")
        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def create_embeddings_task(self, text: str, document_id: str):
    """Create embeddings asynchronously"""
    try:
        logger.info(f"Starting embedding creation task for document {document_id}")

        processing_service = DocumentProcessingService()
        embedding = processing_service.create_embeddings_only(text)

        if embedding:
            # Update document with embedding
            supabase = db_manager.get_supabase()
            supabase.table("documents").update({
                "vector_embedding": embedding,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", document_id).execute()

            logger.info(f"Embedding creation completed for {document_id}")

            return {
                "status": "completed",
                "document_id": document_id,
                "embedding_dimension": len(embedding)
            }
        else:
            logger.error(f"Failed to create embedding for {document_id}")
            return {
                "status": "failed",
                "document_id": document_id,
                "error": "Failed to create embedding"
            }

    except Exception as e:
        logger.error(f"Embedding creation failed for {document_id}: {e}")
        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def suggest_tags_task(self, text: str, document_id: str):
    """Suggest tags asynchronously"""
    try:
        logger.info(f"Starting tag suggestion task for document {document_id}")

        processing_service = DocumentProcessingService()
        tags = processing_service.suggest_tags_only(text)

        # Update document with suggested tags
        supabase = db_manager.get_supabase()
        supabase.table("documents").update({
            "tags": tags,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", document_id).execute()

        logger.info(f"Tag suggestion completed for {document_id}: {tags}")

        return {
            "status": "completed",
            "document_id": document_id,
            "suggested_tags": tags
        }

    except Exception as e:
        logger.error(f"Tag suggestion failed for {document_id}: {e}")
        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }


@celery_app.task(bind=True)
def test_simple_task(self, message: str):
    """Simple test task to verify Celery is working"""
    try:
        logger.info(f"Simple test task received: {message}")
        return {
            "status": "completed",
            "message": f"Processed: {message}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Simple test task failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(bind=True)
def cleanup_failed_documents_task(self):
    """Clean up failed document processing tasks"""
    try:
        logger.info("Starting cleanup of failed documents")

        supabase = db_manager.get_supabase()

        # Find documents that have been in processing state for too long
        # This is a simplified cleanup - in production you might want more sophisticated logic

        # Get documents in processing state
        result = supabase.table("documents").select("*").eq("status", DocumentStatus.PROCESSING.value).execute()

        cleaned_count = 0
        for doc in result.data:
            # Check if document has been processing for more than 1 hour
            created_at = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
            if (datetime.utcnow() - created_at).total_seconds() > 3600:  # 1 hour
                # Mark as failed
                supabase.table("documents").update({
                    "status": DocumentStatus.FAILED.value,
                    "metadata": {
                        "error_message": "Processing timeout",
                        "cleaned_at": datetime.utcnow().isoformat()
                    },
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", doc["id"]).execute()

                cleaned_count += 1

        logger.info(f"Cleanup completed: {cleaned_count} documents marked as failed")

        return {
            "status": "completed",
            "cleaned_count": cleaned_count
        }

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


# Schedule periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks"""
    # Clean up failed documents every hour
    sender.add_periodic_task(
        3600.0,  # 1 hour
        cleanup_failed_documents_task.s(),
        name="cleanup-failed-documents"
    )