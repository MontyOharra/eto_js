"""
Outlook Service for ETO
Handles COM connections to Outlook and email monitoring
"""

import win32com.client
import pythoncom
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import win32com.client.gencache

logger = logging.getLogger(__name__)

class OutlookService:
    def __init__(self):
        self.outlook = None
        self.namespace = None
        self.inbox = None
        self.monitoring = False
        self.monitor_thread = None
        self.current_email = None
        self.current_folder = None
        self.processed_emails = set()
        self.last_poll_time = None
        self._lock = threading.Lock()
        
        # Event-based monitoring
        self.event_handler = None
        self.use_event_monitoring = True  # Prefer events over polling
        self.fallback_to_polling = False  # Track if we fell back to polling
        
        # Database and storage services
        self.db_service = None
        self.pdf_storage = None
        
        # Outlook folder constants mapping
        self.folder_mapping = {
            'Inbox': 6,           # olFolderInbox
            'Outbox': 4,          # olFolderOutbox
            'Sent': 5,            # olFolderSentMail
            'SentMail': 5,        # olFolderSentMail (alternative)
            'Drafts': 16,         # olFolderDrafts
            'DeletedItems': 3,    # olFolderDeletedItems
            'Trash': 3,           # olFolderDeletedItems (alternative)
            'Junk': 23,           # olFolderJunk
            'JunkEmail': 23,      # olFolderJunk (alternative)
            'Calendar': 9,        # olFolderCalendar
            'Contacts': 10,       # olFolderContacts
            'Tasks': 13,          # olFolderTasks
            'Notes': 12,          # olFolderNotes
            'Journal': 11         # olFolderJournal
        }
    
    def set_database_service(self, db_service):
        """Set the database service for storing email and PDF data"""
        self.db_service = db_service
        logger.info("Database service configured for Outlook service")
    
    def set_pdf_storage(self, pdf_storage):
        """Set the PDF storage service for saving attachments"""
        self.pdf_storage = pdf_storage
        logger.info("PDF storage service configured for Outlook service")
    
    def set_pdf_extractor(self, pdf_extractor):
        """Set the PDF extractor service for extracting objects during ingestion"""
        self.pdf_extractor = pdf_extractor
        logger.info("PDF extractor service configured for Outlook service")
    
    def _get_folder(self, account, folder_name: str):
        """Get folder by name, supporting both standard and custom folders"""
        try:
            # First try standard folders using constants
            if folder_name in self.folder_mapping:
                folder_constant = self.folder_mapping[folder_name]
                try:
                    folder = account.DeliveryStore.GetDefaultFolder(folder_constant)
                    logger.info(f"Found standard folder: {folder_name} -> {folder.Name}")
                    return folder
                except Exception as std_error:
                    logger.warning(f"Could not access standard folder {folder_name}: {std_error}")
            
            # If not a standard folder or standard folder failed, search custom folders
            logger.info(f"Searching for custom folder: {folder_name}")
            root_folder = account.DeliveryStore.GetRootFolder()
            
            # Search in root level folders
            for folder in root_folder.Folders:
                if folder.Name.lower() == folder_name.lower():
                    logger.info(f"Found custom folder: {folder_name} -> {folder.Name}")
                    return folder
            
            # Search in Inbox subfolders (common location for custom folders)
            try:
                inbox = account.DeliveryStore.GetDefaultFolder(6)  # olFolderInbox
                for folder in inbox.Folders:
                    if folder.Name.lower() == folder_name.lower():
                        logger.info(f"Found custom folder in Inbox: {folder_name} -> {folder.Name}")
                        return folder
            except Exception as inbox_error:
                logger.warning(f"Could not search Inbox subfolders: {inbox_error}")
            
            # If we get here, folder was not found
            available_folders = []
            try:
                # List available folders for error message
                for folder in root_folder.Folders:
                    available_folders.append(folder.Name)
                    # Add subfolders of major folders
                    if folder.Name in ['Inbox', 'Sent Items', 'Drafts']:
                        for subfolder in folder.Folders:
                            available_folders.append(f"{folder.Name}/{subfolder.Name}")
            except:
                pass
            
            error_msg = f"Folder '{folder_name}' not found."
            if available_folders:
                error_msg += f" Available folders: {', '.join(available_folders[:10])}"  # Limit to first 10
            
            raise Exception(error_msg)
            
        except Exception as e:
            logger.error(f"Error accessing folder '{folder_name}': {e}")
            raise Exception(f"Could not access folder '{folder_name}': {str(e)}")
        
    def connect_default(self, folder_name: str = 'Inbox') -> Dict[str, Any]:
        """Connect to Outlook using default account"""
        try:
            logger.info(f"Connecting to Outlook using default account, folder: {folder_name}")
            
            # Initialize COM
            pythoncom.CoInitialize()
            
            # Initialize Outlook COM objects
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            
            # Use default account
            account = self.namespace.Accounts.Item(1)
            
            # Get the specified folder for this account
            self.inbox = self._get_folder(account, folder_name)
            self.current_email = account.DisplayName
            self.current_folder = folder_name
            
            logger.info(f"Successfully connected to Outlook {folder_name} for {account.DisplayName}")
            
            # Initialize email cursor for downtime recovery
            if self.db_service:
                try:
                    cursor = self.db_service.get_or_create_email_cursor(account.DisplayName, folder_name)
                    if cursor.last_processed_received_date:
                        logger.info(f"Found existing cursor from: {cursor.last_processed_received_date}")
                        
                        # Check for missed emails during downtime
                        self._process_missed_emails_since_cursor(cursor)
                        
                        # Set poll time to NOW for future monitoring (not cursor time)
                        self.last_poll_time = datetime.now()
                        logger.info(f"After processing missed emails, set poll time to: {self.last_poll_time}")
                    else:
                        # First time setup - start from now
                        self.last_poll_time = datetime.now()
                        logger.info(f"First run - set cursor to: {self.last_poll_time}")
                except Exception as cursor_error:
                    logger.error(f"Error initializing email cursor: {cursor_error}")
                    # Fallback to current time
                    self.last_poll_time = datetime.now()
            else:
                # No database service - use current time
                self.last_poll_time = datetime.now()
                logger.info(f"Set cursor to current time: {self.last_poll_time}")
            
            return {
                "status": "connected",
                "email": account.DisplayName,
                "account_name": account.DisplayName,
                "folder_name": folder_name,
                "inbox_name": self.inbox.Name,
                "message_count": self.inbox.Items.Count
            }
            
        except Exception as e:
            logger.error(f"Failed to connect to Outlook: {e}")
            self.disconnect()
            raise Exception(f"Outlook connection failed: {str(e)}")
    
    def connect(self, email_address: str, folder_name: str = 'Inbox') -> Dict[str, Any]:
        """Connect to Outlook and access specific email account"""
        try:
            logger.info(f"Connecting to Outlook for email: {email_address}, folder: {folder_name}")
            
            # Initialize COM
            pythoncom.CoInitialize()
            
            # Initialize Outlook COM objects
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            
            # Try to get the specific account
            try:
                account = self.namespace.Accounts.Item(email_address)
                logger.info(f"Found account: {account.DisplayName}")
            except Exception as e:
                logger.warning(f"Could not find specific account {email_address}, using default: {e}")
                # Use default account if specific one not found
                account = self.namespace.Accounts.Item(1)
            
            # Get the specified folder for this account
            self.inbox = self._get_folder(account, folder_name)
            self.current_email = email_address
            self.current_folder = folder_name
            
            logger.info(f"Successfully connected to Outlook {folder_name} for {email_address}")
            
            # Initialize email cursor for downtime recovery
            if self.db_service:
                try:
                    cursor = self.db_service.get_or_create_email_cursor(email_address, folder_name)
                    if cursor.last_processed_received_date:
                        logger.info(f"Found existing cursor from: {cursor.last_processed_received_date}")
                        
                        # Check for missed emails during downtime
                        self._process_missed_emails_since_cursor(cursor)
                        
                        # Set poll time to NOW for future monitoring (not cursor time)
                        self.last_poll_time = datetime.now()
                        logger.info(f"After processing missed emails, set poll time to: {self.last_poll_time}")
                    else:
                        # First time setup - start from now
                        self.last_poll_time = datetime.now()
                        logger.info(f"First run - set cursor to: {self.last_poll_time}")
                except Exception as cursor_error:
                    logger.error(f"Error initializing email cursor: {cursor_error}")
                    # Fallback to current time
                    self.last_poll_time = datetime.now()
            else:
                # No database service - use current time
                self.last_poll_time = datetime.now()
                logger.info(f"Set cursor to current time: {self.last_poll_time}")
            
            return {
                "status": "connected",
                "email": email_address,
                "account_name": account.DisplayName,
                "folder_name": folder_name,
                "inbox_name": self.inbox.Name,
                "message_count": self.inbox.Items.Count
            }
            
        except Exception as e:
            logger.error(f"Failed to connect to Outlook: {e}")
            self.disconnect()
            raise Exception(f"Outlook connection failed: {str(e)}")
    
    def disconnect(self) -> Dict[str, str]:
        """Disconnect from Outlook"""
        try:
            # Stop monitoring first (this handles thread cleanup properly)
            if self.monitoring:
                self.stop_monitoring()
            
            with self._lock:
                # Clean up event monitoring if active
                self._cleanup_event_monitoring()
                
                self.outlook = None
                self.namespace = None
                self.inbox = None
                self.current_email = None
                self.current_folder = None
                self.processed_emails.clear()
                self.last_poll_time = None
                self.fallback_to_polling = False
                
                # Uninitialize COM
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass  # Ignore errors on uninitialize
                
            logger.info("Disconnected from Outlook")
            return {"status": "disconnected"}
            
        except Exception as e:
            logger.error(f"Error disconnecting from Outlook: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        try:
            # Initialize COM for this thread if not already done
            pythoncom.CoInitialize()
            
            if not self.current_email:
                return {
                    "status": "disconnected",
                    "email": None,
                    "monitoring": False
                }
            
            # Try to reconnect if objects are stale
            if not self.outlook or not self.inbox:
                try:
                    self._reconnect()
                except Exception as reconnect_error:
                    logger.warning(f"Failed to reconnect: {reconnect_error}")
                    return {
                        "status": "connection_lost",
                        "email": self.current_email,
                        "monitoring": self.monitoring,
                        "message": "Connection lost, try restarting"
                    }
            
            # Test the connection by accessing inbox count
            inbox_count = 0
            try:
                inbox_count = self.inbox.Items.Count if self.inbox else 0
            except Exception as count_error:
                logger.warning(f"Could not get inbox count: {count_error}")
                # Try to reconnect
                self._reconnect()
                inbox_count = self.inbox.Items.Count if self.inbox else 0
            
            return {
                "status": "connected",
                "email": self.current_email,
                "monitoring": self.monitoring,
                "monitoring_method": "polling" if self.fallback_to_polling else "events",
                "processed_count": len(self.processed_emails),
                "inbox_count": inbox_count,
                "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None,
                "event_monitoring_active": self.event_handler is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _reconnect(self, max_retries: int = 3, retry_delay: int = 5):
        """
        Reconnect to Outlook using stored email and folder with retry logic
        
        Args:
            max_retries: Maximum number of reconnection attempts
            retry_delay: Delay in seconds between retry attempts
        """
        if not self.current_email:
            raise Exception("No email address stored for reconnection")
        
        folder_name = self.current_folder or 'Inbox'
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Reconnecting to Outlook for: {self.current_email}, folder: {folder_name} (attempt {attempt + 1}/{max_retries})")
                
                # Clean up any existing COM objects first
                try:
                    if hasattr(self, 'outlook') and self.outlook:
                        self.outlook = None
                    if hasattr(self, 'namespace') and self.namespace:
                        self.namespace = None
                    if hasattr(self, 'inbox') and self.inbox:
                        self.inbox = None
                except:
                    pass  # Ignore cleanup errors
                
                # Uninitialize and reinitialize COM for this thread
                try:
                    pythoncom.CoUninitialize()
                except:
                    pass  # Ignore if not initialized
                
                time.sleep(1)  # Brief pause for COM cleanup
                pythoncom.CoInitialize()
                
                # Re-initialize COM objects with error handling
                try:
                    self.outlook = win32com.client.Dispatch("Outlook.Application")
                    if not self.outlook:
                        raise Exception("Failed to create Outlook Application object")
                    
                    self.namespace = self.outlook.GetNamespace("MAPI")
                    if not self.namespace:
                        raise Exception("Failed to get MAPI namespace")
                    
                except Exception as com_error:
                    raise Exception(f"COM initialization failed: {com_error}")
                
                # Get the account with improved error handling
                account = None
                try:
                    # Try specific account first
                    account = self.namespace.Accounts.Item(self.current_email)
                    logger.debug(f"Found specific account: {account.DisplayName}")
                except Exception as account_error:
                    logger.warning(f"Could not find account '{self.current_email}': {account_error}")
                    
                    # Try default account as fallback
                    try:
                        account = self.namespace.Accounts.Item(1)
                        logger.info(f"Using default account: {account.DisplayName}")
                    except Exception as default_error:
                        raise Exception(f"Failed to get default account: {default_error}")
                
                if not account:
                    raise Exception("No account available for connection")
                
                # Get the specified folder with better error handling
                try:
                    self.inbox = self._get_folder(account, folder_name)
                    if not self.inbox:
                        raise Exception(f"Failed to get folder '{folder_name}'")
                        
                except Exception as folder_error:
                    raise Exception(f"Folder access failed: {folder_error}")
                
                # Test the connection by accessing a basic property
                try:
                    inbox_count = self.inbox.Items.Count
                    logger.info(f"Reconnected successfully to {account.DisplayName} {folder_name} ({inbox_count} items)")
                    return  # Success, exit retry loop
                    
                except Exception as test_error:
                    raise Exception(f"Connection test failed: {test_error}")
                
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying reconnection in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Final attempt failed
                    logger.error(f"All {max_retries} reconnection attempts failed")
                    raise Exception(f"Reconnection failed after {max_retries} attempts: {str(e)}")
    
    def start_monitoring(self) -> Dict[str, str]:
        """Start monitoring the inbox for new emails using events or polling fallback"""
        try:
            with self._lock:
                if not self.outlook or not self.inbox:
                    raise Exception("Not connected to Outlook")
                
                if self.monitoring:
                    return {"status": "already_monitoring"}
                
                self.monitoring = True
                
                # Try event-based monitoring first
                if self.use_event_monitoring and self._setup_event_monitoring():
                    logger.info("Started event-based email monitoring")
                    return {"status": "monitoring_started", "method": "events"}
                else:
                    # Fall back to polling if events fail
                    logger.warning("Event monitoring failed, falling back to polling")
                    self.fallback_to_polling = True
                    self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self.monitor_thread.start()
                    logger.info("Started polling-based email monitoring")
                    return {"status": "monitoring_started", "method": "polling"}
                
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.monitoring = False
            return {"status": "error", "message": str(e)}
    
    def stop_monitoring(self) -> Dict[str, str]:
        """Stop monitoring the inbox (both events and polling)"""
        try:
            with self._lock:
                if not self.monitoring:
                    return {"status": "not_monitoring"}
                
                self.monitoring = False
                monitor_thread = self.monitor_thread
                
            # Clean up event monitoring
            self._cleanup_event_monitoring()
            
            # Wait for polling thread to finish if it exists
            if monitor_thread and monitor_thread.is_alive():
                logger.info("Waiting for monitoring thread to stop...")
                monitor_thread.join(timeout=10)  # Wait up to 10 seconds
                
                if monitor_thread.is_alive():
                    logger.warning("Monitoring thread did not stop within timeout")
                else:
                    logger.info("Monitoring thread stopped successfully")
            
            with self._lock:
                self.monitor_thread = None
                self.fallback_to_polling = False
                
            logger.info("Stopped monitoring Outlook inbox")
            return {"status": "monitoring_stopped"}
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return {"status": "error", "message": str(e)}
    
    def _setup_event_monitoring(self) -> bool:
        """
        Setup Outlook COM event monitoring for immediate email processing
        Returns True if events were successfully configured, False otherwise
        """
        try:
            logger.info("Setting up Outlook event monitoring")
            
            # Create event handler class for this service instance
            class OutlookEventHandler:
                def __init__(self, outlook_service):
                    self.outlook_service = outlook_service
                    logger.info("Outlook event handler initialized")
                
                def OnNewMailEx(self, entry_ids):
                    """Handle new mail events - called when new emails arrive"""
                    try:
                        logger.info(f"New mail event received with {len(entry_ids.split(',')) if entry_ids else 0} emails")
                        
                        if not self.outlook_service.monitoring:
                            return
                        
                        # Process each new email entry ID
                        for entry_id in entry_ids.split(',') if entry_ids else []:
                            entry_id = entry_id.strip()
                            if entry_id:
                                self.outlook_service._process_new_email_by_id(entry_id)
                                
                    except Exception as e:
                        logger.error(f"Error in OnNewMailEx event handler: {e}")
                
                def OnItemAdd(self, item):
                    """Handle item add events in the monitored folder"""
                    try:
                        # Check if this is an email (MailItem) with PDF attachments
                        if hasattr(item, 'Class') and item.Class == 43:  # olMail
                            if self.outlook_service._has_pdf_attachments(item):
                                logger.info(f"New email with PDF detected via OnItemAdd: {item.Subject}")
                                self.outlook_service._process_email(item)
                                self.outlook_service.processed_emails.add(item.EntryID)
                    except Exception as e:
                        logger.error(f"Error in OnItemAdd event handler: {e}")
            
            # Create event handler instance
            self.event_handler = OutlookEventHandler(self)
            
            # Set up Application-level events (for NewMailEx)
            try:
                # Use early binding for more reliable event handling
                win32com.client.gencache.EnsureDispatch("Outlook.Application")
                
                # Connect to application events
                self.outlook.NewMailEx = self.event_handler.OnNewMailEx
                logger.info("Connected to Outlook NewMailEx events")
                
                # Also set up folder-level events for the monitored folder
                if self.inbox:
                    # Connect to folder item add events
                    self.inbox.Items.ItemAdd = self.event_handler.OnItemAdd
                    logger.info(f"Connected to folder ItemAdd events for {self.inbox.Name}")
                
                logger.info("Event monitoring setup completed successfully")
                return True
                
            except Exception as event_error:
                logger.error(f"Failed to connect to Outlook events: {event_error}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to setup event monitoring: {e}")
            return False
    
    def _cleanup_event_monitoring(self):
        """Clean up event monitoring connections"""
        try:
            if self.event_handler:
                logger.info("Cleaning up Outlook event monitoring")
                
                # Disconnect from events
                try:
                    if self.outlook:
                        self.outlook.NewMailEx = None
                        logger.debug("Disconnected from NewMailEx events")
                except:
                    pass
                
                try:
                    if self.inbox and self.inbox.Items:
                        self.inbox.Items.ItemAdd = None
                        logger.debug("Disconnected from ItemAdd events")
                except:
                    pass
                
                self.event_handler = None
                logger.info("Event monitoring cleanup completed")
                
        except Exception as e:
            logger.error(f"Error cleaning up event monitoring: {e}")
    
    def _process_new_email_by_id(self, entry_id: str):
        """Process a new email by its EntryID (for event-based monitoring)"""
        try:
            # Skip if already processed
            if entry_id in self.processed_emails:
                return
            
            logger.info(f"Processing new email by EntryID: {entry_id[:20]}...")
            
            # Get the email item by EntryID
            try:
                email_item = self.namespace.GetItemFromID(entry_id)
            except Exception as get_error:
                logger.warning(f"Could not retrieve email with EntryID {entry_id[:20]}...: {get_error}")
                return
            
            # Check if it's in our monitored folder and has PDF attachments
            try:
                # Check if email has PDF attachments
                if self._has_pdf_attachments(email_item):
                    logger.info(f"Processing new email with PDF: {email_item.Subject}")
                    self._process_email(email_item)
                    self.processed_emails.add(entry_id)
                    
                    # Update last poll time to track processing
                    self.last_poll_time = datetime.now()
                else:
                    logger.debug(f"Email has no PDF attachments, skipping: {email_item.Subject}")
                    
            except Exception as process_error:
                logger.error(f"Error processing email {entry_id[:20]}...: {process_error}")
                
        except Exception as e:
            logger.error(f"Error in _process_new_email_by_id for {entry_id[:20]}...: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        # Create thread-specific COM objects
        thread_outlook = None
        thread_namespace = None
        thread_inbox = None
        
        try:
            while self.monitoring:
                try:
                    # Check if we should stop before doing any work
                    if not self.monitoring:
                        break
                        
                    # Recreate COM objects for this thread if needed
                    if not thread_outlook or not thread_inbox:
                        # Check again if we should stop before connecting
                        if not self.monitoring:
                            break
                            
                        thread_outlook = win32com.client.Dispatch("Outlook.Application")
                        thread_namespace = thread_outlook.GetNamespace("MAPI")
                        
                        # Get the account
                        try:
                            account = thread_namespace.Accounts.Item(self.current_email)
                        except:
                            account = thread_namespace.Accounts.Item(1)
                        
                        # Get folder for this thread
                        folder_name = self.current_folder or 'Inbox'
                        thread_inbox = self._get_folder(account, folder_name)
                        logger.info(f"Monitoring thread connected to {folder_name}")
                    
                    # Check again before processing emails
                    if self.monitoring and thread_inbox:
                        self._check_for_new_emails_thread(thread_inbox)
                    
                    # Sleep in smaller chunks and check monitoring flag
                    for _ in range(30):  # 30 seconds total, but check every second
                        if not self.monitoring:
                            break
                        time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    # Reset COM objects on error
                    thread_outlook = None
                    thread_namespace = None
                    thread_inbox = None
                    
                    # Sleep in smaller chunks on error too
                    for _ in range(60):  # 60 seconds total, but check every second
                        if not self.monitoring:
                            break
                        time.sleep(1)
        finally:
            # Uninitialize COM for this thread
            pythoncom.CoUninitialize()
            
        logger.info("Monitoring loop stopped")
    
    def _check_for_new_emails_thread(self, thread_inbox):
        """Check for new emails with PDF attachments (thread-safe version)"""
        try:
            messages = thread_inbox.Items
            messages.Sort("[ReceivedTime]", True)  # Sort by received time, newest first
            
            new_emails_processed = 0
            current_poll_time = datetime.now()
            
            
            for message in messages:
                # Check if monitoring was stopped during processing
                if not self.monitoring:
                    logger.info("Monitoring stopped during email processing, breaking loop")
                    break
                    
                # Only process emails received after last poll time
                if self.last_poll_time and message.ReceivedTime:
                    try:
                        # Convert Outlook COM datetime to naive Python datetime
                        received_time = message.ReceivedTime
                        
                        # Outlook COM dates are timezone-aware, convert to naive
                        if hasattr(received_time, 'replace') and received_time.tzinfo is not None:
                            # Remove timezone info to make it naive
                            message_time = received_time.replace(tzinfo=None)
                        else:
                            # If it's already naive or needs conversion
                            message_time = received_time
                        
                        # Ensure last_poll_time is also naive and not None
                        poll_time = self.last_poll_time
                        if poll_time is None:
                            logger.info("Poll time is None, skipping time comparison")
                            continue  # Skip if cursor was cleared
                            
                        if hasattr(poll_time, 'replace') and poll_time.tzinfo is not None:
                            poll_time = poll_time.replace(tzinfo=None)
                        
                        # Add a small buffer (30 seconds) to account for timing issues
                        from datetime import timedelta
                        poll_time_with_buffer = poll_time - timedelta(seconds=30)
                        
                        if message_time <= poll_time_with_buffer:
                            continue  # Skip older emails
                            
                    except Exception as time_error:
                        logger.warning(f"Error comparing message time, skipping message: {time_error}")
                        continue  # Skip this message instead of processing it
                
                # Skip if already processed by EntryID (backup check)
                if message.EntryID in self.processed_emails:
                    continue
                
                # Check if email has PDF attachments
                if self._has_pdf_attachments(message):
                    logger.info(f"Found new email with PDF: {message.Subject} (received: {message.ReceivedTime})")
                    self._process_email(message)
                    self.processed_emails.add(message.EntryID)
                    new_emails_processed += 1
            
            # Update cursor after successful poll (only if still monitoring)
            if self.monitoring:
                if new_emails_processed > 0:
                    logger.info(f"Processed {new_emails_processed} new emails with PDFs")
                
                # Update the last poll time only if still monitoring
                self.last_poll_time = current_poll_time
                    
        except Exception as e:
            logger.error(f"Error checking emails in thread: {e}")
    
    def _check_for_new_emails(self):
        """Check for new emails with PDF attachments"""
        try:
            messages = self.inbox.Items
            messages.Sort("[ReceivedTime]", True)  # Sort by received time, newest first
            
            for message in messages:
                # Skip if already processed
                if message.EntryID in self.processed_emails:
                    continue
                
                # Check if email has PDF attachments
                if self._has_pdf_attachments(message):
                    logger.info(f"Found new email with PDF: {message.Subject}")
                    self._process_email(message)
                    self.processed_emails.add(message.EntryID)
                    
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
    
    def _has_pdf_attachments(self, message) -> bool:
        """Check if email has PDF attachments"""
        try:
            for attachment in message.Attachments:
                filename = attachment.FileName.lower()
                if filename.endswith('.pdf'):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking attachments: {e}")
            return False
    
    def _process_email(self, message, max_retries: int = 3):
        """
        Process email with PDF attachments and store in database with error recovery
        
        Args:
            message: Outlook message object
            max_retries: Maximum retry attempts for transient failures
        """
        message_subject = "Unknown"
        try:
            message_subject = getattr(message, 'Subject', 'Unknown Subject')
            
            if not self.db_service or not self.pdf_storage:
                logger.error("Database service or PDF storage not configured")
                return
            
            logger.info(f"Processing email: '{message_subject}'")
            
            # Extract PDF attachments with error handling
            pdf_attachments = []
            try:
                pdf_attachments = [att for att in message.Attachments if att.FileName.lower().endswith('.pdf')]
            except Exception as att_error:
                logger.error(f"Error accessing attachments for '{message_subject}': {att_error}")
                return
            
            if not pdf_attachments:
                logger.debug(f"Email '{message_subject}' has no PDF attachments, skipping")
                return
            
            logger.info(f"Found {len(pdf_attachments)} PDF attachments in '{message_subject}'")
            
            # Create email record in database with retry logic
            email_record = None
            for attempt in range(max_retries):
                try:
                    # Safely extract email properties
                    email_data = {
                        "message_id": getattr(message, 'EntryID', f'unknown_{int(time.time())}'),
                        "subject": message_subject,
                        "sender_email": getattr(message, 'SenderEmailAddress', 'unknown@unknown.com'),
                        "sender_name": getattr(message, 'SenderName', None),
                        "received_date": getattr(message, 'ReceivedTime', datetime.now()),
                        "folder_name": self.current_folder,
                        "has_pdf_attachments": True,
                        "attachment_count": len(pdf_attachments)
                    }
                    
                    email_record = self.db_service.create_email_record(email_data)
                    logger.info(f"Created email record ID: {email_record.id} for '{message_subject}'")
                    break  # Success, exit retry loop
                    
                except Exception as db_error:
                    logger.error(f"Database error creating email record for '{message_subject}' (attempt {attempt + 1}): {db_error}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        logger.error(f"Failed to create email record after {max_retries} attempts, skipping email")
                        return
            
            # Process each PDF attachment with error isolation
            processed_pdfs = 0
            failed_pdfs = 0
            
            for i, attachment in enumerate(pdf_attachments):
                attachment_name = "unknown_attachment"
                try:
                    attachment_name = getattr(attachment, 'FileName', f'attachment_{i}')
                    logger.info(f"Processing PDF attachment {i+1}/{len(pdf_attachments)}: {attachment_name}")
                    
                    pdf_result = self._store_pdf_attachment_with_retry(attachment, email_record.id, max_retries)
                    
                    if pdf_result['success']:
                        processed_pdfs += 1
                        logger.info(f"Successfully processed PDF: {attachment_name} -> {pdf_result['sha256_hash']}")
                    else:
                        failed_pdfs += 1
                        logger.error(f"Failed to process PDF: {attachment_name} - {pdf_result.get('error', 'Unknown error')}")
                        
                except Exception as pdf_error:
                    failed_pdfs += 1
                    logger.error(f"Unexpected error processing PDF attachment '{attachment_name}': {pdf_error}")
            
            # Log processing summary
            if processed_pdfs > 0:
                logger.info(f"Email processing completed: '{message_subject}' - {processed_pdfs}/{len(pdf_attachments)} PDFs processed successfully")
            else:
                logger.warning(f"Email processing completed with no successful PDFs: '{message_subject}' - 0/{len(pdf_attachments)} PDFs processed")
            
            # Update email cursor with this processed email (even if some PDFs failed)
            self._update_email_cursor_safe(message, processed_pdfs)
            
        except Exception as e:
            logger.error(f"Critical error processing email '{message_subject}': {e}")
            # Don't re-raise - we want to continue processing other emails
    
    def _store_pdf_attachment_with_retry(self, attachment, email_id: int, max_retries: int = 3):
        """Store PDF attachment with retry logic for transient failures"""
        attachment_name = "unknown"
        
        for attempt in range(max_retries):
            try:
                attachment_name = getattr(attachment, 'FileName', f'attachment_{int(time.time())}')
                
                if attempt > 0:
                    logger.info(f"Retrying PDF storage for '{attachment_name}' (attempt {attempt + 1}/{max_retries})")
                
                result = self._store_pdf_attachment(attachment, email_id)
                
                if result['success']:
                    return result
                else:
                    # Check if this is a retryable error
                    error_msg = result.get('error', '')
                    if self._is_retryable_error(error_msg):
                        if attempt < max_retries - 1:
                            backoff_time = 2 ** attempt
                            logger.warning(f"Retryable error for '{attachment_name}', retrying in {backoff_time}s: {error_msg}")
                            time.sleep(backoff_time)
                            continue
                    
                    # Non-retryable error or final attempt
                    logger.error(f"Final failure storing PDF '{attachment_name}': {error_msg}")
                    return result
                    
            except Exception as e:
                error_msg = str(e)
                if self._is_retryable_error(error_msg) and attempt < max_retries - 1:
                    backoff_time = 2 ** attempt
                    logger.warning(f"Exception storing PDF '{attachment_name}', retrying in {backoff_time}s: {error_msg}")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Final exception storing PDF '{attachment_name}': {error_msg}")
                    return {
                        'success': False,
                        'error': f'Exception after {max_retries} attempts: {error_msg}'
                    }
        
        return {
            'success': False,
            'error': f'Failed after {max_retries} retry attempts'
        }
    
    def _is_retryable_error(self, error_msg: str) -> bool:
        """Determine if an error is likely to be transient and retryable"""
        retryable_keywords = [
            'timeout',
            'connection',
            'network',
            'temporary',
            'busy',
            'locked',
            'com error',
            'rpc',
            'access denied'
        ]
        
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in retryable_keywords)
    
    def _update_email_cursor_safe(self, message, processed_pdfs: int):
        """Safely update email cursor with error handling"""
        try:
            if not self.current_email or not self.current_folder:
                return
            
            # Convert received time to naive datetime for storage
            received_time = getattr(message, 'ReceivedTime', datetime.now())
            if hasattr(received_time, 'replace') and received_time.tzinfo is not None:
                received_time = received_time.replace(tzinfo=None)
            
            message_id = getattr(message, 'EntryID', f'unknown_{int(time.time())}')
            
            self.db_service.update_email_cursor(
                self.current_email, 
                self.current_folder,
                message_id,
                received_time
            )
            
            # Update PDF count in cursor
            if processed_pdfs > 0:
                for _ in range(processed_pdfs):
                    self.db_service.increment_cursor_pdf_count(self.current_email, self.current_folder)
                    
            logger.debug(f"Updated email cursor for {self.current_email}/{self.current_folder}")
            
        except Exception as cursor_error:
            logger.error(f"Error updating email cursor: {cursor_error}")
            # Don't re-raise - cursor update failure shouldn't stop email processing
    
    def _store_pdf_attachment(self, attachment, email_id):
        """Store PDF attachment and create database records"""
        try:
            # Save PDF to storage
            storage_result = self.pdf_storage.save_pdf_attachment(attachment)
            
            if not storage_result['success']:
                logger.error(f"Failed to save PDF: {storage_result.get('error', 'Unknown error')}")
                return storage_result
            
            # Create PDF file record in database (allow duplicates from different emails)
            pdf_data = {
                "email_id": email_id,
                "filename": f"{storage_result['sha256_hash']}.pdf",
                "original_filename": attachment.FileName,
                "file_path": storage_result['file_path'],
                "file_size": storage_result['file_size'],
                "sha256_hash": storage_result['sha256_hash'],
                "page_count": storage_result.get('page_count')
            }
            
            pdf_record = self.db_service.create_pdf_file(pdf_data)
            
            # Extract PDF objects immediately and store in pdf_files.objects_json (new workflow requirement)
            try:
                if hasattr(self, 'pdf_extractor') and self.pdf_extractor:
                    logger.info(f"Extracting PDF objects for {attachment.FileName}")
                    extraction_result = self.pdf_extractor.extract_objects_from_file_path(storage_result['file_path'])
                    
                    if extraction_result['success']:
                        import json
                        objects_json = json.dumps(extraction_result['objects'], default=str)
                        
                        # Update PDF record with extracted objects
                        self.db_service.update_pdf_file_objects(pdf_record.id, objects_json, len(extraction_result['objects']))
                        
                        logger.info(f"Extracted and stored {len(extraction_result['objects'])} PDF objects for {attachment.FileName}")
                    else:
                        logger.error(f"PDF object extraction failed for {attachment.FileName}: {extraction_result.get('error', 'Unknown error')}")
                else:
                    logger.warning("PDF extractor not available - PDF objects not extracted during ingestion")
            except Exception as extract_error:
                logger.error(f"Error during PDF object extraction for {attachment.FileName}: {extract_error}")
            
            # Check if this PDF hash already exists in other emails (for reporting purposes)
            is_duplicate = self._check_if_duplicate_pdf_exists(storage_result['sha256_hash'], pdf_record.id)
            
            # Create ETO run for template matching (always create, even for duplicates)
            eto_run_data = {
                "email_id": email_id,
                "pdf_file_id": pdf_record.id,
                "status": "not_started"  # Initial state for new workflow
            }
            
            eto_run = self.db_service.create_eto_run(eto_run_data)
            
            if is_duplicate:
                logger.warning(f"PDF {attachment.FileName} is duplicate (hash: {storage_result['sha256_hash'][:8]}...) but processing anyway")
            
            logger.info(f"Created PDF file record ID: {pdf_record.id} and ETO run ID: {eto_run.id}")
            
            return {
                'success': True,
                'pdf_record_id': pdf_record.id,
                'eto_run_id': eto_run.id,
                'sha256_hash': storage_result['sha256_hash'],
                'deduplication': storage_result.get('deduplication', False)
            }
            
        except Exception as e:
            logger.error(f"Error storing PDF attachment: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _check_if_duplicate_pdf_exists(self, sha256_hash, current_pdf_id):
        """Check if a PDF with this hash already exists in the system (for reporting)"""
        try:
            if not self.db_service:
                return False
            
            session = self.db_service.get_session()
            try:
                from .database import PdfFile
                
                # Look for other PDF files with the same hash (excluding current one)
                existing_pdf = session.query(PdfFile).filter(
                    PdfFile.sha256_hash == sha256_hash,
                    PdfFile.id != current_pdf_id
                ).first()
                
                return existing_pdf is not None
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error checking for duplicate PDF: {e}")
            return False
    
    def _process_missed_emails_since_cursor(self, cursor):
        """Process emails received during downtime with enhanced cursor persistence"""
        try:
            if not self._validate_cursor(cursor):
                logger.warning("Invalid cursor provided - skipping missed email processing")
                return
            
            cursor_date = cursor.last_processed_received_date
            current_time = datetime.now()
            
            # Validate cursor age - if too old, limit the search scope
            from datetime import timedelta
            max_lookback_days = 7  # Don't look back more than 7 days
            oldest_allowed = current_time - timedelta(days=max_lookback_days)
            
            if cursor_date < oldest_allowed:
                logger.warning(f"Cursor date {cursor_date} is older than {max_lookback_days} days, limiting search to {oldest_allowed}")
                cursor_date = oldest_allowed
            
            logger.info(f"Processing missed emails since cursor: {cursor_date}")
            
            # Get emails with enhanced error handling
            try:
                messages = self.inbox.Items
                messages.Sort("[ReceivedTime]", True)  # Sort by received time, newest first
                total_messages = messages.Count
                logger.info(f"Scanning {total_messages} emails in folder for missed emails")
            except Exception as inbox_error:
                logger.error(f"Error accessing inbox for missed emails: {inbox_error}")
                # Try to reconnect and retry once
                try:
                    self._reconnect()
                    messages = self.inbox.Items
                    messages.Sort("[ReceivedTime]", True)
                    total_messages = messages.Count
                    logger.info(f"After reconnection: scanning {total_messages} emails")
                except Exception as retry_error:
                    logger.error(f"Failed to access inbox after reconnection: {retry_error}")
                    return
            
            missed_emails = []
            emails_checked = 0
            processing_errors = 0
            max_errors = 5  # Stop if too many errors
            
            # Limit the number of emails to check to prevent excessive processing
            max_emails_to_check = min(500, total_messages)  # Check at most 500 emails
            
            for message in messages:
                try:
                    emails_checked += 1
                    
                    # Stop if we've checked enough emails
                    if emails_checked > max_emails_to_check:
                        logger.info(f"Reached max emails to check ({max_emails_to_check}), stopping search")
                        break
                    
                    # Stop if too many processing errors
                    if processing_errors >= max_errors:
                        logger.error(f"Too many processing errors ({processing_errors}), stopping missed email processing")
                        break
                    
                    # Safely get message properties
                    try:
                        message_time = getattr(message, 'ReceivedTime', None)
                        message_subject = getattr(message, 'Subject', 'Unknown Subject')
                        message_id = getattr(message, 'EntryID', None)
                        
                        if not message_time or not message_id:
                            logger.debug(f"Skipping email with missing time/ID: '{message_subject}'")
                            continue
                            
                    except Exception as prop_error:
                        logger.warning(f"Error accessing email properties: {prop_error}")
                        processing_errors += 1
                        continue
                    
                    # Convert to naive datetime for comparison
                    cursor_time = cursor_date
                    if hasattr(message_time, 'replace') and message_time.tzinfo is not None:
                        message_time = message_time.replace(tzinfo=None)
                    
                    if hasattr(cursor_time, 'replace') and cursor_time.tzinfo is not None:
                        cursor_time = cursor_time.replace(tzinfo=None)
                    
                    # Add buffer to account for datetime precision differences
                    cursor_time_with_buffer = cursor_time + timedelta(seconds=5)  # Increased buffer
                    
                    # Check if email is newer than cursor
                    if message_time > cursor_time_with_buffer:
                        logger.info(f"Found missed email: '{message_subject}' ({message_time} > {cursor_time_with_buffer})")
                        missed_emails.append(message)
                    else:
                        logger.debug(f"Email is not newer than cursor: '{message_subject}' ({message_time} <= {cursor_time_with_buffer})")
                        # Since emails are sorted by date (newest first), we can break early
                        if emails_checked > 20:  # Check at least 20 emails before breaking
                            logger.debug("Breaking early - found older emails")
                            break
                        
                except Exception as compare_error:
                    processing_errors += 1
                    logger.warning(f"Error processing email during cursor scan: {compare_error}")
                    
                    # When in doubt about timing, include the email to avoid missing it
                    # But only if we haven't seen too many errors
                    if processing_errors < max_errors:
                        try:
                            subject = getattr(message, 'Subject', 'Unknown')
                            logger.info(f"Including email due to comparison error: '{subject}'")
                            missed_emails.append(message)
                        except:
                            pass  # Skip if we can't even get the subject
            
            # Process found missed emails with enhanced error handling
            if missed_emails:
                # Reverse to process oldest first
                missed_emails.reverse()
                logger.info(f"Processing {len(missed_emails)} missed emails found during downtime")
                
                processed_count = 0
                for i, message in enumerate(missed_emails):
                    try:
                        subject = getattr(message, 'Subject', f'Email_{i+1}')
                        logger.info(f"Processing missed email {i+1}/{len(missed_emails)}: '{subject}'")
                        
                        # Check if already processed (additional safety check)
                        entry_id = getattr(message, 'EntryID', None)
                        if entry_id and entry_id in self.processed_emails:
                            logger.debug(f"Email already processed, skipping: '{subject}'")
                            continue
                        
                        # Process the email with error isolation
                        self._process_email(message)
                        processed_count += 1
                        
                        # Add to processed set
                        if entry_id:
                            self.processed_emails.add(entry_id)
                        
                        # Small delay between processing to avoid overwhelming the system
                        if i < len(missed_emails) - 1:  # Don't delay after the last email
                            time.sleep(0.1)
                            
                    except Exception as process_error:
                        logger.error(f"Error processing missed email {i+1}: {process_error}")
                        # Continue processing other emails despite individual failures
                
                logger.info(f"Completed processing missed emails: {processed_count}/{len(missed_emails)} processed successfully")
            else:
                logger.info(f"No missed emails found after checking {emails_checked} emails")
            
            # Update cursor to reflect the completion of missed email processing
            try:
                if self.current_email and self.current_folder:
                    self.db_service.update_email_cursor(
                        self.current_email,
                        self.current_folder,
                        f"missed_email_scan_{int(time.time())}",
                        current_time
                    )
                    logger.debug("Updated cursor after missed email processing")
            except Exception as cursor_update_error:
                logger.error(f"Error updating cursor after missed email processing: {cursor_update_error}")
                
        except Exception as e:
            logger.error(f"Critical error in missed email processing: {e}")
    
    def _validate_cursor(self, cursor) -> bool:
        """Validate cursor object and its data"""
        try:
            if not cursor:
                logger.debug("Cursor is None")
                return False
            
            if not hasattr(cursor, 'last_processed_received_date'):
                logger.debug("Cursor missing last_processed_received_date attribute")
                return False
            
            if not cursor.last_processed_received_date:
                logger.debug("Cursor has no last_processed_received_date")
                return False
            
            # Validate that cursor date is reasonable (not in the future, not too old)
            cursor_date = cursor.last_processed_received_date
            current_time = datetime.now()
            
            # Convert to naive datetime for comparison
            if hasattr(cursor_date, 'replace') and cursor_date.tzinfo is not None:
                cursor_date = cursor_date.replace(tzinfo=None)
            
            # Check if cursor is in the future (shouldn't happen)
            if cursor_date > current_time:
                logger.warning(f"Cursor date is in the future: {cursor_date} > {current_time}")
                return False
            
            # Check if cursor is too old (more than 30 days)
            from datetime import timedelta
            max_age = timedelta(days=30)
            if current_time - cursor_date > max_age:
                logger.warning(f"Cursor is very old ({current_time - cursor_date}), but will process with limited scope")
                # Still return True but log the warning
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating cursor: {e}")
            return False
    
    def get_recent_emails(self, limit: int = 10) -> List[Dict]:
        """Get recent emails for testing"""
        try:
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            
            if not self.current_email:
                return []
            
            # Ensure we have a valid connection
            if not self.inbox:
                self._reconnect()
            
            messages = self.inbox.Items
            messages.Sort("[ReceivedTime]", True)
            
            recent_emails = []
            count = 0
            
            for message in messages:
                if count >= limit:
                    break
                
                email_info = {
                    "subject": message.Subject,
                    "sender": message.SenderEmailAddress,
                    "received_time": message.ReceivedTime.isoformat() if message.ReceivedTime else None,
                    "has_pdf": self._has_pdf_attachments(message),
                    "processed": message.EntryID in self.processed_emails
                }
                recent_emails.append(email_info)
                count += 1
            
            return recent_emails
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []
    
    def is_healthy(self) -> bool:
        """
        Health check method for service monitoring
        Returns True if the service is functioning properly
        """
        try:
            # Check basic connection health
            if not self.current_email or not self.outlook or not self.inbox:
                logger.debug("Health check failed: not connected")
                return False
            
            # Test COM connection by accessing inbox count
            try:
                inbox_count = self.inbox.Items.Count
                logger.debug(f"Health check passed: inbox accessible with {inbox_count} items")
            except Exception as com_error:
                logger.warning(f"Health check failed: COM error accessing inbox: {com_error}")
                return False
            
            # Check if monitoring is working as expected
            if self.monitoring:
                # For event-based monitoring, check if event handler exists
                if not self.fallback_to_polling and not self.event_handler:
                    logger.warning("Health check failed: event monitoring enabled but no event handler")
                    return False
                
                # For polling, check if thread is alive
                if self.fallback_to_polling:
                    if not self.monitor_thread or not self.monitor_thread.is_alive():
                        logger.warning("Health check failed: polling monitoring enabled but thread not running")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed with exception: {e}")
            return False
    
    def restart_service(self) -> bool:
        """
        Restart method for service monitoring
        Returns True if restart was successful
        """
        try:
            logger.info("Attempting to restart Outlook service")
            
            # Store connection details
            email = self.current_email
            folder = self.current_folder
            
            if not email:
                logger.error("Cannot restart: no email address stored")
                return False
            
            # Disconnect cleanly
            disconnect_result = self.disconnect()
            if disconnect_result.get('status') not in ['disconnected', 'error']:
                logger.warning(f"Disconnect returned unexpected status: {disconnect_result}")
            
            # Wait a moment for cleanup
            time.sleep(2)
            
            # Reconnect
            try:
                if email.endswith('@') or '@' not in email:
                    # Use default connection if email format is invalid
                    connect_result = self.connect_default(folder)
                else:
                    connect_result = self.connect(email, folder)
                
                if connect_result.get('status') != 'connected':
                    logger.error(f"Restart failed: reconnection failed with status {connect_result}")
                    return False
                
                # Restart monitoring if it was previously active
                monitor_result = self.start_monitoring()
                if 'error' in monitor_result.get('status', ''):
                    logger.error(f"Restart failed: monitoring restart failed: {monitor_result}")
                    return False
                
                logger.info("Outlook service restart completed successfully")
                return True
                
            except Exception as connect_error:
                logger.error(f"Restart failed during reconnection: {connect_error}")
                return False
            
        except Exception as e:
            logger.error(f"Restart failed with exception: {e}")
            return False

# Global instance
outlook_service = OutlookService()