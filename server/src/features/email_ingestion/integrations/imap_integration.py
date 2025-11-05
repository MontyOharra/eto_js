"""
IMAP Email Integration
Platform-independent IMAP implementation using imaplib
"""
import logging
import imaplib
import ssl
import email
from email.header import decode_header
from typing import Optional
from datetime import datetime, timezone
import re

from shared.types.email_integrations import (
    EmailMessage,
    EmailAttachment,
    EmailFolder,
    ConnectionTestResult,
)
from .base_integration import BaseEmailIntegration
from .registry import IntegrationRegistry

logger = logging.getLogger(__name__)


@IntegrationRegistry.register(
    "imap",
    name="IMAP",
    description="Connect to any email server using IMAP protocol",
    requires_local_install=False,
    platforms=["windows", "linux", "darwin"],
    authentication="Username and password"
)
class ImapIntegration(BaseEmailIntegration):
    """
    IMAP integration for platform-independent email access.
    Self-registers with IntegrationRegistry for automatic discovery.
    """

    def __init__(
        self,
        host: str,
        port: int,
        email_address: str,
        password: str,
        use_ssl: bool = True,
        folder_name: str = "INBOX"
    ):
        """
        Initialize IMAP integration

        Args:
            host: IMAP server hostname (e.g., "mail.example.com")
            port: IMAP server port (usually 993 for SSL, 143 for non-SSL)
            email_address: Email address for login
            password: Email password
            use_ssl: Use SSL/TLS connection (default: True)
            folder_name: Default folder to monitor (default: "INBOX")
        """
        super().__init__(
            host=host,
            port=port,
            email_address=email_address,
            password=password,
            use_ssl=use_ssl,
            folder_name=folder_name
        )

        self.host = host
        self.port = port
        self.email_address = email_address
        self.password = password
        self.use_ssl = use_ssl
        self.folder_name = folder_name

        # IMAP connection
        self.imap: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None
        self.current_folder: Optional[str] = None

        # State management
        self.connection_time: Optional[datetime] = None
        self.last_error: Optional[str] = None

        self.logger.debug(f"Initialized ImapIntegration for {email_address}@{host}:{port}")

    # ========== Connection Management ==========

    def connect(self) -> bool:
        """
        Establish connection to IMAP server using credentials from __init__

        Returns:
            True if connection successful
        """
        try:
            self.logger.debug(f"Connecting to IMAP server {self.host}:{self.port} (SSL: {self.use_ssl})")

            # Create SSL context
            if self.use_ssl:
                context = ssl.create_default_context()
                self.imap = imaplib.IMAP4_SSL(
                    host=self.host,
                    port=self.port,
                    ssl_context=context
                )
            else:
                self.imap = imaplib.IMAP4(
                    host=self.host,
                    port=self.port
                )

            self.logger.debug(f"Logging in as {self.email_address}")

            # Login
            self.imap.login(self.email_address, self.password)

            # Test folder access
            status, message = self.imap.select(self.folder_name, readonly=True)
            if status != 'OK':
                raise ConnectionError(f"Cannot access folder '{self.folder_name}': {message}")

            # Get message count
            message_count = int(message[0].decode()) if message[0] else 0
            self.logger.debug(f"Folder '{self.folder_name}' has {message_count} messages")

            self.is_connected = True
            self.connection_time = datetime.now(timezone.utc)
            self.current_folder = self.folder_name
            self.last_error = None

            self.logger.info(f"Successfully connected to IMAP server {self.host}")
            return True

        except imaplib.IMAP4.error as e:
            self.last_error = str(e)
            self.logger.error(f"IMAP error connecting to {self.host}: {e}")
            self.is_connected = False
            return False

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Error connecting to IMAP server {self.host}: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """Close connection to IMAP server"""
        try:
            if not self.is_connected or not self.imap:
                return

            try:
                self.imap.close()
                self.imap.logout()
            finally:
                self.imap = None
                self.is_connected = False
                self.connection_time = None
                self.current_folder = None

            self.logger.info(f"Disconnected from IMAP server {self.host}")

        except Exception as e:
            self.logger.error(f"Error disconnecting from IMAP server: {e}")

    def test_connection(self) -> ConnectionTestResult:
        """Test if current connection is valid"""
        try:
            # If already connected, test existing connection
            if self.is_connected and self.imap:
                try:
                    status, message = self.imap.noop()
                    if status == 'OK':
                        return ConnectionTestResult(
                            success=True,
                            message="Connection is active",
                            details={
                                "email_address": self.email_address,
                                "host": self.host,
                                "folder": self.current_folder
                            }
                        )
                    else:
                        return ConnectionTestResult(
                            success=False,
                            message="Connection lost",
                            error=f"NOOP failed: {message}"
                        )
                except Exception as e:
                    return ConnectionTestResult(
                        success=False,
                        message="Connection lost",
                        error=str(e)
                    )

            # Test new connection without persisting
            return self._test_connection_internal()

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message="Connection test failed",
                error=str(e)
            )

    def _test_connection_internal(self) -> ConnectionTestResult:
        """Test connection without persisting state"""
        test_imap = None
        try:
            # Create test connection
            if self.use_ssl:
                context = ssl.create_default_context()
                test_imap = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
            else:
                test_imap = imaplib.IMAP4(self.host, self.port)

            # Test login
            test_imap.login(self.email_address, self.password)

            # Test folder access
            status, message = test_imap.select(self.folder_name, readonly=True)
            if status != 'OK':
                return ConnectionTestResult(
                    success=False,
                    message=f"Folder '{self.folder_name}' not accessible",
                    error=f"Cannot access folder: {message}"
                )

            message_count = int(message[0].decode()) if message[0] else 0

            return ConnectionTestResult(
                success=True,
                message="Connection test successful",
                details={
                    "email_address": self.email_address,
                    "host": self.host,
                    "folder": self.folder_name,
                    "message_count": message_count
                }
            )

        except imaplib.IMAP4.error as e:
            return ConnectionTestResult(
                success=False,
                message="IMAP authentication failed",
                error=str(e)
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message="Connection test failed",
                error=str(e)
            )
        finally:
            if test_imap:
                try:
                    test_imap.logout()
                except:
                    pass

    # ========== Folder Operations ==========

    def discover_folders(self) -> list[EmailFolder]:
        """
        Get list of all available folders in the email account.
        Must be connected before calling.
        """
        if not self.is_connected or not self.imap:
            raise RuntimeError("Must call connect() before discover_folders()")

        folders = []

        try:
            self.logger.debug("Discovering IMAP folders")

            # List all folders
            status, folder_list = self.imap.list()

            if status != 'OK':
                raise Exception(f"Failed to list folders: {folder_list}")

            # Parse folder list
            # Format: (flags) "delimiter" "folder_name"
            folder_pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*?)" (?P<name>.*)')

            for folder_line in folder_list:
                if not folder_line:
                    continue

                if isinstance(folder_line, tuple):
                    # Literal response format: (header, data)
                    folder_str = folder_line[1].decode('utf-8')
                else:
                    # Normal response: bytes-like object
                    # Convert to bytes if it's bytearray or memoryview (though list() typically returns bytes)
                    folder_bytes = bytes(folder_line) if not isinstance(folder_line, bytes) else folder_line
                    folder_str = folder_bytes.decode('utf-8')
                    
                match = folder_pattern.match(folder_str)

                if match:
                    flags = match.group('flags')
                    delimiter = match.group('delimiter')
                    name = match.group('name').strip('"')

                    # Determine folder type
                    folder_type = None
                    name_lower = name.lower()
                    if 'inbox' in name_lower:
                        folder_type = 'inbox'
                    elif 'sent' in name_lower:
                        folder_type = 'sent_items'
                    elif 'draft' in name_lower:
                        folder_type = 'drafts'
                    elif 'trash' in name_lower or 'deleted' in name_lower:
                        folder_type = 'deleted_items'
                    elif 'junk' in name_lower or 'spam' in name_lower:
                        folder_type = 'junk'

                    # Get message count for this folder
                    message_count = 0
                    try:
                        status, msg = self.imap.select(name, readonly=True)
                        if status == 'OK' and msg[0]:
                            message_count = int(msg[0].decode())
                    except:
                        pass

                    folders.append(EmailFolder(
                        name=name,
                        full_path=name,
                        message_count=message_count,
                        unread_count=0,  # Would need to count UNSEEN flags
                        folder_type=folder_type,
                        parent_folder=None
                    ))

            self.logger.info(f"Discovered {len(folders)} IMAP folders")

            # Re-select original folder
            if self.current_folder:
                self.imap.select(self.current_folder, readonly=True)

            return folders

        except Exception as e:
            self.logger.error(f"Error discovering folders: {e}", exc_info=True)
            raise

    def select_folder(self, folder_name: str) -> bool:
        """Select a specific folder for operations"""
        if not self.is_connected or not self.imap:
            return False

        try:
            status, message = self.imap.select(folder_name, readonly=False)
            if status == 'OK':
                self.current_folder = folder_name
                self.logger.debug(f"Selected folder: {folder_name}")
                return True

            self.logger.warning(f"Failed to select folder {folder_name}: {message}")
            return False

        except Exception as e:
            self.logger.error(f"Error selecting folder {folder_name}: {e}")
            return False

    # ========== Email Retrieval ==========

    def get_recent_emails(
        self,
        folder_name: str = "INBOX",
        since_datetime: Optional[datetime] = None,
        limit: int = 100,
        include_read: bool = True
    ) -> list[EmailMessage]:
        """Get recent emails from specified folder"""
        if not self.is_connected or not self.imap:
            raise RuntimeError("Not connected to IMAP server")

        emails = []

        try:
            # Re-select folder to get fresh mailbox state
            # IMAP maintains a cached view - must re-select to see new messages
            # that arrived since last selection
            if self.imap and self.current_folder:
                try:
                    self.imap.close()  # Close current folder
                    self.logger.debug(f"Closed folder to refresh state")
                except Exception as e:
                    self.logger.warning(f"Error closing folder (continuing anyway): {e}")

            # Select folder (fresh state)
            if not self.select_folder(folder_name):
                raise Exception(f"Cannot access folder: {folder_name}")

            self.logger.debug(f"Re-selected folder {folder_name} for fresh mailbox state")

            # Build search criteria
            search_criteria = []

            if not include_read:
                search_criteria.append('UNSEEN')

            if since_datetime:
                # IMAP SINCE only supports date filtering (no time component)
                # Format: DD-MMM-YYYY (e.g., "04-Nov-2025")
                # Note: We filter by exact time later in the fetch loop
                date_str = since_datetime.strftime('%d-%b-%Y')
                search_criteria.append(f'SINCE {date_str}')

            # Search for messages
            search_query = ' '.join(search_criteria) if search_criteria else 'ALL'
            self.logger.debug(f"Searching {folder_name} with criteria: {search_query}")

            status, message_ids = self.imap.search(None, search_query)

            if status != 'OK':
                raise Exception(f"Search failed: {message_ids}")

            # Get message IDs
            msg_id_list = message_ids[0].split()

            # Limit results
            if len(msg_id_list) > limit:
                msg_id_list = msg_id_list[-limit:]  # Get most recent

            self.logger.debug(f"Found {len(msg_id_list)} messages")

            # Fetch messages
            for msg_id in msg_id_list:
                try:
                    email_msg = self._fetch_email_message(msg_id, folder_name)
                    if email_msg:
                        # Filter by exact time if since_datetime provided
                        # IMAP SINCE only filters by date, so we need to filter by time here
                        if since_datetime:
                            # Ensure both datetimes are timezone-aware for comparison
                            msg_time = email_msg.received_date
                            cutoff_time = since_datetime

                            # If cutoff_time is naive, make it UTC
                            if cutoff_time.tzinfo is None:
                                from datetime import timezone
                                cutoff_time = cutoff_time.replace(tzinfo=timezone.utc)

                            # If msg_time is naive, make it UTC
                            if msg_time.tzinfo is None:
                                from datetime import timezone
                                msg_time = msg_time.replace(tzinfo=timezone.utc)

                            # Skip emails received before the cutoff time
                            if msg_time < cutoff_time:
                                self.logger.debug(
                                    f"Skipping email {msg_id.decode()} - "
                                    f"received at {msg_time} (before cutoff {cutoff_time})"
                                )
                                continue

                        emails.append(email_msg)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch message {msg_id}: {e}")
                    continue

            self.logger.debug(f"Retrieved {len(emails)} emails from {folder_name}")
            return emails

        except Exception as e:
            self.logger.error(f"Error getting recent emails: {e}", exc_info=True)
            raise

    def get_email_by_id(self, message_id: str, folder_name: str = "INBOX") -> Optional[EmailMessage]:
        """Get specific email by message ID (UID)"""
        if not self.is_connected or not self.imap:
            return None

        try:
            # Select folder
            if folder_name != self.current_folder:
                if not self.select_folder(folder_name):
                    return None

            # Fetch by UID
            return self._fetch_email_message(message_id, folder_name)

        except Exception as e:
            self.logger.error(f"Error getting email by ID: {e}")
            return None

    def _fetch_email_message(self, msg_id: str | bytes, folder_name: str) -> Optional[EmailMessage]:
        """Fetch and parse a single email message"""
        if not self.imap:
            return None

        try:
            # Fetch email data - fetch() expects str, not bytes
            # Convert bytes to str if necessary (from search results)
            msg_id_str = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id
            status, msg_data = self.imap.fetch(msg_id_str, '(RFC822)')

            if status != 'OK' or not msg_data[0]:
                return None

            # Parse email
            email_body = msg_data[0][1]
            assert type(email_body) is bytes 
            email_message = email.message_from_bytes(email_body)

            # Extract fields
            message_uid = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id
            subject = self._decode_header_value(email_message.get('Subject', ''))
            sender_email = self._extract_email_address(email_message.get('From', ''))
            sender_name = self._extract_name(email_message.get('From', ''))

            # Recipients
            recipient_emails = []
            to_header = email_message.get('To', '')
            if to_header:
                recipient_emails.append(self._extract_email_address(to_header))

            # Date
            date_str = email_message.get('Date', '')
            received_date = self._parse_email_date(date_str)

            # Body
            body_text, body_html = self._extract_body(email_message)
            body_preview = body_text[:500] if body_text else None

            # Attachments - extract both metadata and actual attachment data
            has_attachments = False
            attachment_count = 0
            attachment_filenames = []
            cached_attachments = []

            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    has_attachments = True
                    attachment_count += 1
                    filename = part.get_filename()
                    if filename:
                        decoded_filename = self._decode_header_value(filename)
                        attachment_filenames.append(decoded_filename)

                        # Extract the actual attachment content for caching
                        try:
                            attachment = self._extract_attachment(part)
                            if attachment:
                                cached_attachments.append(attachment)
                                self.logger.debug(
                                    f"Cached attachment: {decoded_filename} "
                                    f"({len(attachment.content)} bytes)"
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to extract attachment {decoded_filename}: {e}"
                            )

            if has_attachments:
                self.logger.debug(
                    f"Email {message_uid} has {attachment_count} attachments, "
                    f"successfully cached {len(cached_attachments)}"
                )

            # Read status (approximate - IMAP doesn't always provide this)
            is_read = True  # Default assumption

            return EmailMessage(
                message_id=message_uid,
                subject=subject,
                sender_email=sender_email,
                sender_name=sender_name,
                recipient_emails=recipient_emails,
                received_date=received_date,
                folder_name=folder_name,
                body_text=body_text,
                body_html=body_html,
                body_preview=body_preview,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
                attachment_filenames=attachment_filenames,
                cached_attachments=cached_attachments,  # Now populated with actual attachment data
                size_bytes=len(email_body),
                is_read=is_read,
                importance='normal'
            )

        except Exception as e:
            self.logger.error(f"Error parsing email message: {e}", exc_info=True)
            return None

    # ========== Attachment Operations ==========

    def get_attachments(self, message_id: str, folder_name: str = "INBOX") -> list[EmailAttachment]:
        """Get all attachments from a specific email"""
        if not self.is_connected or not self.imap:
            return []

        attachments = []

        try:
            # Select folder
            if folder_name != self.current_folder:
                if not self.select_folder(folder_name):
                    return []

            # Fetch email - fetch() expects str, not bytes
            status, msg_data = self.imap.fetch(message_id, '(RFC822)')

            if status != 'OK' or not msg_data[0]:
                return []

            # Parse email
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            # Extract attachments
            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    try:
                        attachment = self._extract_attachment(part)
                        if attachment:
                            attachments.append(attachment)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract attachment: {e}")
                        continue

            self.logger.debug(f"Extracted {len(attachments)} attachments from message {message_id}")
            return attachments

        except Exception as e:
            self.logger.error(f"Error getting attachments: {e}", exc_info=True)
            return []

    def _extract_attachment(self, part) -> Optional[EmailAttachment]:
        """Extract attachment from email part"""
        try:
            filename = part.get_filename()
            if not filename:
                return None

            filename = self._decode_header_value(filename)
            content_type = part.get_content_type()
            content = part.get_payload(decode=True)

            if not content:
                return None

            return EmailAttachment(
                filename=filename,
                content_type=content_type,
                size_bytes=len(content),
                content=content,
                content_id=part.get('Content-ID'),
                is_inline=False
            )

        except Exception as e:
            self.logger.error(f"Error extracting attachment: {e}")
            return None

    # ========== Email State Management ==========

    def mark_as_read(self, message_id: str, folder_name: str = "INBOX") -> bool:
        """Mark email as read"""
        if not self.is_connected or not self.imap:
            return False

        try:
            # Select folder
            if folder_name != self.current_folder:
                if not self.select_folder(folder_name):
                    return False

            # Mark as seen
            status, response = self.imap.store(message_id.encode(), '+FLAGS', '\\Seen')

            if status == 'OK':
                self.logger.debug(f"Marked message {message_id} as read")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error marking message as read: {e}")
            return False

    # ========== Helper Methods ==========

    def _decode_header_value(self, header_value: str) -> str:
        """Decode email header value (handles encoding)"""
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            result = []

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        result.append(part.decode(encoding))
                    else:
                        result.append(part.decode('utf-8', errors='ignore'))
                else:
                    result.append(str(part))

            return ''.join(result)

        except Exception as e:
            self.logger.warning(f"Error decoding header: {e}")
            return str(header_value)

    def _extract_email_address(self, from_header: str) -> str:
        """Extract email address from From header"""
        if not from_header:
            return ""

        # Pattern: "Name" <email@example.com> or email@example.com
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
        if match:
            return match.group(0)

        return from_header

    def _extract_name(self, from_header: str) -> str:
        """Extract name from From header"""
        if not from_header:
            return ""

        # Pattern: "Name" <email@example.com>
        match = re.match(r'"?([^"<]+)"?\s*<', from_header)
        if match:
            return match.group(1).strip()

        # Just email address
        return ""

    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date header to datetime"""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as e:
            self.logger.warning(f"Error parsing date '{date_str}': {e}")
            return datetime.now(timezone.utc)

    def _extract_body(self, email_message) -> tuple[Optional[str], Optional[str]]:
        """Extract text and HTML body from email"""
        body_text = None
        body_html = None

        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get_content_disposition()

                    # Skip attachments
                    if content_disposition == 'attachment':
                        continue

                    if content_type == 'text/plain' and not body_text:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text = payload.decode('utf-8', errors='ignore')

                    elif content_type == 'text/html' and not body_html:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_html = payload.decode('utf-8', errors='ignore')

            else:
                # Single part message
                content_type = email_message.get_content_type()
                payload = email_message.get_payload(decode=True)

                if payload:
                    decoded = payload.decode('utf-8', errors='ignore')
                    if content_type == 'text/plain':
                        body_text = decoded
                    elif content_type == 'text/html':
                        body_html = decoded

        except Exception as e:
            self.logger.error(f"Error extracting body: {e}")

        return body_text, body_html
