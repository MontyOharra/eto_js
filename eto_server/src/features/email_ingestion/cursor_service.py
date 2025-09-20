"""
Email Cursor Service
Manages processing cursors and downtime recovery
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone

from shared.database.repositories import EmailIngestionCursorRepository
from shared.domain import ( 
    EmailIngestionConnectionConfig, EmailIngestionCursor,
    EmailIngestionCursorStatistics, EmailData
)


logger = logging.getLogger(__name__)


class EmailIngestionCursorService:
    """Manages processing cursors and downtime recovery"""
    
    def __init__(self, cursor_repository: EmailIngestionCursorRepository):
        self.cursor_repository = cursor_repository
        self.active_cursors: Dict[str, EmailIngestionCursor] = {}  # Cache for performance
        self.logger = logging.getLogger(__name__)

    # === High-Level API Methods ===
    
    def get_cursor_state(self, email_address: str, folder: str) -> Optional[EmailIngestionCursor]:
        """Retrieve current cursor state for email/folder combination"""
        try:
            cache_key = self._get_cursor_cache_key(email_address, folder)
            
            # Check cache first
            if cache_key in self.active_cursors:
                cached_cursor = self.active_cursors[cache_key]
                logger.debug(f"Retrieved cursor from cache: {email_address}/{folder}")
                return cached_cursor
            
            # Get from database using repository method
            cursor = self.cursor_repository.get_by_email_and_folder(email_address, folder)
            
            if cursor:
                # Cache the cursor
                self._cache_cursor(cursor)
                
                logger.debug(f"Retrieved cursor: {email_address}/{folder} - Last processed: {cursor.last_processed_received_date}")
                return cursor
            else:
                logger.info(f"No cursor found for {email_address}/{folder}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cursor state for {email_address}/{folder}: {e}")
            raise Exception(f"Failed to get cursor state: {e}")
    
    def initialize_cursor(self, connection_config: EmailIngestionConnectionConfig) -> EmailIngestionCursor:
        """Initialize cursor for new email/folder combination"""
        try:
            email_address = connection_config.email_address
            folder_name = connection_config.folder_name
            
            # Check if cursor already exists
            existing_cursor = self.get_cursor_state(email_address, folder_name)
            if existing_cursor:
                logger.debug(f"Cursor already exists for {email_address}/{folder_name}")
                return existing_cursor
            
            # Create new cursor starting from current time
            current_time = datetime.now(timezone.utc)
            last_processed_message_id=f"init_{int(current_time.timestamp())}"
            last_processed_received_date=current_time
            last_check_time=current_time
            total_emails_processed=0
            total_pdfs_found=0

            # Create cursor record and get ID (following config service pattern)
            cursor_id = self.cursor_repository.create_and_get_id({
                "email_address": email_address,
                "folder_name": folder_name,
                "last_processed_message_id": last_processed_message_id,
                "last_processed_received_date": last_processed_received_date,
                "last_check_time": last_check_time,
                "total_emails_processed": total_emails_processed,
                "total_pdfs_found": total_pdfs_found
            })

            # Return the created cursor from repository
            cursor = self.cursor_repository.get_by_id(cursor_id)
            if not cursor:
                raise Exception(f"Failed to retrieve created cursor with ID {cursor_id}")
            self._cache_cursor(cursor)
            
            logger.info(f"Initialized new cursor for {email_address}/{folder_name}")
            return cursor
            
        except Exception as e:
            logger.error(f"Error initializing cursor for {connection_config.email_address or 'default'}/{connection_config.folder_name}: {e}")
            raise Exception(f"Failed to initialize cursor: {e}")
    
    def update_cursor(self, email_address: str, folder_name: str,
                          last_email: EmailData) -> EmailIngestionCursor:
        """Update cursor with latest processed email information"""
        try:
            # Prepare cursor update data from EmailData object
            cursor_data = {
                'last_processed_message_id': last_email.message_id,
                'last_processed_received_date': last_email.received_time,
                'last_check_time': datetime.now(timezone.utc)
            }
            
            # Get existing cursor and update it
            existing_cursor = self.get_cursor_state(email_address, folder_name)
            
            if existing_cursor:
                # Update existing cursor
                update_data = {
                    **cursor_data,
                    'last_check_time': datetime.now(timezone.utc)
                }
                db_cursor = self.cursor_repository.update(existing_cursor.id, update_data)
                if not db_cursor:
                    raise Exception(f"Failed to update cursor with ID {existing_cursor.id}")
            else:
                last_processed_message_id=last_email.message_id
                last_processed_received_date=last_email.received_time
                last_check_time=datetime.now(timezone.utc)
                total_emails_processed=0
                total_pdfs_found=0
                

                cursor_id = self.cursor_repository.create_and_get_id({
                    "email_address": email_address,
                    "folder_name": folder_name,
                    "last_processed_message_id": last_processed_message_id,
                    "last_processed_received_date": last_processed_received_date,
                    "last_check_time": last_check_time,
                    "total_emails_processed": total_emails_processed,
                    "total_pdfs_found": total_pdfs_found
                })

                db_cursor = self.cursor_repository.get_by_id(cursor_id)
                if not db_cursor:
                    raise Exception(f"Failed to retrieve created cursor with ID {cursor_id}")
            
            # Update cache
            self._cache_cursor(db_cursor)
            
            logger.debug(f"Updated cursor: {email_address}/{folder_name} with message {last_email.message_id}")
            return db_cursor
            
        except Exception as e:
            logger.error(f"Error updating cursor for {email_address}/{folder_name}: {e}")
            raise Exception(f"Failed to update cursor: {e}")

    def get_backlog_scope(self, email_address: str, folder: str, 
                              max_hours_back: int) -> Optional[Tuple[datetime, datetime]]:
        """
        Determine time range for backlog processing
        Returns: (start_time, end_time) or None if no backlog
        """
        try:
            cursor_state = self.get_cursor_state(email_address, folder)
            
            if not cursor_state or not cursor_state.last_processed_received_date:
                # No cursor or no last processed date - process from max_hours_back
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=max_hours_back)
                logger.debug(f"No cursor history, processing last {max_hours_back} hours")
                return (start_time, end_time)
            
            # Calculate time windows
            current_time = datetime.now(timezone.utc)
            cursor_time = cursor_state.last_processed_received_date
            max_backlog_start = current_time - timedelta(hours=max_hours_back)
            
            # Determine appropriate start time
            if cursor_time < max_backlog_start:
                # Cursor is older than max backlog - start from max_backlog_start
                start_time = max_backlog_start
                logger.debug(f"Cursor too old, limiting backlog to {max_hours_back} hours")
            else:
                # Start from cursor position
                start_time = cursor_time
                logger.debug(f"Processing from cursor position: {cursor_time}")
            
            return (start_time, current_time)
            
        except Exception as e:
            logger.error(f"Error calculating backlog scope for {email_address}/{folder}: {e}")
            raise Exception(f"Failed to calculate backlog scope: {e}")

    def get_cursor_statistics(self, email_address: str, folder: str) -> Optional[EmailIngestionCursorStatistics]:
        """Get cursor statistics for email/folder combination"""
        try:
            cursor = self.cursor_repository.get_by_email_and_folder(email_address, folder)
            if not cursor:
                return None

            return EmailIngestionCursorStatistics(
                email_address=cursor.email_address,
                folder_name=cursor.folder_name,
                total_emails_processed=cursor.total_emails_processed or 0,
                total_pdfs_found=cursor.total_pdfs_found or 0,
                last_processed_date=cursor.last_processed_received_date,
                last_check_time=cursor.last_check_time,
                last_message_id=cursor.last_processed_message_id
            )
        except Exception as e:
            logger.error(f"Error getting cursor statistics: {e}")
            return None

    # === Internal Helper Methods ===
    
    def _get_cursor_cache_key(self, email_address: str, folder: str) -> str:
        """Generate cache key for cursor"""
        return f"{email_address or 'default'}:{folder}"
    
    def _cache_cursor(self, cursor: EmailIngestionCursor) -> None:
        """Cache cursor for performance"""
        cache_key = self._get_cursor_cache_key(cursor.email_address, cursor.folder_name)
        self.active_cursors[cache_key] = cursor
    
    def clear_cache(self) -> None:
        """Clear cursor cache"""
        self.active_cursors.clear()
        logger.debug("Cursor cache cleared")