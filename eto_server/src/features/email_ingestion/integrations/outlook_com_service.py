"""
Outlook COM Service
Manages Outlook COM connections and basic folder operations
"""
import logging
import threading
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timezone, timedelta

try:
    import win32com.client
    import pythoncom
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False
    win32com = None
    pythoncom = None

from ..types import EmailConnectionConfig, ConnectionStatus, EmailData

logger = logging.getLogger(__name__)


class OutlookComService:
    """Manages Outlook COM connections and basic folder operations"""
    
    def __init__(self):
        if not COM_AVAILABLE:
            logger.warning("Windows COM components not available - Outlook integration disabled")
        
        # COM objects
        self.outlook: Optional[Any] = None
        self.namespace: Optional[Any] = None
        self.current_account: Optional[Any] = None
        self.current_folder: Optional[Any] = None
        
        # State management
        self.connection_config: Optional[EmailConnectionConfig] = None
        self.is_connected: bool = False
        self.connection_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        
        # Thread safety
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Outlook folder constants
        self.folder_mapping = {
            'Inbox': 6, 'Outbox': 4, 'Sent': 5, 'SentMail': 5,
            'Drafts': 16, 'DeletedItems': 3, 'Trash': 3,
            'Junk': 23, 'JunkEmail': 23, 'Calendar': 9,
            'Contacts': 10, 'Tasks': 13, 'Notes': 12, 'Journal': 11
        }

    # === High-Level API Methods ===
    
    def connect(self, connection_config: EmailConnectionConfig) -> Dict[str, Any]:
        """Connect to Outlook with specified configuration"""
        if not COM_AVAILABLE:
            return {
                "success": False,
                "error": "COM components not available",
                "message": "Windows COM components required for Outlook integration"
            }
        
        try:
            with self._lock:
                logger.info(f"Connecting to Outlook - Email: {connection_config.email_address or 'Default'}, Folder: {connection_config.folder_name}")
                
                # Initialize COM
                assert pythoncom is not None and win32com is not None
                pythoncom.CoInitialize()
                
                # Create Outlook application
                self.outlook = win32com.client.Dispatch("Outlook.Application")
                self.namespace = self.outlook.GetNamespace("MAPI")
                assert self.namespace is not None
                    
                # Select account if specified
                if connection_config.email_address:
                    account_found = False
                    for account in self.namespace.Accounts:
                        if account.SmtpAddress.lower() == connection_config.email_address.lower():
                            self.current_account = account
                            account_found = True
                            logger.debug(f"Selected account: {account.SmtpAddress}")
                            break
                    
                    if not account_found:
                        raise Exception(f"Email account {connection_config.email_address} not found")
                else:
                    # Use default account
                    self.current_account = self.namespace.Accounts.Item(1)
                    assert self.current_account is not None
                    logger.debug(f"Using default account: {self.current_account.SmtpAddress}")
                
                # Find and validate the folder
                self.current_folder = self._get_folder_by_name(connection_config.folder_name)
                if not self.current_folder:
                    raise Exception(f"Folder '{connection_config.folder_name}' not found")
                
                # Test the connection by trying to access folder properties
                try:
                    folder_count = self.current_folder.Items.Count
                    logger.debug(f"Folder '{connection_config.folder_name}' has {folder_count} items")
                except Exception as e:
                    raise Exception(f"Cannot access folder '{connection_config.folder_name}': {e}")
                
                self.connection_config = connection_config
                self.is_connected = True
                self.connection_time = datetime.now(timezone.utc)
                self.last_error = None
                
                logger.info("Successfully connected to Outlook")
                return {
                    "success": True,
                    "message": "Connected to Outlook successfully",
                    "email_address": connection_config.email_address,
                    "folder_name": connection_config.folder_name
                }
                
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error connecting to Outlook: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to connect to Outlook"
            }
    
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from Outlook"""
        try:
            with self._lock:
                # Check if already disconnected
                if not self.is_connected:
                    return {"success": True, "message": "Already disconnected"}
                
                try:
                    # Properly release COM objects
                    if self.current_folder:
                        self.current_folder = None
                    if self.current_account:
                        self.current_account = None
                    if self.namespace:
                        self.namespace = None
                    if self.outlook:
                        # Try to quit Outlook if we started it
                        try:
                            self.outlook.Quit()
                        except:
                            pass  # Outlook may already be closed
                        self.outlook = None
                    
                    if COM_AVAILABLE:
                        assert pythoncom is not None
                        pythoncom.CoUninitialize()
                        
                finally:
                    # Always reset state regardless of cleanup success
                    self.current_account = None
                    self.current_folder = None
                    self.is_connected = False
                    self.connection_time = None
                    self.connection_config = None
                
                logger.info("Disconnected from Outlook")
                return {
                    "success": True,
                    "message": "Disconnected from Outlook successfully"
                }
                
        except Exception as e:
            logger.error(f"Error disconnecting from Outlook: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error during Outlook disconnect"
            }
    
    def get_connection_status(self) -> ConnectionStatus:
        """Get current connection status"""
        # Handle connection edge cases
        email_address = None
        folder_name = None
        if self.connection_config:
            email_address = self.connection_config.email_address
            folder_name = self.connection_config.folder_name
        
        # Get actual folder count
        inbox_count = 0
        if self.is_connected and self.current_folder:
            try:
                inbox_count = self.current_folder.Items.Count
            except Exception as e:
                logger.warning(f"Could not get folder count: {e}")
                # Keep inbox_count as 0 if we can't access it
        
        # Verify connection state consistency
        if self.is_connected and not self.current_folder:
            logger.warning("Connection marked as connected but no current folder")
        
        return ConnectionStatus(
            is_connected=self.is_connected,
            email_address=email_address,
            folder_name=folder_name,
            inbox_count=inbox_count,
            last_error=self.last_error,
            connection_time=self.connection_time
        )
    
    def test_connection(self, connection_config: EmailConnectionConfig) -> Dict[str, Any]:
        """Test connection without persisting state"""
        test_outlook = None
        test_namespace = None
        test_folder = None
        
        try:
            logger.info(f"Testing connection - Email: {connection_config.email_address or 'Default'}, Folder: {connection_config.folder_name}")
            
            # Test COM availability
            if not COM_AVAILABLE:
                return {
                    "success": False,
                    "error": "COM components not available",
                    "message": "Windows COM components required for Outlook integration"
                }
            
            # Initialize COM for test
            assert pythoncom is not None and win32com is not None
            pythoncom.CoInitialize()
            
            try:
                # Create temporary Outlook connection
                test_outlook = win32com.client.Dispatch("Outlook.Application")
                test_namespace = test_outlook.GetNamespace("MAPI")
                
                # Test account access
                test_account = None
                if connection_config.email_address:
                    account_found = False
                    for account in test_namespace.Accounts:
                        if account.SmtpAddress.lower() == connection_config.email_address.lower():
                            test_account = account
                            account_found = True
                            break
                    
                    if not account_found:
                        return {
                            "success": False,
                            "error": f"Email account {connection_config.email_address} not found",
                            "message": "Specified email account not found in Outlook"
                        }
                else:
                    # Use default account
                    test_account = test_namespace.Accounts.Item(1)
                
                # Test folder access using temporary folder lookup
                test_folder = self._test_get_folder_by_name(test_namespace, connection_config.folder_name)
                if not test_folder:
                    return {
                        "success": False,
                        "error": f"Folder '{connection_config.folder_name}' not found",
                        "message": f"Folder '{connection_config.folder_name}' not accessible"
                    }
                
                # Get actual folder count
                folder_count = test_folder.Items.Count
                
                return {
                    "success": True,
                    "message": "Connection test successful",
                    "details": {
                        "email_address": test_account.SmtpAddress if test_account else None,
                        "folder_name": connection_config.folder_name,
                        "folder_accessible": True,
                        "email_count": folder_count
                    }
                }
                
            finally:
                # Clean up test connection
                if test_folder:
                    test_folder = None
                if test_namespace:
                    test_namespace = None
                if test_outlook:
                    test_outlook = None
                pythoncom.CoUninitialize()
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection test failed"
            }

    def get_recent_emails(self, limit: int = 10, 
                              start_date: Optional[datetime] = None) -> List[EmailData]:
        """Get recent emails from current folder"""
        try:
            if not self.is_connected or not self.connection_config:
                raise Exception("Not connected to Outlook")
            
            logger.debug(f"Getting {limit} recent emails from {self.connection_config.folder_name}")
            
            # Initialize COM for this thread
            if COM_AVAILABLE:
                assert pythoncom is not None and win32com is not None
                pythoncom.CoInitialize()
            
            try:
                # Create fresh COM objects for this thread
                assert win32com is not None
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                # Find the folder again (thread-safe approach)
                current_folder = None
                
                # Try to find the folder using the same logic as connect()
                for account in namespace.Accounts:
                    if not self.connection_config.email_address or account.SmtpAddress.lower() == self.connection_config.email_address.lower():
                        try:
                            delivery_store = account.DeliveryStore
                            if delivery_store:
                                root_folder = delivery_store.GetRootFolder()
                                current_folder = self._search_folder_recursive(root_folder, self.connection_config.folder_name)
                                if current_folder:
                                    break
                        except Exception as e:
                            logger.debug(f"Error searching account {account.SmtpAddress}: {e}")
                            continue
                
                if not current_folder:
                    raise Exception(f"Folder '{self.connection_config.folder_name}' not found")
                
                # Get folder items and sort by received time (newest first)
                items = current_folder.Items
                items.Sort("[ReceivedTime]", True)  # Descending order
                
                # Apply date filter if provided
                if start_date:
                    # Convert UTC start_date to local time for Outlook filtering
                    # Outlook works in local timezone, but our cursor uses UTC
                    import time
                    from datetime import timezone as dt_timezone
                    
                    if start_date.tzinfo is None:
                        # Assume UTC if no timezone info
                        start_date_utc = start_date.replace(tzinfo=dt_timezone.utc)
                    else:
                        start_date_utc = start_date
                    
                    # Convert to local time
                    local_start_date = start_date_utc.astimezone()
                    start_str = local_start_date.strftime("%m/%d/%Y %H:%M")
                    date_filter = f"[ReceivedTime] >= '{start_str}'"
                    items = items.Restrict(date_filter)
                    logger.debug(f"Applied date filter (converted UTC to local): {date_filter} (original UTC: {start_date})")
                
                # Convert Outlook items to EmailData objects
                emails = []
                count = 0
                for mail in items:
                    if count >= limit:
                        break
                    try:
                        email_data = self._convert_outlook_email(mail)
                        emails.append(email_data)
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to convert email: {e}")
                        continue
                
                logger.debug(f"Retrieved {len(emails)} recent emails from {self.connection_config.folder_name}")
                return emails
                
            finally:
                # Clean up COM for this thread
                if COM_AVAILABLE:
                    assert pythoncom is not None
                    pythoncom.CoUninitialize()
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            raise Exception(f"Failed to get emails: {e}")
    
    def get_mail_object_by_id(self, message_id: str) -> Optional[Any]:
        """Get raw Outlook mail object by message ID for attachment processing"""
        try:
            if not self.is_connected or not self.connection_config:
                logger.warning("Not connected to Outlook when trying to get mail object")
                return None
            
            logger.debug(f"Searching for mail object with message ID: {message_id}")
            
            # Initialize COM for this thread
            if COM_AVAILABLE:
                assert pythoncom is not None and win32com is not None
                pythoncom.CoInitialize()
            
            try:
                # Create fresh COM objects for this thread
                assert win32com is not None
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                # Find the folder again (thread-safe approach)
                current_folder = None
                
                # Try to find the folder using the same logic as connect()
                for account in namespace.Accounts:
                    if not self.connection_config.email_address or account.SmtpAddress.lower() == self.connection_config.email_address.lower():
                        try:
                            delivery_store = account.DeliveryStore
                            if delivery_store:
                                root_folder = delivery_store.GetRootFolder()
                                current_folder = self._search_folder_recursive(root_folder, self.connection_config.folder_name)
                                if current_folder:
                                    break
                        except Exception as e:
                            logger.debug(f"Error searching account {account.SmtpAddress}: {e}")
                            continue
                
                if not current_folder:
                    logger.error(f"Folder '{self.connection_config.folder_name}' not found for mail object retrieval")
                    return None
                
                # Search for the email by message ID
                items = current_folder.Items
                
                # Use Restrict method to find the email efficiently
                filter_str = f"[InternetMessageId] = '{message_id}'"
                filtered_items = items.Restrict(filter_str)
                
                if filtered_items.Count > 0:
                    mail_object = filtered_items.GetFirst()
                    logger.debug(f"Found mail object for message ID: {message_id}")
                    return mail_object
                else:
                    # Fallback: search through items manually (slower but more reliable)
                    logger.debug(f"Direct filter failed, searching manually for message ID: {message_id}")
                    for mail in items:
                        try:
                            if hasattr(mail, 'InternetMessageId') and mail.InternetMessageId == message_id:
                                logger.debug(f"Found mail object via manual search: {message_id}")
                                return mail
                        except Exception as e:
                            logger.debug(f"Error checking mail item: {e}")
                            continue
                
                logger.warning(f"Mail object not found for message ID: {message_id}")
                return None
                
            finally:
                # Clean up COM for this thread
                if COM_AVAILABLE:
                    assert pythoncom is not None
                    pythoncom.CoUninitialize()
            
        except Exception as e:
            logger.error(f"Error getting mail object by ID {message_id}: {e}")
            return None
    
    def _search_folder_recursive(self, parent_folder, target_name, max_depth=3, current_depth=0):
        """Helper method for thread-safe folder searching"""
        if current_depth >= max_depth:
            return None
        
        try:
            for folder in parent_folder.Folders:
                try:
                    if folder.Name.lower() == target_name.lower():
                        return folder
                    
                    if hasattr(folder, 'Folders') and folder.Folders.Count > 0:
                        subfolder_result = self._search_folder_recursive(folder, target_name, max_depth, current_depth + 1)
                        if subfolder_result:
                            return subfolder_result
                            
                except Exception as e:
                    logger.debug(f"Error accessing folder during search: {e}")
                    continue
        except Exception as e:
            logger.debug(f"Error enumerating folders: {e}")
        
        return None


    # === Internal Helper Methods ===
    
    def _get_folder_by_name(self, folder_name: str) -> Optional[Any]:
        """Get Outlook folder by name"""
        try:
            if not self.namespace:
                return None
            
            def search_folders_recursive(parent_folder, target_name, max_depth=3, current_depth=0):
                """Recursively search for folder by name"""
                if current_depth >= max_depth:
                    return None
                
                try:
                    for folder in parent_folder.Folders:
                        try:
                            # Check if this folder matches (case-insensitive)
                            if folder.Name.lower() == target_name.lower():
                                return folder
                            
                            # Search subfolders recursively
                            if hasattr(folder, 'Folders') and folder.Folders.Count > 0:
                                subfolder_result = search_folders_recursive(folder, target_name, max_depth, current_depth + 1)
                                if subfolder_result:
                                    return subfolder_result
                                    
                        except Exception as e:
                            logger.debug(f"Error accessing folder during search: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Error enumerating folders: {e}")
                
                return None
                
            # Phase 1: Try standard folder mapping first
            if folder_name in self.folder_mapping:
                folder_id = self.folder_mapping[folder_name]
                return self.namespace.GetDefaultFolder(folder_id)
            
            # Phase 2: Search through all accounts' folders recursively
            for account in self.namespace.Accounts:
                try:
                    # Get the delivery store for this account
                    delivery_store = account.DeliveryStore
                    if delivery_store:
                        # Get root folder for this account's store
                        root_folder = delivery_store.GetRootFolder()
                        
                        # Search recursively in this account's folders
                        found_folder = search_folders_recursive(root_folder, folder_name)
                        if found_folder:
                            logger.debug(f"Found folder '{folder_name}' in account {account.SmtpAddress}")
                            return found_folder
                except Exception as e:
                    logger.debug(f"Error searching account {account.SmtpAddress}: {e}")
                    continue
            
            # Phase 3: Fallback - search namespace folders directly
            try:
                found_folder = search_folders_recursive(self.namespace, folder_name)
                if found_folder:
                    return found_folder
            except Exception as e:
                logger.debug(f"Error in fallback search: {e}")
                    
            return None
        except Exception as e:
            logger.error(f"Error finding folder {folder_name}: {e}")
            return None
    
    def _test_get_folder_by_name(self, namespace: Any, folder_name: str) -> Optional[Any]:
        """Get Outlook folder by name for testing (doesn't use self.namespace)"""
        try:
            # Try standard folder mapping first
            if folder_name in self.folder_mapping:
                folder_id = self.folder_mapping[folder_name]
                return namespace.GetDefaultFolder(folder_id)
            
            # Try finding by name in all folders
            for folder in namespace.Folders:
                if folder.Name.lower() == folder_name.lower():
                    return folder
                    
            return None
        except Exception as e:
            logger.error(f"Error finding folder {folder_name}: {e}")
            return None
    
    def _convert_outlook_email(self, outlook_mail: Any) -> EmailData:
        """Convert Outlook mail item to EmailData"""
        try:
            # Get basic email properties
            message_id = outlook_mail.EntryID or ""
            subject = outlook_mail.Subject or ""
            sender_email = outlook_mail.SenderEmailAddress or ""
            sender_name = outlook_mail.SenderName
            
            # Convert received time to UTC for consistent storage
            received_time_local = outlook_mail.ReceivedTime
            logger.info(f"Raw Outlook ReceivedTime: {received_time_local}, tzinfo: {getattr(received_time_local, 'tzinfo', 'No tzinfo attribute')}")
            
            # Handle timezone conversion - Outlook mislabels local time as UTC
            if hasattr(received_time_local, 'tzinfo') and received_time_local.tzinfo is not None:
                logger.info("Outlook returned timezone-aware datetime - treating as local time mislabeled as UTC")
                # Outlook mislabels local time as UTC, so we ignore the timezone info
                # and treat the time values as local time, then convert to UTC
                import time
                from datetime import timezone as dt_timezone
                
                # Get the time values but ignore the incorrect timezone info
                local_time_naive = datetime(
                    received_time_local.year, received_time_local.month, received_time_local.day,
                    received_time_local.hour, received_time_local.minute, received_time_local.second,
                    received_time_local.microsecond
                )
                
                # Get the system's local timezone with proper DST handling
                # This automatically detects whether DST is in effect for this date
                local_timestamp = local_time_naive.timestamp()
                local_time_with_tz = datetime.fromtimestamp(local_timestamp)
                utc_time = datetime.utcfromtimestamp(local_timestamp)
                
                # Make timezone-naive for storage
                received_time = datetime(
                    utc_time.year, utc_time.month, utc_time.day,
                    utc_time.hour, utc_time.minute, utc_time.second,
                    utc_time.microsecond
                )
                
                # Calculate the actual offset for logging
                offset_seconds = (local_timestamp - datetime.fromtimestamp(local_timestamp, tz=dt_timezone.utc).replace(tzinfo=None).timestamp())
                offset_hours = -offset_seconds / 3600  # Negative because we're going from local to UTC
                
                logger.info(f"Converted email time: {received_time_local} (mislabeled as UTC) -> {local_time_naive} (local) -> {received_time} (UTC naive) [offset: {offset_hours:+.0f} hours]")
            elif hasattr(received_time_local, 'replace') and received_time_local.tzinfo is None:
                logger.info("Converting local time to UTC...")
                # Outlook returned timezone-naive datetime - treat as local time and convert to UTC
                import time
                from datetime import timezone as dt_timezone
                
                # Use system timezone handling with automatic DST detection
                local_timestamp = received_time_local.timestamp()
                utc_time = datetime.utcfromtimestamp(local_timestamp)
                
                # Explicitly create timezone-naive datetime in UTC
                received_time = datetime(
                    utc_time.year, utc_time.month, utc_time.day,
                    utc_time.hour, utc_time.minute, utc_time.second,
                    utc_time.microsecond
                )
                
                # Calculate the actual offset for logging
                offset_seconds = (local_timestamp - datetime.fromtimestamp(local_timestamp, tz=dt_timezone.utc).replace(tzinfo=None).timestamp())
                offset_hours = -offset_seconds / 3600
                
                logger.info(f"Converted email time: {received_time_local} (local) -> {received_time} (UTC) [offset: {offset_hours:+.0f} hours], tzinfo: {received_time.tzinfo}")
            else:
                logger.info("Using fallback - no timezone conversion")
                # Fallback - assume it's already in correct format
                received_time = received_time_local
            
            # Get attachment information
            has_attachments = outlook_mail.Attachments.Count > 0
            attachment_count = outlook_mail.Attachments.Count
            attachment_filenames = []
            has_pdf_attachments = False
            
            if has_attachments:
                for attachment in outlook_mail.Attachments:
                    filename = attachment.FileName
                    attachment_filenames.append(filename)
                    if filename.lower().endswith('.pdf'):
                        has_pdf_attachments = True
            
            # Get body preview (first 200 characters)
            body_preview = None
            if outlook_mail.Body:
                body_preview = outlook_mail.Body[:200]
            
            return EmailData(
                message_id=message_id,
                subject=subject,
                sender_email=sender_email,
                sender_name=sender_name,
                received_time=received_time,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
                attachment_filenames=attachment_filenames,
                has_pdf_attachments=has_pdf_attachments,
                body_preview=body_preview
            )
            
        except Exception as e:
            logger.error(f"Error converting email: {e}")
            raise Exception(f"Failed to convert email: {e}")