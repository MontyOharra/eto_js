"""
IMAP Email Integration
Platform-independent IMAP implementation using imaplib.
"""
import email
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import imaplib
import logging
import re
import ssl
from datetime import datetime, timezone
from typing import Optional

from .base_integration import BaseEmailIntegration, EmailMessage
from .registry import IntegrationRegistry

logger = logging.getLogger(__name__)


@IntegrationRegistry.register(
    "imap",
    name="IMAP",
    description="Connect to any email server using IMAP protocol",
    platforms=["windows", "linux", "darwin"],
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
    ):
        """
        Initialize IMAP integration.

        Args:
            host: IMAP server hostname (e.g., "mail.example.com")
            port: IMAP server port (usually 993 for SSL, 143 for non-SSL)
            email_address: Email address for login
            password: Email password or app password
            use_ssl: Use SSL/TLS connection (default: True)
        """
        super().__init__()

        self.host = host
        self.port = port
        self.email_address = email_address
        self.password = password
        self.use_ssl = use_ssl

        # Connection state
        self._imap: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None

        self.logger.debug(f"Initialized ImapIntegration for {email_address}@{host}:{port}")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._imap is not None

    def connect(self) -> bool:
        """
        Establish connection to IMAP server.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.logger.debug(f"Connecting to IMAP server {self.host}:{self.port} (SSL: {self.use_ssl})")

            # Create connection
            if self.use_ssl:
                context = ssl.create_default_context()
                self._imap = imaplib.IMAP4_SSL(
                    host=self.host,
                    port=self.port,
                    ssl_context=context,
                )
            else:
                self._imap = imaplib.IMAP4(
                    host=self.host,
                    port=self.port,
                )

            # Authenticate
            self.logger.debug(f"Authenticating as {self.email_address}")
            self._imap.login(self.email_address, self.password)

            self.logger.info(f"Connected to IMAP server {self.host}")
            return True

        except imaplib.IMAP4.error as e:
            self.logger.error(f"IMAP authentication failed for {self.host}: {e}")
            self._imap = None
            return False

        except Exception as e:
            self.logger.error(f"Failed to connect to IMAP server {self.host}: {e}")
            self._imap = None
            return False

    def disconnect(self) -> None:
        """Close connection to IMAP server."""
        if self._imap is None:
            return

        try:
            try:
                self._imap.close()
            except Exception:
                pass  # Folder may not be selected

            self._imap.logout()
            self.logger.info(f"Disconnected from IMAP server {self.host}")

        except Exception as e:
            self.logger.warning(f"Error during disconnect from {self.host}: {e}")

        finally:
            self._imap = None

    def get_capabilities(self) -> list[str]:
        """
        Get server capabilities (IMAP-specific).

        Must be connected before calling.

        Returns:
            List of capability strings (e.g., ["IMAP4rev1", "IDLE", "UIDPLUS"])
        """
        if self._imap is None:
            raise RuntimeError("Not connected. Call connect() first.")

        capabilities = []
        if hasattr(self._imap, 'capabilities') and self._imap.capabilities:
            for cap in self._imap.capabilities:
                if isinstance(cap, bytes):
                    capabilities.append(cap.decode('utf-8'))
                else:
                    capabilities.append(str(cap))

        return capabilities

    def list_folders(self) -> list[str]:
        """
        List all folders/mailboxes on the server.

        Must be connected before calling.

        Returns:
            List of folder paths (e.g., ["INBOX", "INBOX.Sent", "INBOX.Drafts"])
            The delimiter is included in the path (e.g., "." or "/")
        """
        if self._imap is None:
            raise RuntimeError("Not connected. Call connect() first.")

        folders: list[str] = []

        # LIST command returns all mailboxes
        # Pattern "" "*" means: reference "" (root), pattern "*" (all folders)
        status, folder_data = self._imap.list()

        if status != "OK":
            self.logger.warning(f"Failed to list folders: {status}")
            return folders

        for item in folder_data:
            if item is None:
                continue

            # Each item is bytes like:
            #   b'(\\HasNoChildren) "." "INBOX.Subfolder"'
            #   b'(\\HasNoChildren) "." INBOX'
            #   b'(\\Noselect) "/" ""'  <- root, skip this
            if isinstance(item, bytes):
                item_str = item.decode('utf-8')
            else:
                item_str = str(item)

            # Parse the IMAP LIST response
            # Format: (flags) "delimiter" folder_name
            # folder_name may be quoted or unquoted
            try:
                # Find the closing paren of flags
                paren_end = item_str.find(')')
                if paren_end == -1:
                    continue

                # Rest is: "delimiter" folder_name
                rest = item_str[paren_end + 1:].strip()

                # Extract delimiter (quoted)
                if not rest.startswith('"'):
                    continue
                delim_end = rest.find('"', 1)
                if delim_end == -1:
                    continue

                # Get folder name (everything after delimiter, stripped)
                folder_part = rest[delim_end + 1:].strip()

                # Folder name may be quoted or unquoted
                if folder_part.startswith('"') and folder_part.endswith('"'):
                    folder_name = folder_part[1:-1]
                else:
                    folder_name = folder_part

                # Skip empty folder names (root namespace)
                if not folder_name:
                    continue

                folders.append(folder_name)

            except Exception as e:
                self.logger.debug(f"Could not parse folder from: {item_str} - {e}")
                continue

        # Sort alphabetically (case-insensitive)
        folders.sort(key=str.casefold)

        self.logger.debug(f"Found {len(folders)} folders")
        return folders

    def get_emails_since_uid(
        self,
        folder_name: str,
        since_uid: int,
        limit: int = 100,
    ) -> list[EmailMessage]:
        """
        Get emails with UID greater than since_uid.

        Uses IMAP UID SEARCH and UID FETCH commands for efficient retrieval.

        Args:
            folder_name: Folder to retrieve emails from
            since_uid: Only get emails with UID > this value
            limit: Maximum number of emails to retrieve

        Returns:
            List of EmailMessage dataclasses ordered by UID ascending
        """
        if self._imap is None:
            raise RuntimeError("Not connected. Call connect() first.")

        # Select the folder
        status, data = self._imap.select(folder_name, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Failed to select folder '{folder_name}': {data}")

        # Build UID search range: UID greater than since_uid
        # IMAP UID ranges: "UID start:*" means from start to highest
        search_range = f"{since_uid + 1}:*"

        self.logger.debug(f"Searching for UIDs in range {search_range}")

        # UID SEARCH to find matching messages
        status, data = self._imap.uid("SEARCH", None, f"UID {search_range}")
        if status != "OK":
            self.logger.warning(f"UID SEARCH failed: {data}")
            return []

        # Parse UIDs from response
        uid_list_str = data[0].decode("utf-8") if data[0] else ""
        if not uid_list_str.strip():
            self.logger.debug("No new emails found")
            return []

        uid_list = [int(uid) for uid in uid_list_str.split()]

        # Filter out UIDs <= since_uid (IMAP range is inclusive)
        uid_list = [uid for uid in uid_list if uid > since_uid]

        # Sort ascending (oldest first) and apply limit
        uid_list.sort()
        uid_list = uid_list[:limit]

        if not uid_list:
            self.logger.debug("No new emails after filtering")
            return []

        self.logger.debug(f"Found {len(uid_list)} new emails: UIDs {uid_list[0]}-{uid_list[-1]}")

        # Fetch each email
        messages: list[EmailMessage] = []
        for uid in uid_list:
            try:
                msg = self._fetch_email_by_uid(uid, folder_name)
                if msg:
                    messages.append(msg)
            except Exception as e:
                self.logger.warning(f"Failed to fetch email UID {uid}: {e}")
                continue

        return messages

    def get_highest_uid(self, folder_name: str) -> int | None:
        """
        Get the highest UID in the folder.

        Args:
            folder_name: Folder to check

        Returns:
            Highest UID in folder, or None if folder is empty
        """
        if self._imap is None:
            raise RuntimeError("Not connected. Call connect() first.")

        # Select the folder
        status, data = self._imap.select(folder_name, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Failed to select folder '{folder_name}': {data}")

        # Search for all messages
        status, data = self._imap.uid("SEARCH", None, "ALL")
        if status != "OK":
            self.logger.warning(f"UID SEARCH ALL failed: {data}")
            return None

        uid_list_str = data[0].decode("utf-8") if data[0] else ""
        if not uid_list_str.strip():
            return None

        uid_list = [int(uid) for uid in uid_list_str.split()]
        if not uid_list:
            return None

        highest = max(uid_list)
        self.logger.debug(f"Highest UID in {folder_name}: {highest}")
        return highest

    def _fetch_email_by_uid(self, uid: int, folder_name: str) -> EmailMessage | None:
        """
        Fetch a single email by UID.

        Args:
            uid: Email UID
            folder_name: Folder containing the email

        Returns:
            EmailMessage dataclass or None if fetch fails
        """
        if self._imap is None:
            raise RuntimeError("Not connected. Call connect() first.")

        # Fetch the email headers and body structure
        # BODY.PEEK[] fetches entire message without marking as read
        status, data = self._imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if status != "OK":
            self.logger.warning(f"Failed to fetch UID {uid}: {data}")
            return None

        # Parse the response - data is a list of tuples
        raw_email = None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                raw_email = item[1]
                break

        if not raw_email:
            self.logger.warning(f"No email data for UID {uid}")
            return None

        # Parse the email message
        try:
            msg = email.message_from_bytes(raw_email)
            return self._parse_email_message(msg, uid, folder_name)
        except Exception as e:
            self.logger.warning(f"Failed to parse email UID {uid}: {e}")
            return None

    def _parse_email_message(
        self,
        msg: email.message.Message,
        uid: int,
        folder_name: str,
    ) -> EmailMessage:
        """
        Parse an email.message.Message into our EmailMessage dataclass.

        Args:
            msg: Parsed email message
            uid: Email UID
            folder_name: Folder name

        Returns:
            EmailMessage dataclass
        """
        # Extract Message-ID
        message_id = msg.get("Message-ID", "")
        if message_id:
            # Clean up Message-ID (remove < > brackets if present)
            message_id = message_id.strip().strip("<>")

        # Extract subject
        subject = self._decode_header_value(msg.get("Subject", ""))

        # Extract sender
        from_header = msg.get("From", "")
        sender_name, sender_email = parseaddr(from_header)
        sender_name = self._decode_header_value(sender_name) if sender_name else None
        sender_email = sender_email or ""

        # Extract date
        date_header = msg.get("Date")
        received_date = datetime.now(timezone.utc)  # fallback
        if date_header:
            try:
                received_date = parsedate_to_datetime(date_header)
                # Ensure timezone aware
                if received_date.tzinfo is None:
                    received_date = received_date.replace(tzinfo=timezone.utc)
            except Exception:
                pass  # Use fallback

        # Extract body
        body_text = None
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain" and body_text is None:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="replace")
                    except Exception:
                        pass

                elif content_type == "text/html" and body_html is None:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_html = payload.decode(charset, errors="replace")
                    except Exception:
                        pass
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    if content_type == "text/html":
                        body_html = text
                    else:
                        body_text = text
            except Exception:
                pass

        # Count attachments
        attachment_count = 0
        attachment_filenames: list[str] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    attachment_count += 1
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header_value(filename)
                        attachment_filenames.append(filename)

        return EmailMessage(
            uid=uid,
            message_id=message_id,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            received_date=received_date.isoformat(),
            folder_name=folder_name,
            body_text=body_text,
            body_html=body_html,
            has_attachments=attachment_count > 0,
            attachment_count=attachment_count,
            attachment_filenames=attachment_filenames if attachment_filenames else None,
        )

    def _decode_header_value(self, value: str) -> str:
        """
        Decode an email header value that may be encoded (RFC 2047).

        Args:
            value: Raw header value

        Returns:
            Decoded string
        """
        if not value:
            return ""

        try:
            decoded_parts = decode_header(value)
            result_parts = []
            for data, charset in decoded_parts:
                if isinstance(data, bytes):
                    result_parts.append(data.decode(charset or "utf-8", errors="replace"))
                else:
                    result_parts.append(data)
            return "".join(result_parts)
        except Exception:
            return value
