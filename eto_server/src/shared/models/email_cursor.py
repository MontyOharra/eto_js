"""
Email Cursor Domain Models
Pydantic models for cursor management
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EmailCursorBase(BaseModel):
    """Base cursor fields"""
    config_id: int = Field(..., description="Associated configuration ID")
    email_address: str = Field(..., description="Email address being monitored")
    folder_name: str = Field(..., description="Email folder name")
    last_processed_message_id: str = Field(..., description="Last processed message ID")
    last_processed_received_date: datetime = Field(..., description="Last processed email date")
    last_check_time: datetime = Field(..., description="Last check timestamp")
    total_emails_processed: int = Field(0, ge=0, description="Total emails processed")
    total_pdfs_found: int = Field(0, ge=0, description="Total PDFs found")

    class Config:
        from_attributes = True


class EmailCursor(EmailCursorBase):
    """Complete cursor with DB fields"""
    id: int = Field(..., description="Cursor ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    @classmethod
    def from_db_model(cls, db_model) -> 'EmailCursor':
        """Create from database model"""
        return cls(
            id=db_model.id,
            config_id=db_model.config_id,
            email_address=db_model.email_address,
            folder_name=db_model.folder_name,
            last_processed_message_id=db_model.last_processed_message_id,
            last_processed_received_date=db_model.last_processed_received_date,
            last_check_time=db_model.last_check_time,
            total_emails_processed=db_model.total_emails_processed or 0,
            total_pdfs_found=db_model.total_pdfs_found or 0,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at
        )


class EmailCursorCreate(EmailCursorBase):
    """Request model for creating cursors"""
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        return self.model_dump()


class EmailCursorUpdate(BaseModel):
    """Request model for updating cursors"""
    last_processed_message_id: Optional[str] = None
    last_processed_received_date: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        return self.model_dump(exclude_unset=True)