"""
Standard Email Integration
Platform-independent email integration using IMAP (receive) and SMTP (send).
"""
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime, formatdate, make_msgid
from email.message import Message
import imaplib
import logging
import smtplib
import ssl
import threading
import time

from .base_integration import BaseEmailIntegration
from shared.types.email_integrations import EmailMessage, EmailAttachment, ValidationResult, SendEmailResult
from shared.utils.datetime import utc_now, ensure_utc_aware
from .registry import IntegrationRegistry
from shared.exceptions import PermanentEmailError, TransientEmailError

logger = logging.getLogger(__name__)


@IntegrationRegistry.register(
    "standard",
    name="Standard Email",
    description="Connect to any email server using IMAP (receive) and SMTP (send)",
    platforms=["windows", "linux", "darwin"],
)
class StandardEmailIntegration(BaseEmailIntegration):
    """
    Standard email integration using IMAP for receiving and SMTP for sending.

    Manages persistent IMAP connection with automatic keepalive and reconnection.
    Thread-safe for concurrent folder operations via internal lock.
    SMTP connections are created per-send operation.
    """

    # Keepalive interval in seconds (send NOOP to prevent server timeout)
    KEEPALIVE_INTERVAL = 300  # 5 minutes

    def __init__(
        self,
        imap_host: str,
        imap_port: int,
        email_address: str,
        password: str,
        smtp_host: str = "",
        smtp_port: int = 587,
        use_ssl: bool = True,
    ):
        """
        Initialize standard email integration.

        Args:
            imap_host: IMAP server hostname (e.g., "imap.example.com")
            imap_port: IMAP server port (usually 993 for SSL, 143 for non-SSL)
            email_address: Email address for login
            password: Email password or app password
            smtp_host: SMTP server hostname (e.g., "smtp.example.com")
            smtp_port: SMTP server port (587 for TLS, 465 for SSL)
            use_ssl: Use SSL/TLS connection (default: True)
        """
        super().__init__()

        # IMAP settings (receiving)
        self.imap_host = imap_host
        self.imap_port = imap_port

        # SMTP settings (sending)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

        # Shared settings
        self.email_address = email_address
        self.password = password
        self.use_ssl = use_ssl

        # IMAP connection state
        self._imap: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None
        self._lock = threading.Lock()

        # Keepalive thread
        self._keepalive_thread: threading.Thread | None = None
        self._keepalive_stop = threading.Event()

        self.logger.debug(f"Initialized StandardEmailIntegration for {email_address} (IMAP: {imap_host}:{imap_port}, SMTP: {smtp_host}:{smtp_port})")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._imap is not None

    # ========== Lifecycle Methods ==========

    def startup(self) -> None:
        """
        Establish persistent connection and start keepalive.

        Called when first config for this account is activated.
        """
        self.logger.info(f"[IMAP] STARTUP for {self.email_address}")
        self.logger.info(f"[IMAP]   Server: {self.imap_host}:{self.imap_port} (SSL: {self.use_ssl})")

        with self._lock:
            if not self._connect():
                raise RuntimeError(f"Failed to connect to IMAP server {self.imap_host}")

            self._start_keepalive()

        self.logger.info(f"[IMAP] STARTUP COMPLETE - Connection established for {self.email_address}")

    def shutdown(self) -> None:
        """
        Stop keepalive and close connection.

        Called when last config for this account is deactivated or on server shutdown.
        """
        self.logger.info(f"[IMAP] SHUTDOWN for {self.email_address}")

        self._stop_keepalive()

        with self._lock:
            self._disconnect()

        self.logger.info(f"[IMAP] SHUTDOWN COMPLETE - Connection closed for {self.email_address}")

    def validate_credentials(self) -> ValidationResult:
        """
        Validate credentials by connecting, getting capabilities, and disconnecting.

        This is a transient operation - does not use/affect persistent connection.
        """
        self.logger.info(f"Validating credentials for {self.email_address}")

        try:
            # Create temporary connection for validation
            if self.use_ssl:
                context = ssl.create_default_context()
                temp_imap = imaplib.IMAP4_SSL(
                    host=self.imap_host,
                    port=self.imap_port,
                    ssl_context=context,
                )
            else:
                temp_imap = imaplib.IMAP4(
                    host=self.imap_host,
                    port=self.imap_port,
                )

            # Authenticate
            temp_imap.login(self.email_address, self.password)

            # Get folder count
            status, folder_data = temp_imap.list()
            folder_count = 0
            if status == "OK" and folder_data:
                folder_count = len([f for f in folder_data if f])

            # Disconnect
            try:
                temp_imap.logout()
            except Exception:
                pass

            self.logger.info(f"Credentials validated for {self.email_address}")

            return ValidationResult(
                success=True,
                message="Connection successful",
                folder_count=folder_count,
            )

        except imaplib.IMAP4.error as e:
            self.logger.warning(f"IMAP authentication failed for {self.email_address}: {e}")
            return ValidationResult(
                success=False,
                message=f"Authentication failed: {e}",
            )
        except Exception as e:
            self.logger.error(f"Connection failed for {self.email_address}: {e}")
            return ValidationResult(
                success=False,
                message=f"Connection failed: {e}",
            )

    # ========== Internal Connection Management ==========

    def _connect(self) -> bool:
        """
        Establish connection to IMAP server (internal, not locked).

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.logger.debug(f"Connecting to IMAP server {self.imap_host}:{self.imap_port} (SSL: {self.use_ssl})")

            if self.use_ssl:
                context = ssl.create_default_context()
                self._imap = imaplib.IMAP4_SSL(
                    host=self.imap_host,
                    port=self.imap_port,
                    ssl_context=context,
                )
            else:
                self._imap = imaplib.IMAP4(
                    host=self.imap_host,
                    port=self.imap_port,
                )

            self.logger.debug(f"Authenticating as {self.email_address}")
            self._imap.login(self.email_address, self.password)

            self.logger.info(f"Connected to IMAP server {self.imap_host}")
            return True

        except imaplib.IMAP4.error as e:
            self.logger.error(f"IMAP authentication failed for {self.imap_host}: {e}")
            self._imap = None
            return False

        except Exception as e:
            self.logger.error(f"Failed to connect to IMAP server {self.imap_host}: {e}")
            self._imap = None
            return False

    def _disconnect(self) -> None:
        """Close connection to IMAP server (internal, not locked)."""
        if self._imap is None:
            return

        try:
            try:
                self._imap.close()
            except Exception:
                pass  # Folder may not be selected

            self._imap.logout()
            self.logger.info(f"Disconnected from IMAP server {self.imap_host}")

        except Exception as e:
            self.logger.warning(f"Error during disconnect from {self.imap_host}: {e}")

        finally:
            self._imap = None

    def _ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if needed (must hold lock)."""
        if self._imap is None:
            self.logger.warning(f"[IMAP] Connection lost for {self.email_address}, RECONNECTING...")
            if not self._connect():
                raise TransientEmailError(f"Failed to reconnect to IMAP server {self.imap_host}")
            self.logger.info(f"[IMAP] RECONNECTED successfully for {self.email_address}")

    def _is_connection_error(self, error: Exception) -> bool:
        """Check if an exception indicates a dead/broken connection."""
        # imaplib.IMAP4.abort is raised for socket errors
        if isinstance(error, imaplib.IMAP4.abort):
            return True
        # SSL errors indicate connection issues
        if isinstance(error, (ssl.SSLError, ssl.SSLEOFError)):
            return True
        # Socket errors
        if isinstance(error, (ConnectionError, OSError)):
            return True
        # Check error message for connection-related keywords
        error_str = str(error).lower()
        connection_keywords = ['socket', 'eof', 'connection', 'broken pipe', 'reset by peer']
        return any(keyword in error_str for keyword in connection_keywords)

    def _handle_connection_error(self, error: Exception, operation: str) -> None:
        """
        Handle a connection error by cleaning up and preparing for reconnection.

        This sets self._imap to None so _ensure_connected will reconnect on retry.
        Must be called while holding self._lock.
        """
        self.logger.warning(f"[IMAP] Connection error during {operation} for {self.email_address}: {error}")
        try:
            if self._imap is not None:
                self._imap.logout()
        except Exception:
            pass  # Ignore errors during cleanup
        self._imap = None
        self.logger.info(f"[IMAP] Connection cleared for {self.email_address}, will reconnect on retry")

    def _start_keepalive(self) -> None:
        """Start keepalive background thread."""
        if self._keepalive_thread is not None:
            return

        self._keepalive_stop.clear()
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_loop,
            daemon=True,
            name=f"imap-keepalive-{self.email_address}",
        )
        self._keepalive_thread.start()
        self.logger.debug("Keepalive thread started")

    def _stop_keepalive(self) -> None:
        """Stop keepalive background thread."""
        if self._keepalive_thread is None:
            return

        self._keepalive_stop.set()
        self._keepalive_thread.join(timeout=5)
        self._keepalive_thread = None
        self.logger.debug("Keepalive thread stopped")

    def _keepalive_loop(self) -> None:
        """Background thread that sends periodic NOOP to keep connection alive."""
        while not self._keepalive_stop.wait(timeout=self.KEEPALIVE_INTERVAL):
            try:
                with self._lock:
                    if self._imap is not None:
                        self._imap.noop()
                        self.logger.debug(f"[IMAP] Keepalive NOOP sent for {self.email_address}")
            except Exception as e:
                self.logger.warning(f"[IMAP] Keepalive NOOP failed for {self.email_address}: {e}")
                # Connection is dead - set to None so _ensure_connected will reconnect
                with self._lock:
                    try:
                        if self._imap is not None:
                            self._imap.logout()
                    except Exception:
                        pass  # Ignore errors during cleanup
                    self._imap = None
                self.logger.info(f"[IMAP] Connection marked dead for {self.email_address}, will reconnect on next operation")

    # ========== Folder Operations ==========

    def list_folders(self) -> list[str]:
        """
        List all folders/mailboxes on the server.

        Returns:
            List of folder paths sorted alphabetically
        """
        with self._lock:
            self._ensure_connected()

            if self._imap is None:
                raise RuntimeError("Not connected")

            folders: list[str] = []

            status, folder_data = self._imap.list()

            if status != "OK":
                self.logger.warning(f"Failed to list folders: {status}")
                return folders

            for item in folder_data:
                if item is None:
                    continue

                if isinstance(item, bytes):
                    item_str = item.decode('utf-8')
                else:
                    item_str = str(item)

                try:
                    paren_end = item_str.find(')')
                    if paren_end == -1:
                        continue

                    rest = item_str[paren_end + 1:].strip()

                    if not rest.startswith('"'):
                        continue
                    delim_end = rest.find('"', 1)
                    if delim_end == -1:
                        continue

                    folder_part = rest[delim_end + 1:].strip()

                    if folder_part.startswith('"') and folder_part.endswith('"'):
                        folder_name = folder_part[1:-1]
                    else:
                        folder_name = folder_part

                    if not folder_name:
                        continue

                    folders.append(folder_name)

                except Exception as e:
                    self.logger.debug(f"Could not parse folder from: {item_str} - {e}")
                    continue

            folders.sort(key=str.casefold)

            self.logger.debug(f"Found {len(folders)} folders")
            return folders

    # ========== Email Operations ==========

    def get_emails_since_uid(
        self,
        folder_name: str,
        since_uid: int,
        limit: int = 100,
    ) -> list[EmailMessage]:
        """
        Get emails with UID greater than since_uid.

        Thread-safe - uses internal lock.
        Automatically handles connection errors by clearing connection for retry.
        """
        with self._lock:
            try:
                self._ensure_connected()

                if self._imap is None:
                    raise TransientEmailError("Not connected")

                # Select the folder (quote if contains spaces)
                quoted_folder = self._quote_folder_name(folder_name)
                self.logger.debug(f"[IMAP] Selecting folder '{folder_name}' (quoted: {quoted_folder}) for {self.email_address}")
                status, data = self._imap.select(quoted_folder, readonly=True)
                if status != "OK":
                    self._raise_folder_error(folder_name, data)

                search_range = f"{since_uid + 1}:*"

                self.logger.debug(f"Searching for UIDs in range {search_range}")

                status, data = self._imap.uid("SEARCH", f"UID {search_range}")
                if status != "OK":
                    self.logger.warning(f"UID SEARCH failed: {data}")
                    return []

                uid_list_str = data[0].decode("utf-8") if data[0] else ""
                if not uid_list_str.strip():
                    self.logger.debug("No new emails found")
                    return []

                uid_list = [int(uid) for uid in uid_list_str.split()]
                uid_list = [uid for uid in uid_list if uid > since_uid]
                uid_list.sort()
                uid_list = uid_list[:limit]

                if not uid_list:
                    self.logger.debug("No new emails after filtering")
                    return []

                self.logger.debug(f"Found {len(uid_list)} new emails: UIDs {uid_list[0]}-{uid_list[-1]}")

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

            except (PermanentEmailError, TransientEmailError):
                # Re-raise our own exceptions as-is
                raise
            except Exception as e:
                # Check if this is a connection error
                if self._is_connection_error(e):
                    self._handle_connection_error(e, "get_emails_since_uid")
                    raise TransientEmailError(f"Connection lost during email fetch: {e}")
                # Unknown error - re-raise as-is
                raise

    def get_highest_uid(self, folder_name: str) -> int | None:
        """
        Get the highest UID in the folder.

        Thread-safe - uses internal lock.
        Automatically handles connection errors by clearing connection for retry.
        """
        with self._lock:
            try:
                self._ensure_connected()

                if self._imap is None:
                    raise TransientEmailError("Not connected")

                quoted_folder = self._quote_folder_name(folder_name)
                status, data = self._imap.select(quoted_folder, readonly=True)
                if status != "OK":
                    self._raise_folder_error(folder_name, data)

                status, data = self._imap.uid("SEARCH", "ALL")
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

            except (PermanentEmailError, TransientEmailError):
                raise
            except Exception as e:
                if self._is_connection_error(e):
                    self._handle_connection_error(e, "get_highest_uid")
                    raise TransientEmailError(f"Connection lost during UID lookup: {e}")
                raise

    def get_attachments(
        self,
        folder_name: str,
        uid: int,
        file_extensions: list[str] | None = None,
    ) -> list[EmailAttachment]:
        """
        Download attachments for a specific email by UID.

        Thread-safe - uses internal lock.
        Automatically handles connection errors by clearing connection for retry.

        Args:
            folder_name: Folder containing the email
            uid: UID of the email
            file_extensions: Optional list of extensions to filter by (e.g., [".pdf"]).
                            Case-insensitive. If None, returns all attachments.

        Returns:
            List of EmailAttachment dataclasses with filename, content_type, and data
        """
        with self._lock:
            try:
                self._ensure_connected()

                if self._imap is None:
                    raise TransientEmailError("Not connected")

                # Select folder (quote if contains spaces)
                quoted_folder = self._quote_folder_name(folder_name)
                status, _ = self._imap.select(quoted_folder, readonly=True)
                if status != "OK":
                    self.logger.error(f"Failed to select folder {folder_name}")
                    return []

                # Fetch the email
                status, data = self._imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
                if status != "OK":
                    self.logger.warning(f"Failed to fetch UID {uid} for attachments: {data}")
                    return []

                raw_email = None
                for item in data:
                    if isinstance(item, tuple) and len(item) >= 2:
                        raw_email = item[1]
                        break

                if not raw_email:
                    self.logger.warning(f"No email data for UID {uid}")
                    return []

                try:
                    msg = email.message_from_bytes(raw_email)
                    return self._extract_attachments(msg, file_extensions)
                except Exception as e:
                    self.logger.error(f"Failed to parse email UID {uid} for attachments: {e}")
                    return []

            except (PermanentEmailError, TransientEmailError):
                raise
            except Exception as e:
                if self._is_connection_error(e):
                    self._handle_connection_error(e, "get_attachments")
                    raise TransientEmailError(f"Connection lost during attachment fetch: {e}")
                raise

    def _extract_attachments(
        self,
        msg: Message,
        file_extensions: list[str] | None = None,
    ) -> list[EmailAttachment]:
        """
        Extract attachments from a parsed email message.

        Args:
            msg: Parsed email message
            file_extensions: Optional list of extensions to filter by (e.g., [".pdf"])

        Returns:
            List of EmailAttachment dataclasses
        """
        attachments: list[EmailAttachment] = []

        # Normalize extensions for case-insensitive comparison
        normalized_extensions: set[str] | None = None
        if file_extensions:
            normalized_extensions = {ext.lower().lstrip('.') for ext in file_extensions}

        if not msg.is_multipart():
            return attachments

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip non-attachment parts
            if "attachment" not in content_disposition:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            # Decode filename if needed
            filename = self._decode_header_value(filename)

            # Check extension filter
            if normalized_extensions:
                # Get file extension (without the dot)
                ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                if ext not in normalized_extensions:
                    self.logger.debug(f"Skipping attachment '{filename}' - extension '.{ext}' not in filter")
                    continue

            # Get attachment content
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    self.logger.warning(f"Empty payload for attachment '{filename}'")
                    continue
                if not isinstance(payload, bytes):
                    self.logger.warning(f"Unexpected payload type for '{filename}': {type(payload)}")
                    continue
            
                content_type = part.get_content_type() or "application/octet-stream"

                attachments.append(EmailAttachment(
                    filename=filename,
                    content_type=content_type,
                    data=payload,
                ))

                self.logger.debug(
                    f"Extracted attachment: '{filename}' ({content_type}, {len(payload)} bytes)"
                )

            except Exception as e:
                self.logger.error(f"Failed to extract attachment '{filename}': {e}")
                continue

        self.logger.info(f"Extracted {len(attachments)} attachment(s)" +
                        (f" matching extensions {file_extensions}" if file_extensions else ""))

        return attachments

    # ========== Helper Methods ==========

    def _quote_folder_name(self, folder_name: str) -> str:
        """
        Quote folder name for IMAP commands if needed.

        IMAP requires folder names containing spaces or special characters
        to be enclosed in double quotes.
        """
        # If already quoted, return as-is
        if folder_name.startswith('"') and folder_name.endswith('"'):
            return folder_name

        # Quote if contains spaces or special IMAP characters
        if ' ' in folder_name or any(c in folder_name for c in ['(', ')', '{', '}', '%', '*', '\\']):
            # Escape any existing double quotes and backslashes
            escaped = folder_name.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'

        return folder_name

    # ========== Error Handling ==========

    def _raise_folder_error(self, folder_name: str, data: list) -> None:
        """
        Raise appropriate exception based on folder selection error.

        Categorizes errors as permanent (folder doesn't exist) or transient
        (connection issues, server errors).
        """
        error_str = str(data)
        error_bytes = data[0] if data and isinstance(data[0], bytes) else b""

        # Check for permanent errors (folder doesn't exist)
        permanent_indicators = [
            b"doesn't exist",
            b"does not exist",
            b"not exist",
            b"Mailbox not found",
            b"NO Mailbox",
            b"NONEXISTENT",
        ]

        for indicator in permanent_indicators:
            if indicator.lower() in error_bytes.lower():
                raise PermanentEmailError(
                    f"Folder '{folder_name}' does not exist: {error_str}"
                )

        # Default to transient error (may be connection issue, server problem, etc.)
        raise TransientEmailError(
            f"Failed to select folder '{folder_name}': {error_str}"
        )

    # ========== Internal Email Parsing ==========

    def _fetch_email_by_uid(self, uid: int, folder_name: str) -> EmailMessage | None:
        """Fetch a single email by UID (must hold lock)."""
        if self._imap is None:
            raise RuntimeError("Not connected")

        status, data = self._imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if status != "OK":
            self.logger.warning(f"Failed to fetch UID {uid}: {data}")
            return None

        raw_email = None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                raw_email = item[1]
                break

        if not raw_email:
            self.logger.warning(f"No email data for UID {uid}")
            return None

        try:
            msg = email.message_from_bytes(raw_email)
            return self._parse_email_message(msg, uid, folder_name)
        except Exception as e:
            self.logger.warning(f"Failed to parse email UID {uid}: {e}")
            return None

    def _parse_email_message(
        self,
        msg: Message,
        uid: int,
        folder_name: str,
    ) -> EmailMessage:
        """Parse an email.message.Message into our EmailMessage dataclass."""
        message_id = msg.get("Message-ID", "")
        if message_id:
            message_id = message_id.strip().strip("<>")

        subject = self._decode_header_value(msg.get("Subject", ""))

        from_header = msg.get("From", "")
        sender_name, sender_email = parseaddr(from_header)
        sender_name = self._decode_header_value(sender_name) if sender_name else None
        sender_email = sender_email or ""

        date_header = msg.get("Date")
        received_date = utc_now()
        if date_header:
            try:
                received_date = ensure_utc_aware(parsedate_to_datetime(date_header))
            except Exception:
                pass

        body_text = None
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain" and body_text is None:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="replace")
                    except Exception:
                        pass

                elif content_type == "text/html" and body_html is None:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            body_html = payload.decode(charset, errors="replace")
                    except Exception:
                        pass
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    charset = msg.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    if content_type == "text/html":
                        body_html = text
                    else:
                        body_text = text
            except Exception:
                pass

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
        """Decode an email header value that may be encoded (RFC 2047)."""
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

    # ========== SMTP Email Sending ==========

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        body_html: str | None = None,
    ) -> SendEmailResult:
        """
        Send an email using SMTP.

        Creates a new SMTP connection for each send operation (stateless).
        Uses TLS/SSL based on port and use_ssl setting.

        Args:
            to_address: Recipient email address
            subject: Email subject line
            body: Plain text email body
            body_html: Optional HTML email body (if provided, sends multipart)

        Returns:
            SendEmailResult with success status and message
        """
        if not self.smtp_host:
            return SendEmailResult(
                success=False,
                message="SMTP host not configured for this email account",
            )

        self.logger.info(f"[SMTP] Sending email to {to_address}")
        self.logger.debug(f"[SMTP]   Server: {self.smtp_host}:{self.smtp_port}")
        self.logger.debug(f"[SMTP]   Subject: {subject}")

        try:
            # Build the email message
            if body_html:
                # Multipart message with both plain text and HTML
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(body_html, "html", "utf-8"))
            else:
                # Plain text only
                msg = MIMEText(body, "plain", "utf-8")

            # Standard headers (required by RFC 5322 and expected by mail servers)
            msg["Subject"] = subject
            msg["From"] = self.email_address
            msg["To"] = to_address
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain=self.email_address.split("@")[1])
            msg["MIME-Version"] = "1.0"

            # Connect and send
            # Port 465 = SSL (SMTPS), Port 587 = STARTTLS, others = try STARTTLS
            if self.smtp_port == 465:
                # Direct SSL connection
                self.logger.debug("[SMTP] Using SSL connection (port 465)")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    host=self.smtp_host,
                    port=self.smtp_port,
                    context=context,
                ) as smtp:
                    smtp.login(self.email_address, self.password)
                    smtp.send_message(msg)
            else:
                # STARTTLS connection (port 587 or other)
                self.logger.debug(f"[SMTP] Using STARTTLS connection (port {self.smtp_port})")
                with smtplib.SMTP(
                    host=self.smtp_host,
                    port=self.smtp_port,
                ) as smtp:
                    smtp.ehlo()
                    if self.use_ssl:
                        context = ssl.create_default_context()
                        smtp.starttls(context=context)
                        smtp.ehlo()
                    smtp.login(self.email_address, self.password)
                    smtp.send_message(msg)

            self.logger.info(f"[SMTP] Email sent successfully to {to_address}")
            return SendEmailResult(
                success=True,
                message=f"Email sent successfully to {to_address}",
            )

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"[SMTP] Authentication failed: {e}")
            return SendEmailResult(
                success=False,
                message=f"SMTP authentication failed: {e}",
            )
        except smtplib.SMTPRecipientsRefused as e:
            self.logger.error(f"[SMTP] Recipient refused: {e}")
            return SendEmailResult(
                success=False,
                message=f"Recipient address refused: {to_address}",
            )
        except smtplib.SMTPException as e:
            self.logger.error(f"[SMTP] SMTP error: {e}")
            return SendEmailResult(
                success=False,
                message=f"SMTP error: {e}",
            )
        except Exception as e:
            self.logger.error(f"[SMTP] Failed to send email: {e}")
            return SendEmailResult(
                success=False,
                message=f"Failed to send email: {e}",
            )
