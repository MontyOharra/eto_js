"""
Outlook Service for ETO
Handles COM connections to Outlook and email monitoring
"""

import win32com.client
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
        self.processed_emails = set()
        self._lock = threading.Lock()
        
    def connect_default(self) -> Dict[str, Any]:
        """Connect to Outlook using default account"""
        try:
            logger.info("Connecting to Outlook using default account")
            
            # Initialize Outlook COM objects
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            
            # Use default account
            account = self.namespace.Accounts.Item(1)
            
            # Get the inbox for this account
            self.inbox = account.DeliveryStore.GetDefaultFolder(6)  # olFolderInbox
            self.current_email = account.DisplayName
            
            logger.info(f"Successfully connected to Outlook inbox for {account.DisplayName}")
            
            return {
                "status": "connected",
                "email": account.DisplayName,
                "account_name": account.DisplayName,
                "inbox_name": self.inbox.Name,
                "message_count": self.inbox.Items.Count
            }
            
        except Exception as e:
            logger.error(f"Failed to connect to Outlook: {e}")
            self.disconnect()
            raise Exception(f"Outlook connection failed: {str(e)}")
    
    def connect(self, email_address: str) -> Dict[str, Any]:
        """Connect to Outlook and access specific email account"""
        try:
            logger.info(f"Connecting to Outlook for email: {email_address}")
            
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
            
            # Get the inbox for this account
            self.inbox = account.DeliveryStore.GetDefaultFolder(6)  # olFolderInbox
            self.current_email = email_address
            
            logger.info(f"Successfully connected to Outlook inbox for {email_address}")
            
            return {
                "status": "connected",
                "email": email_address,
                "account_name": account.DisplayName,
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
            with self._lock:
                if self.monitoring:
                    self.stop_monitoring()
                
                self.outlook = None
                self.namespace = None
                self.inbox = None
                self.current_email = None
                self.processed_emails.clear()
                
            logger.info("Disconnected from Outlook")
            return {"status": "disconnected"}
            
        except Exception as e:
            logger.error(f"Error disconnecting from Outlook: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        try:
            if not self.outlook or not self.inbox:
                return {
                    "status": "disconnected",
                    "email": None,
                    "monitoring": False
                }
            
            return {
                "status": "connected",
                "email": self.current_email,
                "monitoring": self.monitoring,
                "processed_count": len(self.processed_emails),
                "inbox_count": self.inbox.Items.Count if self.inbox else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
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
                
            logger.info("Stopped monitoring Outlook inbox")
            return {"status": "monitoring_stopped"}
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            return {"status": "error", "message": str(e)}
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        
        while self.monitoring:
            try:
                if self.inbox:
                    self._check_for_new_emails()
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
        
        logger.info("Monitoring loop stopped")
    
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
        """Process email with PDF attachments"""
        try:
            email_data = {
                "subject": message.Subject,
                "sender": message.SenderEmailAddress,
                "received_time": message.ReceivedTime.isoformat() if message.ReceivedTime else None,
                "attachments": []
            }
            
            # Process each PDF attachment
            for attachment in message.Attachments:
                if attachment.FileName.lower().endswith('.pdf'):
                    attachment_data = {
                        "name": attachment.FileName,
                        "size": attachment.Size if hasattr(attachment, 'Size') else 0
                    }
                    email_data["attachments"].append(attachment_data)
            
            logger.info(f"Processed email: {email_data['subject']} with {len(email_data['attachments'])} PDFs")
            
            # Here you would typically save to database or notify other services
            # For now, just log the data
            logger.info(f"Email data: {json.dumps(email_data, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
    
    def get_recent_emails(self, limit: int = 10) -> List[Dict]:
        """Get recent emails for testing"""
        try:
            if not self.inbox:
                return []
            
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