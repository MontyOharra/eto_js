"""
Outlook Reader module for extracting PDF attachments from emails.

This module uses the Windows COM interface to connect to Outlook
and retrieve PDF attachments from specified folders.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Any
from dataclasses import dataclass

try:
    import win32com.client
except ImportError:
    print("Warning: pywin32 not installed. Outlook integration will not work.")
    win32com = None

from loguru import logger

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PDFAttachment:
    """Data class to store PDF attachment information"""

    filename: str
    content: bytes
    sender: str
    subject: str
    received_time: datetime
    size: int



class OutlookReader:
    """Handles reading PDF attachments from Outlook emails."""

    def __init__(self):
        self.outlook_app: Optional[Any] = None
        self.namespace: Optional[Any] = None
        self.temp_files: List[Path] = []  # Track temporary files for cleanup

    def connect(self) -> bool:
        """
        Connect to Outlook application.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if win32com is None:
                raise ImportError("pywin32 library not available")

            self.outlook_app = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook_app.GetNamespace("MAPI")
            logger.info("Connected to Outlook successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Outlook: {e}")
            return False

    def get_folder(self, folder_name: str, subfolder_name: Optional[str] = None):
        """
        Get a specific Outlook folder.

        Args:
            folder_name: Name of the main folder (e.g., "Inbox")
            subfolder_name: Name of the subfolder (optional)

        Returns:
            Outlook folder object or None if not found
        """
        try:
            # Check if namespace is available
            if self.namespace is None:
                logger.error("Outlook namespace not available")
                return None

            # Get the default inbox or specified folder
            if folder_name.lower() == "inbox":
                folder = self.namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
            else:
                # Search for folder by name at top level first
                folder = None
                for f in self.namespace.Folders:
                    if f.Name.lower() == folder_name.lower():
                        folder = f
                        break

                # If not found at top level, search within email account folders
                if folder is None:
                    for account_folder in self.namespace.Folders:
                        try:
                            for subfolder in account_folder.Folders:
                                if subfolder.Name.lower() == folder_name.lower():
                                    folder = subfolder
                                    logger.info(
                                        f"Found folder '{folder_name}' in account '{account_folder.Name}'"
                                    )
                                    break
                            if folder is not None:
                                break
                        except:
                            continue  # Skip if can't access subfolders

                if folder is None:
                    logger.error(f"Folder '{folder_name}' not found")
                    return None

            # Navigate to subfolder if specified
            if subfolder_name:
                for subfolder in folder.Folders:
                    if subfolder.Name.lower() == subfolder_name.lower():
                        folder = subfolder
                        break
                else:
                    logger.error(
                        f"Subfolder '{subfolder_name}' not found in '{folder_name}'"
                    )
                    return None

            logger.info(f"Found folder: {folder.Name}")
            return folder

        except Exception as e:
            logger.error(f"Error accessing folder: {e}")
            return None

    async def get_attachments_in_folder(
        self, folder_name: str, subfolder_name: Optional[str] = None
    ) -> List[PDFAttachment]:
        """
        Retrieve all PDF attachments from the specified Outlook folder.

        Args:
            folder_name: Name of the Outlook folder to search
            subfolder_name: Optional subfolder name to search within

        Returns:
            List of PDFAttachment objects
        """
        if not self.connect():
            return []

        attachments = []

        try:
            # Get the target folder
            folder = self.get_folder(folder_name, subfolder_name)

            if not folder:
                return []

            logger.info(f"Scanning {folder.Items.Count} emails for PDF attachments")

            # Iterate through emails in the folder
            for item in folder.Items:
                try:
                    # Check if email has attachments
                    if hasattr(item, "Attachments") and item.Attachments.Count > 0:
                        attachments.extend(await self._get_attachments_in_email(item))

                except Exception as e:
                    logger.warning(f"Error processing email: {e}")
                    continue

            logger.info(f"Found {len(attachments)} PDF attachments")
            return attachments

        except Exception as e:
            logger.error(f"Error retrieving PDF attachments: {e}")
            return []

    async def _get_attachments_in_email(self, email_item) -> List[PDFAttachment]:
        """
        Gets a list of PDF attachments from a single email.

        Args:
            email_item: Outlook email item

        Returns:
            List of PDFAttachment objects from this email
        """
        attachments = []

        try:
            for attachment in email_item.Attachments:
                # Check if it's a PDF file
                if self._is_pdf_attachment(attachment):
                    pdf_attachment = await self._save_attachment(attachment, email_item)
                    if pdf_attachment:
                        attachments.append(pdf_attachment)

        except Exception as e:
            logger.error(f"Error processing email attachments: {e}")

        return attachments

    def _is_pdf_attachment(self, attachment) -> bool:
        """
        Check if an attachment is a PDF file.

        Args:
            attachment: Outlook attachment object

        Returns:
            bool: True if attachment is a PDF
        """
        try:
            filename = attachment.FileName.lower()

            # Check file extension
            if not any(
                filename.endswith(ext) for ext in outlook_config.ALLOWED_EXTENSIONS
            ):
                return False

            # Check file size
            if attachment.Size > outlook_config.MAX_FILE_SIZE_MB * 1024 * 1024:
                logger.warning(
                    f"PDF file {attachment.FileName} is too large ({attachment.Size} bytes)"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking attachment: {e}")
            return False

    async def _save_attachment(self, attachment, email_item) -> Optional[PDFAttachment]:
        """
        Save an attachment to temporary storage.

        Args:
            attachment: Outlook attachment object
            email_item: Outlook email item

        Returns:
            PDFAttachment object or None if failed
        """
        try:
            # Create a temporary file
            temp_dir = tempfile.gettempdir()
            temp_filename = (
                f"pdf_attachment_{len(self.temp_files)}_{attachment.FileName}"
            )
            temp_path = Path(temp_dir) / temp_filename

            # Save the attachment
            attachment.SaveAsFile(str(temp_path))
            self.temp_files.append(temp_path)

            # Read the file content
            with open(temp_path, "rb") as f:
                content = f.read()

            # Get email received time as datetime
            received_time = getattr(email_item, "ReceivedTime", None)
            if received_time is None:
                from datetime import datetime

                received_time = datetime.now()

            # Create PDFAttachment object
            pdf_attachment = PDFAttachment(
                filename=attachment.FileName,
                content=content,
                sender=getattr(email_item, "SenderEmailAddress", "Unknown"),
                subject=getattr(email_item, "Subject", "No Subject"),
                received_time=received_time,
                size=attachment.Size,
            )

            logger.info(f"Saved PDF attachment: {attachment.FileName}")
            return pdf_attachment

        except Exception as e:
            logger.error(f"Error saving attachment {attachment.FileName}: {e}")
            return None

    async def cleanup(self):
        """Clean up temporary files and close connections."""
        try:
            # Remove temporary files
            for temp_file in self.temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {temp_file}: {e}")

            self.temp_files.clear()

            # Close Outlook connection
            if self.namespace:
                self.namespace = None
            if self.outlook_app:
                self.outlook_app = None

            logger.info("Outlook reader cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
