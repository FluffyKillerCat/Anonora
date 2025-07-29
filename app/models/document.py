from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    SCANNED_PDF = "scanned_pdf"


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    tags: List[str] = Field(default_factory=list, description="Document tags")

    @validator('title')
    def validate_title(cls, v):
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            return v.strip()
        return v


class DocumentCreate(DocumentBase):
    file_path: str = Field(..., description="Path to the document file")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    original_filename: str = Field(..., min_length=1, max_length=255, description="Original filename")

    @validator('file_size')
    def validate_file_size(cls, v):
        if v > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError('File size must be less than 100MB')
        return v


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    tags: Optional[List[str]] = Field(None, description="Document tags")

    @validator('title')
    def validate_title(cls, v):
        if v is not None:
            return v.strip()
        return v

    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            return v.strip()
        return v


class DocumentInDB(DocumentBase):
    id: UUID = Field(..., description="Document unique identifier")
    owner_id: UUID = Field(..., description="Document owner ID")
    file_path: str = Field(..., description="Path to the document file")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    original_filename: str = Field(..., description="Original filename")
    document_type: DocumentType = Field(..., description="Document type")
    status: DocumentStatus = Field(..., description="Document processing status")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    anonymized_text: Optional[str] = Field(None, description="Anonymized text content")
    vector_embedding: Optional[List[float]] = Field(None, description="Document vector embedding")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Document last update timestamp")

    class Config:
        from_attributes = True


class Document(DocumentInDB):
    pass


class DocumentShare(BaseModel):
    id: UUID = Field(..., description="Share record unique identifier")
    document_id: UUID = Field(..., description="Shared document ID")
    shared_with_user_id: UUID = Field(..., description="User ID with whom document is shared")
    permissions: List[str] = Field(..., description="Share permissions")
    created_at: datetime = Field(..., description="Share creation timestamp")
    created_by: UUID = Field(..., description="User who created the share")

    @validator('permissions')
    def validate_permissions(cls, v):
        valid_permissions = ["read", "write", "share"]
        for permission in v:
            if permission not in valid_permissions:
                raise ValueError(f'Invalid permission: {permission}. Valid permissions are: {valid_permissions}')
        return v

    class Config:
        from_attributes = True


class DocumentSearchResult(BaseModel):
    document: Document = Field(..., description="Matched document")
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity score")
    matched_content: str = Field(..., description="Matched content snippet")


class DocumentProcessingTask(BaseModel):
    id: UUID = Field(..., description="Task unique identifier")
    document_id: UUID = Field(..., description="Document ID being processed")
    task_type: str = Field(..., description="Type of processing task")
    status: str = Field(..., description="Task status")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Task last update timestamp")

    @validator('task_type')
    def validate_task_type(cls, v):
        valid_types = ["extract", "anonymize", "embed", "tag"]
        if v not in valid_types:
            raise ValueError(f'Invalid task type: {v}. Valid types are: {valid_types}')
        return v

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["pending", "processing", "completed", "failed"]
        if v not in valid_statuses:
            raise ValueError(f'Invalid status: {v}. Valid statuses are: {valid_statuses}')
        return v

    class Config:
        from_attributes = True


class AuditLog(BaseModel):
    id: UUID = Field(..., description="Audit log unique identifier")
    user_id: UUID = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[UUID] = Field(None, description="ID of affected resource")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional action details")
    ip_address: Optional[str] = Field(None, description="User's IP address")
    user_agent: Optional[str] = Field(None, description="User's browser/agent")
    created_at: datetime = Field(..., description="Audit log timestamp")

    @validator('action')
    def validate_action(cls, v):
        valid_actions = ["upload", "search", "view", "share", "delete"]
        if v not in valid_actions:
            raise ValueError(f'Invalid action: {v}. Valid actions are: {valid_actions}')
        return v

    @validator('resource_type')
    def validate_resource_type(cls, v):
        valid_types = ["document", "user", "system"]
        if v not in valid_types:
            raise ValueError(f'Invalid resource type: {v}. Valid types are: {valid_types}')
        return v

    class Config:
        from_attributes = True