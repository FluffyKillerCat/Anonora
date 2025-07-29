from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer
from app.models.document import Document, DocumentUpdate, DocumentStatus
from app.services.document_processing_service import DocumentProcessingService
from app.core.database import db_manager
from app.core.config import settings
from app.api.auth.auth import get_current_user_id
import aiofiles
import os
import uuid
from typing import List, Optional
import logging
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


def ensure_uuid_string(value):
    """Convert UUID objects to strings for JSON serialization"""
    if isinstance(value, UUID):
        return str(value)
    return value


router = APIRouter(prefix="/documents", tags=["documents"])
security = HTTPBearer()
processing_service = DocumentProcessingService()


@router.post("/upload", response_model=Document)
async def upload_document(
        file: UploadFile = File(...),
        title: str = Form(...),
        description: Optional[str] = Form(None),
        tags: Optional[str] = Form("[]"),
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported"
            )

        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum limit of {settings.max_file_size} bytes"
            )

        os.makedirs(settings.upload_dir, exist_ok=True)

        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.upload_dir, unique_filename)

        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        document_id = str(uuid.uuid4())
        document_data = {
            "id": document_id,
            "owner_id": ensure_uuid_string(current_user_id),
            "title": title,
            "description": description,
            "tags": tags.split(',') if tags else [],
            "file_path": file_path,
            "file_size": len(content),
            "original_filename": file.filename,
            "status": DocumentStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        supabase = db_manager.get_supabase()
        result = supabase.table("documents").insert(document_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save document record"
            )

        task_id = processing_service.process_document_async(file_path, document_id)

        supabase.table("documents").update({
            "processing_task_id": task_id,
            "status": DocumentStatus.PROCESSING.value
        }).eq("id", document_id).execute()

        created_document = result.data[0]
        return Document(**created_document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.get("/", response_model=List[Document])
async def list_documents(
        skip: int = 0,
        limit: int = 10,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("owner_id", current_user_id).range(skip,
                                                                                               skip + limit - 1).execute()

        documents = []
        for doc in result.data:
            documents.append(Document(**doc))

        return documents

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get("/{document_id}", response_model=Document)
async def get_document(
        document_id: str,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("id", document_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        document = result.data[0]

        # Convert both to strings for comparison to handle UUID objects
        document_owner_id = ensure_uuid_string(document["owner_id"])
        current_user_id_str = ensure_uuid_string(current_user_id)

        if document_owner_id != current_user_id_str:
            share_result = supabase.table("document_shares").select("*").eq("document_id", document_id).eq(
                "shared_with_user_id", current_user_id_str).execute()

            if not share_result.data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

        return Document(**document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.put("/{document_id}", response_model=Document)
async def update_document(
        document_id: str,
        document_update: DocumentUpdate,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("id", document_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        document = result.data[0]

        # Convert both to strings for comparison to handle UUID objects
        document_owner_id = ensure_uuid_string(document["owner_id"])
        current_user_id_str = ensure_uuid_string(current_user_id)

        if document_owner_id != current_user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        update_data = {}
        if document_update.title is not None:
            update_data["title"] = document_update.title
        if document_update.description is not None:
            update_data["description"] = document_update.description
        if document_update.tags is not None:
            update_data["tags"] = document_update.tags

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        update_data["updated_at"] = datetime.utcnow().isoformat()

        result = supabase.table("documents").update(update_data).eq("id", document_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update document"
            )

        updated_document = result.data[0]
        return Document(**updated_document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )


@router.delete("/{document_id}")
async def delete_document(
        document_id: str,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("id", document_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        document = result.data[0]

        # Convert both to strings for comparison to handle UUID objects
        document_owner_id = ensure_uuid_string(document["owner_id"])
        current_user_id_str = ensure_uuid_string(current_user_id)

        if document_owner_id != current_user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        if os.path.exists(document["file_path"]):
            os.remove(document["file_path"])

        supabase.table("documents").delete().eq("id", document_id).execute()

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.get("/{document_id}/status")
async def get_document_processing_status(
        document_id: str,
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("id", document_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        document = result.data[0]

        # Convert both to strings for comparison to handle UUID objects
        document_owner_id = ensure_uuid_string(document["owner_id"])
        current_user_id_str = ensure_uuid_string(current_user_id)

        if document_owner_id != current_user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        task_id = document.get("processing_task_id")
        if task_id:
            status_info = processing_service.get_processing_status(task_id)
        else:
            status_info = {"status": "unknown", "progress": 0}

        return {
            "document_id": document_id,
            "status": document["status"],
            "processing_status": status_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document status"
        )


@router.post("/{document_id}/share")
async def share_document(
        document_id: str,
        shared_with_email: str,
        permissions: List[str],
        current_user_id: str = Depends(get_current_user_id)
):
    try:
        supabase = db_manager.get_supabase()

        result = supabase.table("documents").select("*").eq("id", document_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        document = result.data[0]

        # Convert both to strings for comparison to handle UUID objects
        document_owner_id = ensure_uuid_string(document["owner_id"])
        current_user_id_str = ensure_uuid_string(current_user_id)

        if document_owner_id != current_user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        user_result = supabase.table("users").select("*").eq("email", shared_with_email).execute()

        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        shared_with_user = user_result.data[0]

        share_data = {
            "document_id": document_id,
            "shared_with_user_id": ensure_uuid_string(shared_with_user["id"]),
            "permissions": permissions,
            "created_by": ensure_uuid_string(current_user_id),
            "created_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("document_shares").insert(share_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to share document"
            )

        return {"message": "Document shared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to share document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share document"
        )