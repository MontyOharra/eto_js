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
                self.outlook = None
                self.namespace = None
                self.inbox = None
                self.current_email = None
                self.current_folder = None
                self.processed_emails.clear()
                self.last_poll_time = None
                
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
                "processed_count": len(self.processed_emails),
                "inbox_count": inbox_count,
                "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _reconnect(self):
        """Reconnect to Outlook using stored email and folder"""
        if not self.current_email:
            raise Exception("No email address stored for reconnection")
        
        folder_name = self.current_folder or 'Inbox'
        logger.info(f"Reconnecting to Outlook for: {self.current_email}, folder: {folder_name}")
        
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        # Re-initialize COM objects
        self.outlook = win32com.client.Dispatch("Outlook.Application")
        self.namespace = self.outlook.GetNamespace("MAPI")
        
        # Get the account (try specific first, fallback to default)
        try:
            account = self.namespace.Accounts.Item(self.current_email)
        except Exception as account_error:
            logger.warning(f"Could not find account {self.current_email}, using default: {account_error}")
            account = self.namespace.Accounts.Item(1)
        
        # Get the specified folder
        self.inbox = self._get_folder(account, folder_name)
        logger.info(f"Reconnected successfully to {account.DisplayName} {folder_name}")
    
    def start_monitoring(self) -> Dict[str, str]:
        """Start monitoring the inbox for new emails"""
        try:
            with self._lock:
                if not self.outlook or not self.inbox:
                    raise Exception("Not connected to Outlook")
                
                if self.monitoring:
                    return {"status": "already_monitoring"}
                
                self.monitoring = True
                self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()
                
            logger.info("Started monitoring Outlook inbox")
            return {"status": "monitoring_started"}
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return {"status": "error", "message": str(e)}
    
    def stop_monitoring(self) -> Dict[str, str]:
        """Stop monitoring the inbox"""
        try:
            with self._lock:
                if not self.monitoring:
                    return {"status": "not_monitoring"}
                
                self.monitoring = False
                monitor_thread = self.monitor_thread
                
            # Wait for the monitoring thread to finish outside the lock
            if monitor_thread and monitor_thread.is_alive():
                logger.info("Waiting for monitoring thread to stop...")
                monitor_thread.join(timeout=10)  # Wait up to 10 seconds
                
                if monitor_thread.is_alive():
                    logger.warning("Monitoring thread did not stop within timeout")
                else:
                    logger.info("Monitoring thread stopped successfully")
            
            with self._lock:
                self.monitor_thread = None
                
            logger.info("Stopped monitoring Outlook inbox")
            return {"status": "monitoring_stopped"}
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return {"status": "error", "message": str(e)}
    
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
    
    def _process_email(self, message):
        """Process email with PDF attachments and store in database"""
        try:
            if not self.db_service or not self.pdf_storage:
                logger.error("Database service or PDF storage not configured")
                return
            
            # Count PDF attachments
            pdf_attachments = [att for att in message.Attachments if att.FileName.lower().endswith('.pdf')]
            
            if not pdf_attachments:
                logger.info(f"Email '{message.Subject}' has no PDF attachments, skipping")
                return
            
            # Create email record in database
            email_data = {
                "message_id": message.EntryID,
                "subject": message.Subject,
                "sender_email": message.SenderEmailAddress,
                "sender_name": getattr(message, 'SenderName', None),
                "received_date": message.ReceivedTime,
                "folder_name": self.current_folder,
                "has_pdf_attachments": True,
                "attachment_count": len(pdf_attachments)
            }
            
            email_record = self.db_service.create_email_record(email_data)
            logger.info(f"Created email record ID: {email_record.id} for '{message.Subject}'")
            
            # Process each PDF attachment
            processed_pdfs = 0
            for attachment in pdf_attachments:
                try:
                    pdf_result = self._store_pdf_attachment(attachment, email_record.id)
                    if pdf_result['success']:
                        processed_pdfs += 1
                        logger.info(f"Processed PDF: {attachment.FileName} -> {pdf_result['sha256_hash']}")
                except Exception as pdf_error:
                    logger.error(f"Error processing PDF attachment {attachment.FileName}: {pdf_error}")
            
            logger.info(f"Successfully processed email '{message.Subject}' with {processed_pdfs}/{len(pdf_attachments)} PDFs")
            
            # Update email cursor with this processed email
            if self.current_email and self.current_folder:
                try:
                    # Convert received time to naive datetime for storage
                    received_time = message.ReceivedTime
                    if hasattr(received_time, 'replace') and received_time.tzinfo is not None:
                        received_time = received_time.replace(tzinfo=None)
                    
                    self.db_service.update_email_cursor(
                        self.current_email, 
                        self.current_folder,
                        message.EntryID,
                        received_time
                    )
                    if processed_pdfs > 0:
                        # Update PDF count in cursor
                        for _ in range(processed_pdfs):
                            self.db_service.increment_cursor_pdf_count(self.current_email, self.current_folder)
                except Exception as cursor_error:
                    logger.error(f"Error updating email cursor: {cursor_error}")
            
        except Exception as e:
            logger.error(f"Error processing email '{message.Subject}': {e}")
    
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
            
            # Check if this PDF hash already exists in other emails (for reporting purposes)
            is_duplicate = self._check_if_duplicate_pdf_exists(storage_result['sha256_hash'], pdf_record.id)
            
            # Create ETO run for template matching (always create, even for duplicates)
            eto_run_data = {
                "email_id": email_id,
                "pdf_file_id": pdf_record.id,
                "run_type": "template_match",
                "status": "pending",
                "is_duplicate_pdf": is_duplicate,
                "duplicate_handling_result": "flagged_duplicate" if is_duplicate else "processed_as_new"
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
        """Process emails received during downtime"""
        try:
            if not cursor.last_processed_received_date:
                logger.info("No previous cursor date - skipping missed email processing")
                return
            
            cursor_date = cursor.last_processed_received_date
            logger.info(f"Checking for emails received after cursor: {cursor_date}")
            
            # Get emails received after the cursor date
            messages = self.inbox.Items
            messages.Sort("[ReceivedTime]", True)  # Sort by received time, newest first
            logger.info(f"Total emails in folder: {messages.Count}")
            
            missed_emails = []
            emails_checked = 0
            
            for message in messages:
                try:
                    emails_checked += 1
                    message_time = message.ReceivedTime
                    cursor_time = cursor_date
                    
                    # Convert both to naive datetime for comparison
                    if hasattr(message_time, 'replace') and message_time.tzinfo is not None:
                        message_time = message_time.replace(tzinfo=None)
                    
                    if hasattr(cursor_time, 'replace') and cursor_time.tzinfo is not None:
                        cursor_time = cursor_time.replace(tzinfo=None)
                    
                    # Debug logging for each email comparison
                    logger.debug(f"Email '{message.Subject}': received {message_time} vs cursor {cursor_time}")
                    
                    # Add a small buffer (1 second) to account for datetime precision differences
                    from datetime import timedelta
                    cursor_time_with_buffer = cursor_time + timedelta(seconds=1)
                    
                    # Use > with buffer to avoid reprocessing the last processed email due to precision issues
                    if message_time > cursor_time_with_buffer:
                        logger.info(f"Found missed email: '{message.Subject}' ({message_time} > {cursor_time_with_buffer})")
                        missed_emails.append(message)
                    else:
                        logger.debug(f"Skipping older/same email: '{message.Subject}' ({message_time} <= {cursor_time_with_buffer})")
                        # Since we're sorted by date (newest first), we can break early
                        if emails_checked > 10:  # Only break after checking at least 10 emails to be safe
                            break
                        
                except Exception as compare_error:
                    logger.warning(f"Error comparing email time for '{message.Subject}': {compare_error}")
                    # When in doubt, include the email to avoid missing it
                    missed_emails.append(message)
            
            if missed_emails:
                # Reverse to process oldest first
                missed_emails.reverse()
                logger.info(f"Found {len(missed_emails)} emails received during downtime")
                
                for message in missed_emails:
                    logger.info(f"Processing missed email: '{message.Subject}' received at {message.ReceivedTime}")
                    self._process_email(message)
                    # Add to processed set to prevent duplicate processing in real-time monitoring
                    self.processed_emails.add(message.EntryID)
                    
                logger.info(f"Finished processing {len(missed_emails)} missed emails")
            else:
                logger.info("No missed emails found")
                
        except Exception as e:
            logger.error(f"Error processing missed emails: {e}")
    
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

# Global instance
outlook_service = OutlookService() 