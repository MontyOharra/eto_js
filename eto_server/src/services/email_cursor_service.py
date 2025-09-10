"""
Email Cursor Service
Manages processing cursors and downtime recovery
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from ..database.repositories import CursorRepository
from ..database.models import EmailCursor

logger = logging.getLogger(__name__)


@dataclass
class CursorState:
    """Cursor state information"""
    email_address: str
    folder_name: str
    last_processed_message_id: Optional[str]
    last_processed_received_date: Optional[datetime]
    total_emails_processed: int
    total_pdfs_found: int
    last_check_time: datetime


class EmailCursorService:
    """Manages processing cursors and downtime recovery"""
    
    def __init__(self, cursor_repository: CursorRepository):
        self.cursor_repository = cursor_repository
        self.active_cursors: Dict[str, CursorState] = {}  # Cache for performance
        self.logger = logging.getLogger(__name__)

    # === High-Level API Methods ===
    
    async def get_cursor_state(self, email_address: str, folder: str) -> Optional[CursorState]:
        """Retrieve current cursor state for email/folder combination"""
        try:
            cache_key = self._get_cursor_cache_key(email_address, folder)
            
            # Check cache first
            if cache_key in self.active_cursors:
                cached_cursor = self.active_cursors[cache_key]
                logger.debug(f"Retrieved cursor from cache: {email_address}/{folder}")
                return cached_cursor
            
            # Get from database
            db_cursor = self.cursor_repository.get_by_email_and_folder(email_address, folder)
            
            if db_cursor:
                cursor_state = CursorState(
                    email_address=db_cursor.email_address,
                    folder_name=db_cursor.folder_name,
                    last_processed_message_id=db_cursor.last_processed_message_id,
                    last_processed_received_date=db_cursor.last_processed_received_date,
                    total_emails_processed=db_cursor.total_emails_processed or 0,
                    total_pdfs_found=db_cursor.total_pdfs_found or 0,
                    last_check_time=db_cursor.last_check_time or datetime.now(timezone.utc)
                )
                
                # Cache the cursor state
                self._cache_cursor_state(cursor_state)
                
                logger.info(f"Retrieved cursor state: {email_address}/{folder} - Last processed: {cursor_state.last_processed_received_date}")
                return cursor_state
            else:
                logger.info(f"No cursor found for {email_address}/{folder}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cursor state for {email_address}/{folder}: {e}")
            return None
    
    async def initialize_cursor(self, email_address: str, folder: str) -> CursorState:
        """Initialize new cursor at current timestamp"""
        try:
            current_time = datetime.now(timezone.utc)
            
            cursor_data = {
                'email_address': email_address,
                'folder_name': folder,
                'last_processed_message_id': None,
                'last_processed_received_date': current_time,
                'last_check_time': current_time,
                'total_emails_processed': 0,
                'total_pdfs_found': 0
            }
            
            # Use the repository's create_or_update_cursor method
            db_cursor = self.cursor_repository.create_or_update_cursor(
                email_address, folder, cursor_data
            )
            
            cursor_state = CursorState(
                email_address=db_cursor.email_address,
                folder_name=db_cursor.folder_name,
                last_processed_message_id=db_cursor.last_processed_message_id,
                last_processed_received_date=db_cursor.last_processed_received_date,
                total_emails_processed=db_cursor.total_emails_processed or 0,
                total_pdfs_found=db_cursor.total_pdfs_found or 0,
                last_check_time=db_cursor.last_check_time or current_time
            )
            
            # Cache the new cursor state
            self._cache_cursor_state(cursor_state)
            
            logger.info(f"Initialized new cursor: {email_address}/{folder} at {current_time}")
            return cursor_state
            
        except Exception as e:
            logger.error(f"Error initializing cursor for {email_address}/{folder}: {e}")
            raise Exception(f"Failed to initialize cursor: {e}")
    
    async def update_cursor(self, email_address: str, folder: str, 
                          last_email_data: Dict[str, Any]) -> CursorState:
        """Update cursor with latest processed email information"""
        try:
            # Prepare cursor update data
            cursor_data = {
                'last_processed_message_id': last_email_data.get('message_id'),
                'last_processed_received_date': last_email_data.get('received_date', datetime.now(timezone.utc)),
                'last_check_time': datetime.now(timezone.utc)
            }
            
            # Update using repository
            db_cursor = self.cursor_repository.create_or_update_cursor(
                email_address, folder, cursor_data
            )
            
            # Create updated cursor state
            cursor_state = CursorState(
                email_address=db_cursor.email_address,
                folder_name=db_cursor.folder_name,
                last_processed_message_id=db_cursor.last_processed_message_id,
                last_processed_received_date=db_cursor.last_processed_received_date,
                total_emails_processed=db_cursor.total_emails_processed or 0,
                total_pdfs_found=db_cursor.total_pdfs_found or 0,
                last_check_time=db_cursor.last_check_time or datetime.now(timezone.utc)
            )
            
            # Update cache
            self._cache_cursor_state(cursor_state)
            
            logger.debug(f"Updated cursor: {email_address}/{folder} with message {last_email_data.get('message_id')}")
            return cursor_state
            
        except Exception as e:
            logger.error(f"Error updating cursor for {email_address}/{folder}: {e}")
            raise Exception(f"Failed to update cursor: {e}")
    
    async def reset_cursor_to_current(self, email_address: str, folder: str) -> CursorState:
        """Reset cursor to current timestamp (for configuration changes)"""
        try:
            current_time = datetime.now(timezone.utc)
            
            logger.info(f"Resetting cursor to current time: {email_address}/{folder}")
            
            # Get existing cursor to preserve statistics
            existing_cursor = await self.get_cursor_state(email_address, folder)
            
            cursor_data = {
                'last_processed_message_id': f"config_reset_{int(current_time.timestamp())}",
                'last_processed_received_date': current_time,
                'last_check_time': current_time
            }
            
            # Update cursor with new timestamp
            db_cursor = self.cursor_repository.create_or_update_cursor(
                email_address, folder, cursor_data
            )
            
            cursor_state = CursorState(
                email_address=db_cursor.email_address,
                folder_name=db_cursor.folder_name,
                last_processed_message_id=db_cursor.last_processed_message_id,
                last_processed_received_date=db_cursor.last_processed_received_date,
                total_emails_processed=db_cursor.total_emails_processed or 0,
                total_pdfs_found=db_cursor.total_pdfs_found or 0,
                last_check_time=db_cursor.last_check_time or current_time
            )
            
            # Update cache
            self._cache_cursor_state(cursor_state)
            
            logger.info(f"Reset cursor to {current_time}: {email_address}/{folder}")
            return cursor_state
            
        except Exception as e:
            logger.error(f"Error resetting cursor for {email_address}/{folder}: {e}")
            raise Exception(f"Failed to reset cursor: {e}")
    
    async def get_backlog_scope(self, email_address: str, folder: str, 
                              max_hours_back: int) -> Optional[Tuple[datetime, datetime]]:
        """
        Determine time range for backlog processing
        Returns: (start_time, end_time) or None if no backlog
        """
        try:
            cursor_state = await self.get_cursor_state(email_address, folder)
            
            if not cursor_state or not cursor_state.last_processed_received_date:
                logger.info(f"No cursor found for {email_address}/{folder} - no backlog to process")
                return None
            
            current_time = datetime.now(timezone.utc)
            cursor_time = cursor_state.last_processed_received_date
            
            # Validate cursor state
            if not self._validate_cursor_state(cursor_state):
                logger.warning(f"Invalid cursor state for {email_address}/{folder} - skipping backlog")
                return None
            
            # Calculate backlog window
            start_time, end_time = self._calculate_backlog_window(cursor_time, max_hours_back)
            
            # Only return if there's actually a meaningful time range
            if start_time >= end_time or (end_time - start_time).total_seconds() < 60:
                logger.info(f"No meaningful backlog window for {email_address}/{folder}")
                return None
            
            logger.info(f"Backlog scope for {email_address}/{folder}: {start_time} to {end_time}")
            return (start_time, end_time)
            
        except Exception as e:
            logger.error(f"Error determining backlog scope for {email_address}/{folder}: {e}")
            return None

    # === Statistics Methods ===
    
    async def increment_processing_stats(self, email_address: str, folder: str,
                                       emails_processed: int, pdfs_found: int) -> None:
        """Update cursor processing statistics"""
        try:
            # Get cursor ID for repository update
            db_cursor = self.cursor_repository.get_by_email_and_folder(email_address, folder)
            
            if db_cursor:
                self.cursor_repository.update_processing_stats(db_cursor.id, emails_processed, pdfs_found)
                
                # Update cache if present
                cache_key = self._get_cursor_cache_key(email_address, folder)
                if cache_key in self.active_cursors:
                    cached_cursor = self.active_cursors[cache_key]
                    cached_cursor.total_emails_processed += emails_processed
                    cached_cursor.total_pdfs_found += pdfs_found
                    cached_cursor.last_check_time = datetime.now(timezone.utc)
                
                logger.debug(f"Updated processing stats: {email_address}/{folder} +{emails_processed} emails, +{pdfs_found} PDFs")
            else:
                logger.warning(f"Cannot update stats - cursor not found: {email_address}/{folder}")
                
        except Exception as e:
            logger.error(f"Error updating processing stats for {email_address}/{folder}: {e}")
    
    def get_cursor_statistics(self, email_address: str, folder: str) -> Optional[Dict[str, Any]]:
        """Get processing statistics for cursor"""
        try:
            cache_key = self._get_cursor_cache_key(email_address, folder)
            
            cursor_state = None
            if cache_key in self.active_cursors:
                cursor_state = self.active_cursors[cache_key]
            else:
                # Get from database if not cached
                db_cursor = self.cursor_repository.get_by_email_and_folder(email_address, folder)
                if db_cursor:
                    cursor_state = CursorState(
                        email_address=db_cursor.email_address,
                        folder_name=db_cursor.folder_name,
                        last_processed_message_id=db_cursor.last_processed_message_id,
                        last_processed_received_date=db_cursor.last_processed_received_date,
                        total_emails_processed=db_cursor.total_emails_processed or 0,
                        total_pdfs_found=db_cursor.total_pdfs_found or 0,
                        last_check_time=db_cursor.last_check_time or datetime.now(timezone.utc)
                    )
            
            if cursor_state:
                return {
                    "email_address": cursor_state.email_address,
                    "folder_name": cursor_state.folder_name,
                    "total_emails_processed": cursor_state.total_emails_processed,
                    "total_pdfs_found": cursor_state.total_pdfs_found,
                    "last_processed_date": cursor_state.last_processed_received_date.isoformat() if cursor_state.last_processed_received_date else None,
                    "last_check_time": cursor_state.last_check_time.isoformat(),
                    "last_message_id": cursor_state.last_processed_message_id
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting cursor statistics for {email_address}/{folder}: {e}")
            return None
    
    def get_all_cursor_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for all active cursors"""
        try:
            all_cursors = self.cursor_repository.get_all()
            statistics = []
            
            for cursor in all_cursors:
                stats = {
                    "email_address": cursor.email_address,
                    "folder_name": cursor.folder_name,
                    "total_emails_processed": cursor.total_emails_processed or 0,
                    "total_pdfs_found": cursor.total_pdfs_found or 0,
                    "last_processed_date": cursor.last_processed_received_date.isoformat() if cursor.last_processed_received_date else None,
                    "last_check_time": cursor.last_check_time.isoformat() if cursor.last_check_time else None,
                    "last_message_id": cursor.last_processed_message_id
                }
                statistics.append(stats)
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error getting all cursor statistics: {e}")
            return []

    # === Helper Methods ===
    
    def _validate_cursor_state(self, cursor_state: CursorState) -> bool:
        """Validate cursor integrity and reasonable values"""
        try:
            if not cursor_state:
                logger.debug("Cursor state is None")
                return False
            
            if not cursor_state.email_address or not cursor_state.folder_name:
                logger.debug("Cursor missing email_address or folder_name")
                return False
            
            if not cursor_state.last_processed_received_date:
                logger.debug("Cursor has no last_processed_received_date")
                return False
            
            # Validate that cursor date is reasonable (not in the future, not too old)
            current_time = datetime.now(timezone.utc)
            cursor_time = cursor_state.last_processed_received_date
            
            # Convert to naive datetime for comparison if needed
            if hasattr(cursor_time, 'replace') and cursor_time.tzinfo is not None:
                cursor_time = cursor_time.replace(tzinfo=None)
            
            # Check if cursor is in the future (shouldn't happen)
            if cursor_time > current_time + timedelta(minutes=5):  # 5 minute tolerance
                logger.warning(f"Cursor date is in the future: {cursor_time} > {current_time}")
                return False
            
            # Check if cursor is too old (more than 30 days)
            max_age = timedelta(days=30)
            if current_time - cursor_time > max_age:
                logger.warning(f"Cursor is very old ({current_time - cursor_time}), but will process with limited scope")
                # Still return True but log the warning
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating cursor state: {e}")
            return False
    
    def _calculate_backlog_window(self, cursor_time: datetime, max_hours: int) -> Tuple[datetime, datetime]:
        """Calculate safe backlog processing window"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Convert cursor_time to naive if needed
            if hasattr(cursor_time, 'replace') and cursor_time.tzinfo is not None:
                cursor_time = cursor_time.replace(tzinfo=None)
            
            # Validate max_hours
            if max_hours <= 0:
                max_hours = 24  # Default to 24 hours
            
            # Maximum lookback from current time
            max_lookback = current_time - timedelta(hours=max_hours)
            
            # Start time is the later of cursor_time or max_lookback
            start_time = max(cursor_time, max_lookback)
            
            # End time is current time
            end_time = current_time
            
            logger.debug(f"Backlog window: {start_time} to {end_time} (cursor: {cursor_time}, max_hours: {max_hours})")
            
            return (start_time, end_time)
            
        except Exception as e:
            logger.error(f"Error calculating backlog window: {e}")
            # Return safe default (last hour)
            current_time = datetime.now(timezone.utc)
            return (current_time - timedelta(hours=1), current_time)
    
    def _cache_cursor_state(self, cursor_state: CursorState) -> None:
        """Cache cursor state for performance"""
        try:
            cache_key = self._get_cursor_cache_key(cursor_state.email_address, cursor_state.folder_name)
            self.active_cursors[cache_key] = cursor_state
            logger.debug(f"Cached cursor state: {cache_key}")
            
        except Exception as e:
            logger.error(f"Error caching cursor state: {e}")
    
    def _get_cursor_cache_key(self, email_address: str, folder: str) -> str:
        """Generate cache key for cursor"""
        return f"{email_address.lower()}:{folder.lower()}"
    
    def _log_cursor_update(self, email_address: str, folder: str, 
                          old_state: Optional[CursorState], new_state: CursorState) -> None:
        """Log cursor state changes"""
        try:
            if old_state:
                logger.info(f"Cursor updated: {email_address}/{folder} - "
                          f"From {old_state.last_processed_received_date} "
                          f"to {new_state.last_processed_received_date}")
            else:
                logger.info(f"Cursor created: {email_address}/{folder} - "
                          f"Set to {new_state.last_processed_received_date}")
                
        except Exception as e:
            logger.error(f"Error logging cursor update: {e}")
    
    def clear_cache(self) -> None:
        """Clear cursor cache (useful for testing or memory management)"""
        try:
            cache_size = len(self.active_cursors)
            self.active_cursors.clear()
            logger.info(f"Cleared cursor cache - {cache_size} entries removed")
            
        except Exception as e:
            logger.error(f"Error clearing cursor cache: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            return {
                "cached_cursors": len(self.active_cursors),
                "cache_keys": list(self.active_cursors.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {"error": str(e)}