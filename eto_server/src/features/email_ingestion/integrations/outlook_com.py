"""
Outlook COM Integration
Implementation of email integration for local Outlook using COM interface
"""
import logging
import threading
import tempfile
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import win32com.client
import pythoncom

from shared.models.email_integration import (
    EmailMessage,
    EmailAttachment,
    EmailFolder,
    EmailAccount,
    OutlookComConfig,
    ConnectionTestResult
)
from .base_integration import BaseEmailIntegration

logger = logging.getLogger(__name__)


class OutlookComIntegration(BaseEmailIntegration):
    """
    Outlook COM implementation of email integration.
    Uses Windows COM interface to interact with locally installed Outlook.
    """
    
    def __init__(self, config: OutlookComConfig):
        """
        Initialize Outlook COM integration
        
        Args:
            config: OutlookComConfig with connection settings
        """
        super().__init__(config)
        # Store config with proper type
        self.config: OutlookComConfig = config
        
        # COM objects
        self.outlook: Optional[Any] = None
        self.namespace: Optional[Any] = None
        self.current_account: Optional[Any] = None
        self.current_folder: Optional[Any] = None
        
        # State management
        self.connection_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Outlook folder constants for standard folders
        self.folder_mapping = {
            'Inbox': 6, 'Outbox': 4, 'Sent': 5, 'SentMail': 5,
            'Drafts': 16, 'DeletedItems': 3, 'Trash': 3,
            'Junk': 23, 'JunkEmail': 23, 'Calendar': 9,
            'Contacts': 10, 'Tasks': 13, 'Notes': 12, 'Journal': 11
        }
    
    # ========== Connection Management ==========
    
    def connect(self, account_identifier: Optional[str] = None) -> bool:
        """
        Connect to Outlook using COM interface
        
        Args:
            account_identifier: Email address of account to connect to (optional)
            
        Returns:
            True if connection successful
        """
        try:
            with self._lock:
                # Use account from config if not provided
                if not account_identifier:
                    account_identifier = self.config.account_identifier
                
                self.logger.debug(f"Connecting to Outlook - Account: {account_identifier or 'Default'}")
                
                # Initialize COM
                pythoncom.CoInitialize()
                
                # Create Outlook application
                self.outlook = win32com.client.Dispatch("Outlook.Application")
                self.namespace = self.outlook.GetNamespace("MAPI")
                assert self.namespace is not None
                
                # Select account if specified
                if account_identifier:
                    account_found = False
                    for account in self.namespace.Accounts:
                        if account.SmtpAddress.lower() == account_identifier.lower():
                            self.current_account = account
                            account_found = True
                            self.logger.debug(f"Selected account: {account.SmtpAddress}")
                            break
                    
                    if not account_found:
                        raise ConnectionError(f"Email account {account_identifier} not found in Outlook")
                else:
                    # Use default account
                    if self.namespace.Accounts.Count > 0:
                        self.current_account = self.namespace.Accounts.Item(1)
                        assert self.current_account is not None
                        self.logger.debug(f"Using default account: {self.current_account.SmtpAddress}")
                    else:
                        raise ConnectionError("No Outlook accounts configured")
                
                # Select default folder
                self.current_folder = self._get_folder_by_name(self.config.default_folder)
                if not self.current_folder:
                    raise ConnectionError(f"Folder '{self.config.default_folder}' not found")
                
                # Test folder access
                try:
                    folder_count = self.current_folder.Items.Count
                    self.logger.debug(f"Folder '{self.config.default_folder}' has {folder_count} items")
                except Exception as e:
                    raise ConnectionError(f"Cannot access folder '{self.config.default_folder}': {e}")
                
                self.is_connected = True
                self.connection_time = datetime.now(timezone.utc)
                self.last_error = None
                
                self.logger.info("Successfully connected to Outlook")
                return True
                
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Error connecting to Outlook: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Outlook and cleanup COM objects"""
        try:
            with self._lock:
                if not self.is_connected:
                    return
                
                try:
                    # Release COM objects
                    self.current_folder = None
                    self.current_account = None
                    self.namespace = None
                    
                    if self.outlook:
                        try:
                            # Don't quit Outlook as user might be using it
                            pass
                        except:
                            pass
                        self.outlook = None
                    
                    pythoncom.CoUninitialize()
                    
                finally:
                    self.is_connected = False
                    self.connection_time = None
                
                self.logger.info("Disconnected from Outlook")
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from Outlook: {e}")
    
    def test_connection(self) -> ConnectionTestResult:
        """Test current connection or validate configuration"""
        try:
            # If already connected, test the existing connection
            if self.is_connected and self.current_folder:
                try:
                    item_count = self.current_folder.Items.Count
                    return ConnectionTestResult(
                        success=True,
                        message="Connection is active",
                        details={
                            "email_address": self.current_account.SmtpAddress if self.current_account else None,
                            "folder_name": self.config.default_folder,
                            "item_count": item_count
                        }
                    )
                except Exception as e:
                    return ConnectionTestResult(
                        success=False,
                        message="Connection lost",
                        error=str(e)
                    )
            
            # Test new connection without persisting
            test_result = self._test_connection_internal()
            return test_result
            
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message="Connection test failed",
                error=str(e)
            )
    
    # ========== Account Discovery ==========
    
    def discover_accounts(self) -> List[EmailAccount]:
        """Discover all available Outlook accounts"""
        accounts = []
        
        try:
            # Ensure we have namespace
            if not self.namespace:
                if not self.is_connected:
                    pythoncom.CoInitialize()
                    outlook = win32com.client.Dispatch("Outlook.Application")
                    namespace = outlook.GetNamespace("MAPI")
                else:
                    namespace = self.namespace
            else:
                namespace = self.namespace
            assert namespace is not None
            for i, account in enumerate(namespace.Accounts):
                try:
                    accounts.append(EmailAccount(
                        email_address=account.SmtpAddress,
                        display_name=account.DisplayName,
                        account_type=str(account.AccountType),
                        is_default=(i == 0),
                        provider_specific_id=None
                    ))
                except Exception as e:
                    self.logger.debug(f"Error accessing account {i}: {e}")
                    continue
            
            self.logger.info(f"Discovered {len(accounts)} Outlook accounts")
            
        except Exception as e:
            self.logger.error(f"Error discovering accounts: {e}")
        
        return accounts
    
    # ========== Folder Operations ==========
    
    def discover_folders(self, account_identifier: Optional[str] = None) -> List[EmailFolder]:
        """Discover all folders for the specified or current account"""
        folders = []
        
        try:
            # Use current connection or create temporary one
            if self.is_connected and self.namespace:
                namespace = self.namespace
                target_account = self.current_account
            else:
                pythoncom.CoInitialize()
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                # Find target account
                target_account = None
                if account_identifier:
                    for account in namespace.Accounts:
                        if account.SmtpAddress.lower() == account_identifier.lower():
                            target_account = account
                            break
                
                if not target_account and namespace.Accounts.Count > 0:
                    target_account = namespace.Accounts.Item(1)
            
            if not target_account:
                raise Exception("No Outlook account available")
            
            # Get root folder and discover recursively
            root_folder = target_account.DeliveryStore.GetRootFolder()
            self._discover_folders_recursive(root_folder, folders, max_depth=3)
            
            self.logger.info(f"Discovered {len(folders)} folders")
            
        except Exception as e:
            self.logger.error(f"Error discovering folders: {e}")
        
        return folders
    
    def select_folder(self, folder_name: str) -> bool:
        """Select a specific folder for operations"""
        try:
            if not self.is_connected:
                return False
            
            folder = self._get_folder_by_name(folder_name)
            if folder:
                self.current_folder = folder
                self.logger.debug(f"Selected folder: {folder_name}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error selecting folder {folder_name}: {e}")
            return False
    
    # ========== Email Retrieval ==========
    
    def get_recent_emails(self, 
                         folder_name: str = "Inbox",
                         since_datetime: Optional[datetime] = None,
                         limit: int = 100,
                         include_read: bool = True) -> List[EmailMessage]:
        """Get recent emails from specified folder"""
        emails = []
        
        try:
            if not self.is_connected:
                raise Exception("Not connected to Outlook")
            
            # Get or select folder
            if folder_name != self.config.default_folder or not self.current_folder:
                if not self.select_folder(folder_name):
                    raise Exception(f"Cannot access folder: {folder_name}")
            
            # Thread-safe COM access
            pythoncom.CoInitialize()
            
            try:
                # Create fresh COM reference for this thread
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                # Find the folder
                folder = self._get_folder_by_name_threadsafe(namespace, folder_name)
                if not folder:
                    raise Exception(f"Folder '{folder_name}' not found")
                
                # Get and sort items
                items = folder.Items
                items.Sort("[ReceivedTime]", True)  # Descending
                
                # Apply date filter if provided
                if since_datetime:
                    # Convert to local time for Outlook
                    if since_datetime.tzinfo is None:
                        since_datetime = since_datetime.replace(tzinfo=timezone.utc)
                    local_time = since_datetime.astimezone()
                    date_filter = f"[ReceivedTime] > '{local_time.strftime('%m/%d/%Y %H:%M')}'"
                    items = items.Restrict(date_filter)
                
                # Apply read filter if needed
                if not include_read:
                    items = items.Restrict("[UnRead] = True")
                
                # Convert to EmailMessage models
                count = 0
                for mail_item in items:
                    if count >= limit:
                        break
                    
                    try:
                        email_msg = self._convert_to_email_message(mail_item, folder_name)
                        emails.append(email_msg)
                        count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to convert email: {e}")
                        continue
                
                self.logger.debug(f"Retrieved {len(emails)} emails from {folder_name}")
                
            finally:
                pythoncom.CoUninitialize()
            
        except Exception as e:
            self.logger.error(f"Error getting recent emails: {e}")
            raise
        
        return emails
    
    def get_email_by_id(self, message_id: str, folder_name: str = "Inbox") -> Optional[EmailMessage]:
        """Get specific email by message ID"""
        try:
            if not self.is_connected:
                return None
            
            pythoncom.CoInitialize()
            
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                folder = self._get_folder_by_name_threadsafe(namespace, folder_name)
                if not folder:
                    return None
                
                # Search for the specific message
                for mail_item in folder.Items:
                    if mail_item.EntryID == message_id:
                        return self._convert_to_email_message(mail_item, folder_name)
                
                return None
                
            finally:
                pythoncom.CoUninitialize()
                
        except Exception as e:
            self.logger.error(f"Error getting email by ID: {e}")
            return None
    
    # ========== Attachment Operations ==========
    
    def get_attachments(self, message_id: str, folder_name: str = "Inbox") -> List[EmailAttachment]:
        """Get all attachments from a specific email"""
        attachments = []
        
        try:
            if not self.is_connected:
                return attachments
            
            pythoncom.CoInitialize()
            
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                folder = self._get_folder_by_name_threadsafe(namespace, folder_name)
                if not folder:
                    return attachments
                
                # Find the email
                mail_item = None
                for item in folder.Items:
                    if item.EntryID == message_id:
                        mail_item = item
                        break
                
                if not mail_item or not hasattr(mail_item, 'Attachments'):
                    return attachments
                
                # Extract attachments
                for attachment in mail_item.Attachments:
                    try:
                        att_model = self._extract_attachment(attachment)
                        if att_model:
                            attachments.append(att_model)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract attachment: {e}")
                        continue
                
            finally:
                pythoncom.CoUninitialize()
                
        except Exception as e:
            self.logger.error(f"Error getting attachments: {e}")
        
        return attachments
    
    # ========== Email State Management ==========
    
    def mark_as_read(self, message_id: str, folder_name: str = "Inbox") -> bool:
        """Mark email as read"""
        try:
            if not self.is_connected:
                return False
            
            pythoncom.CoInitialize()
            
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                folder = self._get_folder_by_name_threadsafe(namespace, folder_name)
                if not folder:
                    return False
                
                # Find and mark the email
                for mail_item in folder.Items:
                    if mail_item.EntryID == message_id:
                        mail_item.UnRead = False
                        mail_item.Save()
                        self.logger.debug(f"Marked email {message_id} as read")
                        return True
                
                return False
                
            finally:
                pythoncom.CoUninitialize()
                
        except Exception as e:
            self.logger.error(f"Error marking email as read: {e}")
            return False
    
    # ========== Internal Helper Methods ==========
    
    def _test_connection_internal(self) -> ConnectionTestResult:
        """Test connection without persisting state"""
        test_outlook = None
        test_namespace = None
        
        try:
            pythoncom.CoInitialize()
            
            try:
                test_outlook = win32com.client.Dispatch("Outlook.Application")
                test_namespace = test_outlook.GetNamespace("MAPI")
                
                # Test account access
                account_identifier = self.config.account_identifier
                test_account = None
                
                if account_identifier:
                    for account in test_namespace.Accounts:
                        if account.SmtpAddress.lower() == account_identifier.lower():
                            test_account = account
                            break
                    
                    if not test_account:
                        return ConnectionTestResult(
                            success=False,
                            message=f"Account {account_identifier} not found",
                            error="Specified email account not found in Outlook"
                        )
                else:
                    if test_namespace.Accounts.Count > 0:
                        test_account = test_namespace.Accounts.Item(1)
                
                # Test folder access
                test_folder = self._get_folder_by_name_test(test_namespace, self.config.default_folder)
                if not test_folder:
                    return ConnectionTestResult(
                        success=False,
                        message=f"Folder '{self.config.default_folder}' not accessible",
                        error=f"Cannot find folder: {self.config.default_folder}"
                    )
                
                folder_count = test_folder.Items.Count
                
                return ConnectionTestResult(
                    success=True,
                    message="Connection test successful",
                    details={
                        "email_address": test_account.SmtpAddress if test_account else None,
                        "folder_name": self.config.default_folder,
                        "email_count": folder_count
                    }
                )
                
            finally:
                pythoncom.CoUninitialize()
                
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message="Connection test failed",
                error=str(e)
            )
    
    def _get_folder_by_name(self, folder_name: str) -> Optional[Any]:
        """Get folder by name from current namespace"""
        if not self.namespace:
            return None
        
        # Try standard folder mapping first
        if folder_name in self.folder_mapping:
            try:
                return self.namespace.GetDefaultFolder(self.folder_mapping[folder_name])
            except:
                pass
        
        # Search through account folders
        if self.current_account:
            try:
                root_folder = self.current_account.DeliveryStore.GetRootFolder()
                return self._search_folder_recursive(root_folder, folder_name)
            except:
                pass
        
        return None
    
    def _get_folder_by_name_threadsafe(self, namespace: Any, folder_name: str) -> Optional[Any]:
        """Get folder by name for thread-safe operations"""
        # Try standard folders
        if folder_name in self.folder_mapping:
            try:
                return namespace.GetDefaultFolder(self.folder_mapping[folder_name])
            except:
                pass
        
        # Search all accounts
        for account in namespace.Accounts:
            try:
                root_folder = account.DeliveryStore.GetRootFolder()
                folder = self._search_folder_recursive(root_folder, folder_name)
                if folder:
                    return folder
            except:
                continue
        
        return None
    
    def _get_folder_by_name_test(self, namespace: Any, folder_name: str) -> Optional[Any]:
        """Get folder for testing (doesn't use self.namespace)"""
        if folder_name in self.folder_mapping:
            try:
                return namespace.GetDefaultFolder(self.folder_mapping[folder_name])
            except:
                pass
        
        # Try finding in first account
        if namespace.Accounts.Count > 0:
            try:
                account = namespace.Accounts.Item(1)
                root_folder = account.DeliveryStore.GetRootFolder()
                return self._search_folder_recursive(root_folder, folder_name, max_depth=2)
            except:
                pass
        
        return None
    
    def _search_folder_recursive(self, parent_folder: Any, target_name: str, 
                                max_depth: int = 3, current_depth: int = 0) -> Optional[Any]:
        """Recursively search for folder by name"""
        if current_depth >= max_depth:
            return None
        
        try:
            for folder in parent_folder.Folders:
                try:
                    if folder.Name.lower() == target_name.lower():
                        return folder
                    
                    if hasattr(folder, 'Folders') and folder.Folders.Count > 0:
                        result = self._search_folder_recursive(
                            folder, target_name, max_depth, current_depth + 1
                        )
                        if result:
                            return result
                            
                except Exception as e:
                    self.logger.debug(f"Error accessing folder: {e}")
                    continue
        except Exception as e:
            self.logger.debug(f"Error enumerating folders: {e}")
        
        return None
    
    def _discover_folders_recursive(self, parent_folder: Any, folder_list: List[EmailFolder],
                                   current_depth: int = 0, max_depth: int = 3,
                                   parent_path: str = ""):
        """Recursively discover folders and add to list"""
        if current_depth >= max_depth:
            return
        
        try:
            for folder in parent_folder.Folders:
                try:
                    folder_name = folder.Name
                    folder_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
                    
                    # Determine folder type
                    folder_type = None
                    if folder_name.lower() in ['inbox', 'sent items', 'drafts', 'deleted items', 'outbox']:
                        folder_type = folder_name.lower().replace(' ', '_')
                    
                    folder_list.append(EmailFolder(
                        name=folder_name,
                        full_path=folder_path,
                        message_count=folder.Items.Count if hasattr(folder, 'Items') else 0,
                        unread_count=0,  # Would need to iterate items to count
                        folder_type=folder_type,
                        parent_folder=parent_path if parent_path else None
                    ))
                    
                    # Recurse into subfolders
                    if hasattr(folder, 'Folders') and folder.Folders.Count > 0:
                        self._discover_folders_recursive(
                            folder, folder_list, current_depth + 1, max_depth, folder_path
                        )
                        
                except Exception as e:
                    self.logger.debug(f"Error processing folder: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Error iterating folders: {e}")
    
    def _convert_to_email_message(self, outlook_mail: Any, folder_name: str) -> EmailMessage:
        """Convert Outlook mail item to EmailMessage model"""
        try:
            # Extract basic properties
            message_id = outlook_mail.EntryID or ""
            subject = outlook_mail.Subject or ""
            sender_email = outlook_mail.SenderEmailAddress or ""
            sender_name = outlook_mail.SenderName or ""
            
            # Handle recipients
            recipient_emails = []
            try:
                for recipient in outlook_mail.Recipients:
                    recipient_emails.append(recipient.Address)
            except:
                pass
            
            # Convert received time to UTC
            received_time = self._convert_outlook_time_to_utc(outlook_mail.ReceivedTime)
            
            # Body content
            body_text = outlook_mail.Body if hasattr(outlook_mail, 'Body') else None
            body_html = outlook_mail.HTMLBody if hasattr(outlook_mail, 'HTMLBody') else None
            body_preview = body_text[:500] if body_text else None
            
            # Attachment info
            has_attachments = outlook_mail.Attachments.Count > 0
            attachment_count = outlook_mail.Attachments.Count
            attachment_filenames = []
            
            if has_attachments:
                for attachment in outlook_mail.Attachments:
                    try:
                        attachment_filenames.append(attachment.FileName)
                    except:
                        continue
            
            # Read status and importance
            is_read = not outlook_mail.UnRead if hasattr(outlook_mail, 'UnRead') else True
            importance = "normal"
            if hasattr(outlook_mail, 'Importance'):
                if outlook_mail.Importance == 2:
                    importance = "high"
                elif outlook_mail.Importance == 0:
                    importance = "low"
            
            return EmailMessage(
                message_id=message_id,
                subject=subject,
                sender_email=sender_email,
                sender_name=sender_name,
                recipient_emails=recipient_emails,
                received_date=received_time,
                folder_name=folder_name,
                body_text=body_text,
                body_html=body_html,
                body_preview=body_preview,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
                attachment_filenames=attachment_filenames,
                size_bytes=outlook_mail.Size if hasattr(outlook_mail, 'Size') else 0,
                is_read=is_read,
                importance=importance
            )
            
        except Exception as e:
            self.logger.error(f"Error converting email: {e}")
            raise
    
    def _convert_outlook_time_to_utc(self, outlook_time: Any) -> datetime:
        """Convert Outlook time to UTC datetime"""
        try:
            # Outlook returns local time but sometimes marks it as UTC
            if hasattr(outlook_time, 'tzinfo') and outlook_time.tzinfo is not None:
                # Strip incorrect timezone and treat as local
                local_time = datetime(
                    outlook_time.year, outlook_time.month, outlook_time.day,
                    outlook_time.hour, outlook_time.minute, outlook_time.second,
                    outlook_time.microsecond
                )
            else:
                local_time = outlook_time
            
            # Convert local to UTC
            local_timestamp = local_time.timestamp()
            utc_time = datetime.utcfromtimestamp(local_timestamp)
            
            # Return timezone-aware UTC
            return utc_time.replace(tzinfo=timezone.utc)
            
        except Exception as e:
            self.logger.warning(f"Error converting time, using as-is: {e}")
            if isinstance(outlook_time, datetime):
                return outlook_time
            return datetime.now(timezone.utc)
    
    def _extract_attachment(self, attachment: Any) -> Optional[EmailAttachment]:
        """Extract attachment and convert to EmailAttachment model"""
        temp_path = None
        
        try:
            filename = attachment.FileName
            size = attachment.Size if hasattr(attachment, 'Size') else 0
            
            # Determine content type
            content_type = "application/octet-stream"
            if filename.lower().endswith('.pdf'):
                content_type = "application/pdf"
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif filename.lower().endswith('.png'):
                content_type = "image/png"
            elif filename.lower().endswith(('.doc', '.docx')):
                content_type = "application/msword"
            
            # Extract content using temp file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            
            attachment.SaveAsFile(temp_path)
            
            with open(temp_path, 'rb') as f:
                content = f.read()
            
            return EmailAttachment(
                filename=filename,
                content_type=content_type,
                size_bytes=size,
                content=content,
                content_id=None,
                is_inline=False
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting attachment: {e}")
            return None
            
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass