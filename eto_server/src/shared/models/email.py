"""
Email Domain Models
Pydantic models for email records (append-only pattern)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class EmailBase(BaseModel):
    """Base email fields used for creation and display"""
    config_id: int = Field(..., description="Associated email config ID")
    message_id: str = Field(..., description="Unique email message ID from provider")
    subject: Optional[str] = Field(default=None, description="Email subject line")
    sender_email: Optional[str] = Field(default=None, description="Sender email address")
    sender_name: Optional[str] = Field(default=None, description="Sender display name")
    received_date: datetime = Field(..., description="When email was received (UTC)")
    folder_name: Optional[str] = Field(default=None, description="Email folder name")
    has_pdf_attachments: bool = Field(default=False, description="Whether email has PDF attachments")
    attachment_count: int = Field(default=0, ge=0, description="Total number of attachments")
    pdf_count: int = Field(default=0, ge=0, description="Number of PDF attachments")
    body_preview: Optional[str] = Field(default=None, max_length=500, description="Email body preview text")
    
    def model_dump_for_db(self) -> Dict[str, Any]:
        """
        Convert model to dict for database insertion.
        Consistent with other models even though no special handling needed.
        """
        return self.model_dump(exclude_unset=True)


class EmailCreate(EmailBase):
    """Model for creating new email records"""
    pass  # All fields inherited from EmailBase


class Email(EmailBase):
    """Complete email domain model with database fields"""
    id: int = Field(..., description="Database ID")
    processed_at: datetime = Field(..., description="When email was processed and saved")
    created_at: datetime = Field(..., description="When record was created in database")
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_db_model(cls, model: Any) -> 'Email':
        """
        Create from database model.
        Used by repository's _convert_to_domain_object method.
        """
        return cls(
            id=model.id,
            config_id=model.config_id,
            message_id=model.message_id,
            subject=model.subject,
            sender_email=model.sender_email,
            sender_name=model.sender_name,
            received_date=model.received_date,
            folder_name=model.folder_name,
            has_pdf_attachments=model.has_pdf_attachments,
            attachment_count=model.attachment_count,
            pdf_count=model.pdf_count,
            body_preview=getattr(model, 'body_preview', None),  # May not exist in older records
            processed_at=model.processed_at,
            created_at=model.created_at
        )


class EmailSummary(BaseModel):
    """Lightweight email summary for list views"""
    id: int = Field(..., description="Database ID")
    config_id: int = Field(..., description="Associated config ID")
    subject: Optional[str] = Field(default=None, description="Email subject")
    sender_email: Optional[str] = Field(default=None, description="Sender email")
    received_date: datetime = Field(..., description="When received")
    has_pdf_attachments: bool = Field(default=False, description="Has PDFs")
    pdf_count: int = Field(default=0, description="Number of PDFs")
    created_at: datetime = Field(..., description="When processed")
    
    class Config:
        from_attributes = True