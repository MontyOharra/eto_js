"""
Outlook Connection Service
Manages Outlook COM connections and basic folder operations
"""
import win32com.client
import pythoncom
import logging
import threading
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Connection configuration data structure"""
    email_address: Optional[str]
    folder_name: str


@dataclass
class ConnectionStatus:
    """Connection status information"""
    is_connected: bool
    email_address: Optional[str]
    folder_name: Optional[str]
    inbox_count: int
    last_error: Optional[str]
    connection_time: Optional[datetime]


class OutlookConnectionService:
    """Manages Outlook COM connections and basic folder operations"""
    
    def __init__(self):
        # COM objects
        self.outlook: Optional[win32com.client.CDispatch] = None
        self.namespace: Optional[win32com.client.CDispatch] = None
        self.current_account: Optional[win32com.client.CDispatch] = None
        self.current_folder: Optional[win32com.client.CDispatch] = None
        
        # State management
        self.connection_config: Optional[ConnectionConfig] = None
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
    
    async def connect(self, connection_config: ConnectionConfig) -> ConnectionStatus:
        """Establish connection using configuration"""
        try:
            with self._lock:
                logger.info(f"Connecting to Outlook - Email: {connection_config.email_address or 'Default'}, Folder: {connection_config.folder_name}")
                
                # Store configuration
                self.connection_config = connection_config
                
                # Initialize COM and create objects
                self._initialize_com()
                self.outlook, self.namespace = self._create_outlook_objects()
                
                # Resolve account
                self.current_account = self._resolve_account(connection_config.email_address)
                assert self.current_account is not None
                # Resolve folder
                self.current_folder = self._resolve_folder(self.current_account, connection_config.folder_name)
                
                # Test connection health
                if not self._validate_connection_health():
                    raise Exception("Connection health check failed")
                
                # Update state
                self.is_connected = True
                self.connection_time = datetime.now(timezone.utc)
                self.last_error = None
                
                logger.info(f"Successfully connected to Outlook {connection_config.folder_name} for {self.current_account.DisplayName}")
                
                return await self.get_connection_status()
                
        except Exception as e:
            self._log_connection_error(e, "connect")
            self.last_error = str(e)
            self.is_connected = False
            await self.disconnect()
            raise Exception(f"Outlook connection failed: {str(e)}")
    
    async def disconnect(self) -> bool:
        """Clean disconnection with COM cleanup"""
        try:
            with self._lock:
                logger.info("Disconnecting from Outlook")
                
                self._cleanup_com_objects()
                
                # Reset state
                self.is_connected = False
                self.connection_config = None
                self.connection_time = None
                self.current_account = None
                self.current_folder = None
                
                logger.info("Disconnected from Outlook successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self.last_error = str(e)
            return False
    
    async def get_connection_status(self) -> ConnectionStatus:
        """Get detailed connection status and health"""
        try:
            inbox_count = 0
            email_address = None
            folder_name = None
            
            if self.is_connected and self.current_folder and self.current_account:
                try:
                    # Test connection by accessing basic properties
                    inbox_count = self.current_folder.Items.Count
                    email_address = self.current_account.DisplayName
                    folder_name = self.current_folder.Name
                except Exception as health_error:
                    logger.warning(f"Connection health check failed: {health_error}")
                    # Try to reconnect
                    try:
                        if self.connection_config:
                            await self.reconnect()
                            inbox_count = self.current_folder.Items.Count
                            email_address = self.current_account.DisplayName
                            folder_name = self.current_folder.Name
                    except Exception as reconnect_error:
                        logger.error(f"Reconnection failed: {reconnect_error}")
                        self.is_connected = False
                        self.last_error = str(reconnect_error)
            
            return ConnectionStatus(
                is_connected=self.is_connected,
                email_address=email_address,
                folder_name=folder_name,
                inbox_count=inbox_count,
                last_error=self.last_error,
                connection_time=self.connection_time
            )
            
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return ConnectionStatus(
                is_connected=False,
                email_address=None,
                folder_name=None,
                inbox_count=0,
                last_error=str(e),
                connection_time=None
            )
    
    async def test_connection(self, connection_config: ConnectionConfig) -> Dict[str, Any]:
        """Test connection without establishing persistent connection"""
        try:
            logger.info(f"Testing connection - Email: {connection_config.email_address or 'Default'}, Folder: {connection_config.folder_name}")
            
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            
            try:
                # Create temporary COM objects
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                # Resolve account
                if connection_config.email_address:
                    try:
                        account = namespace.Accounts.Item(connection_config.email_address)
                    except:
                        account = namespace.Accounts.Item(1)
                else:
                    account = namespace.Accounts.Item(1)
                
                # Test folder access
                folder = self._resolve_folder(account, connection_config.folder_name)
                
                # Test basic operations
                folder_count = folder.Items.Count
                
                return {
                    "success": True,
                    "account_name": account.DisplayName,
                    "folder_name": folder.Name,
                    "message_count": folder_count,
                    "message": "Connection test successful"
                }
                
            finally:
                # Clean up COM
                pythoncom.CoUninitialize()
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection test failed"
            }
    
    async def get_available_folders(self, email_address: Optional[str] = None) -> List[Dict[str, str]]:
        """List all accessible folders for account"""
        try:
            logger.info(f"Getting available folders for {email_address or 'default account'}")
            
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            
            try:
                # Create temporary COM objects
                outlook = win32com.client.Dispatch("Outlook.Application")
                namespace = outlook.GetNamespace("MAPI")
                
                # Resolve account
                if email_address:
                    try:
                        account = namespace.Accounts.Item(email_address)
                    except:
                        account = namespace.Accounts.Item(1)
                else:
                    account = namespace.Accounts.Item(1)
                
                folders = []
                
                # Get root folder
                root_folder = account.DeliveryStore.GetRootFolder()
                
                # Add standard folders
                for folder_name, folder_constant in self.folder_mapping.items():
                    try:
                        folder = account.DeliveryStore.GetDefaultFolder(folder_constant)
                        folders.append({
                            "name": folder_name,
                            "display_name": folder.Name,
                            "type": "standard"
                        })
                    except:
                        pass
                
                # Add custom folders from root
                try:
                    for folder in root_folder.Folders:
                        if folder.Name not in [f["display_name"] for f in folders]:
                            folders.append({
                                "name": folder.Name,
                                "display_name": folder.Name,
                                "type": "custom"
                            })
                except Exception as custom_error:
                    logger.warning(f"Error getting custom folders: {custom_error}")
                
                logger.info(f"Found {len(folders)} available folders")
                return folders
                
            finally:
                # Clean up COM
                pythoncom.CoUninitialize()
                
        except Exception as e:
            logger.error(f"Error getting available folders: {e}")
            return []
    
    def get_current_folder(self) -> Optional[win32com.client.CDispatch]:
        """Get current connected folder object (for email scanning)"""
        if self.is_connected and self.current_folder:
            return self.current_folder
        return None
    
    async def reconnect(self, max_retries: int = 3) -> bool:
        """Reconnect with current configuration"""
        if not self.connection_config:
            raise Exception("No connection configuration stored for reconnection")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Reconnecting to Outlook (attempt {attempt + 1}/{max_retries})")
                
                # Clean up existing connection
                await self.disconnect()
                
                # Wait a moment for cleanup
                time.sleep(2)
                
                # Reconnect
                await self.connect(self.connection_config)
                
                logger.info("Reconnection successful")
                return True
                
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying reconnection in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} reconnection attempts failed")
                    raise Exception(f"Reconnection failed after {max_retries} attempts: {str(e)}")
        
        return False

    # === Lower-Level Helper Methods ===
    
    def _initialize_com(self) -> None:
        """Initialize COM for current thread"""
        try:
            pythoncom.CoInitialize()
            logger.debug("COM initialized for thread")
        except Exception as e:
            logger.warning(f"COM initialization warning: {e}")
    
    def _create_outlook_objects(self) -> Tuple[Any, Any]:
        """Create Outlook Application and MAPI namespace"""
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            if not outlook:
                raise Exception("Failed to create Outlook Application object")
            
            namespace = outlook.GetNamespace("MAPI")
            if not namespace:
                raise Exception("Failed to get MAPI namespace")
            
            logger.debug("Created Outlook COM objects successfully")
            return outlook, namespace
            
        except Exception as e:
            logger.error(f"Failed to create Outlook objects: {e}")
            raise Exception(f"COM object creation failed: {e}")
    
    def _resolve_account(self, email_address: Optional[str]) -> Any:
        """Resolve account by email or use default"""
        try:
            assert self.namespace is not None
            if email_address:
                try:
                    account = self.namespace.Accounts.Item(email_address)
                    logger.debug(f"Found specific account: {account.DisplayName}")
                    return account
                except Exception as specific_error:
                    logger.warning(f"Could not find account '{email_address}': {specific_error}")
            
            # Use default account as fallback
            account = self.namespace.Accounts.Item(1)
            logger.info(f"Using default account: {account.DisplayName}")
            return account
            
        except Exception as e:
            logger.error(f"Failed to resolve account: {e}")
            raise Exception(f"Account resolution failed: {e}")
    
    def _resolve_folder(self, account: Any, folder_name: str) -> Any:
        """Resolve folder with fallback logic and error reporting"""
        try:
            # First try standard folders using constants
            if folder_name in self.folder_mapping:
                folder_constant = self.folder_mapping[folder_name]
                try:
                    folder = account.DeliveryStore.GetDefaultFolder(folder_constant)
                    logger.debug(f"Found standard folder: {folder_name} -> {folder.Name}")
                    return folder
                except Exception as std_error:
                    logger.warning(f"Could not access standard folder {folder_name}: {std_error}")
            
            # If not a standard folder or standard folder failed, search custom folders
            logger.debug(f"Searching for custom folder: {folder_name}")
            root_folder = account.DeliveryStore.GetRootFolder()
            
            # Search in root level folders
            for folder in root_folder.Folders:
                if folder.Name.lower() == folder_name.lower():
                    logger.debug(f"Found custom folder: {folder_name} -> {folder.Name}")
                    return folder
            
            # Search in Inbox subfolders (common location for custom folders)
            try:
                inbox = account.DeliveryStore.GetDefaultFolder(6)  # olFolderInbox
                for folder in inbox.Folders:
                    if folder.Name.lower() == folder_name.lower():
                        logger.debug(f"Found custom folder in Inbox: {folder_name} -> {folder.Name}")
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
            logger.error(f"Error resolving folder '{folder_name}': {e}")
            raise Exception(f"Could not access folder '{folder_name}': {str(e)}")
    
    def _validate_connection_health(self) -> bool:
        """Test connection health by accessing basic properties"""
        try:
            if not self.current_folder or not self.current_account:
                return False
            
            # Test basic operations
            folder_count = self.current_folder.Items.Count
            account_name = self.current_account.DisplayName
            
            logger.debug(f"Connection health check passed: {account_name} {self.current_folder.Name} ({folder_count} items)")
            return True
            
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False
    
    def _cleanup_com_objects(self) -> None:
        """Clean up COM objects and uninitialize COM"""
        try:
            # Set COM objects to None
            self.outlook = None
            self.namespace = None
            self.current_account = None
            self.current_folder = None
            
            # Uninitialize COM
            try:
                pythoncom.CoUninitialize()
                logger.debug("COM uninitialized")
            except:
                pass  # Ignore errors on uninitialize
                
        except Exception as e:
            logger.warning(f"Error during COM cleanup: {e}")
    
    def _log_connection_error(self, error: Exception, operation: str) -> None:
        """Log connection errors with context"""
        error_msg = f"Outlook connection error during {operation}: {error}"
        logger.error(error_msg)
        
        # Try to get available drivers for debugging
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            logger.debug(f"Available ODBC drivers: {drivers}")
        except:
            pass