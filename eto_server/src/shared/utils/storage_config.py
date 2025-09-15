"""
Cross-Platform Storage Configuration Utilities
Handles platform-specific application data directory detection and configuration
"""
import os
import sys
import platform
import tempfile
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def get_default_storage_path() -> str:
    """
    Get platform-appropriate default storage path
    
    Returns:
        str: Platform-specific default storage directory path
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: Use LOCALAPPDATA or APPDATA
        appdata = os.getenv('LOCALAPPDATA', os.getenv('APPDATA'))
        if appdata:
            return os.path.join(appdata, 'ETO_System', 'pdf_storage')
        else:
            # Fallback to user profile
            return os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ETO_System', 'pdf_storage')
    
    elif system == "darwin":  # macOS
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'ETO_System', 'pdf_storage')
    
    elif system == "linux":
        # Linux: Use XDG_DATA_HOME or fallback to ~/.local/share
        xdg_data_home = os.getenv('XDG_DATA_HOME')
        if xdg_data_home:
            return os.path.join(xdg_data_home, 'eto_system', 'pdf_storage')
        else:
            return os.path.join(os.path.expanduser('~'), '.local', 'share', 'eto_system', 'pdf_storage')
    
    else:
        # Unknown system - use home directory
        logger.warning(f"Unknown system platform: {system}, using home directory fallback")
        return os.path.join(os.path.expanduser('~'), '.eto_system', 'pdf_storage')


def get_portable_storage_path() -> str:
    """
    Get storage path relative to application executable for portable deployments
    
    Returns:
        str: Path relative to executable or script location
    """
    try:
        # If running as compiled executable (PyInstaller)
        if hasattr(sys, '_MEIPASS'):
            app_dir = os.path.dirname(sys.executable)
            logger.debug("Detected PyInstaller executable, using executable directory")
        else:
            # If running as Python script - go up from src/ to project root
            current_file = os.path.abspath(__file__)
            # Navigate: storage_config.py -> utils -> shared -> src -> project_root
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
            logger.debug(f"Detected Python script, using project root: {app_dir}")
        
        portable_path = os.path.join(app_dir, 'data', 'pdf_storage')
        logger.info(f"Portable storage path: {portable_path}")
        return portable_path
        
    except Exception as e:
        logger.warning(f"Error determining portable path: {e}, falling back to user data directory")
        return get_default_storage_path()


def get_development_storage_path() -> str:
    """
    Get development storage path - maintains current C:/apps/eto/ structure for testing
    
    Returns:
        str: Development storage path
    """
    return "C:/apps/eto/server/storage"


def get_app_config_file_path() -> str:
    """
    Get path to application configuration file
    
    Returns:
        str: Path to config file location
    """
    system = platform.system().lower()
    
    if system == "windows":
        appdata = os.getenv('APPDATA')
        if appdata:
            return os.path.join(appdata, 'ETO_System', 'config.json')
        else:
            return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'ETO_System', 'config.json')
    
    elif system == "darwin":  # macOS
        return os.path.join(os.path.expanduser('~'), 'Library', 'Preferences', 'com.eto_system.config.json')
    
    else:  # Linux and others
        xdg_config_home = os.getenv('XDG_CONFIG_HOME')
        if xdg_config_home:
            return os.path.join(xdg_config_home, 'eto_system', 'config.json')
        else:
            return os.path.join(os.path.expanduser('~'), '.config', 'eto_system', 'config.json')


def load_app_config(config_file_path: str) -> Dict[str, Any]:
    """
    Load application configuration from JSON file
    
    Args:
        config_file_path: Path to configuration file
        
    Returns:
        Dict[str, Any]: Configuration dictionary or empty dict if not found
    """
    try:
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as f:
                config = json.load(f)
                logger.debug(f"Loaded configuration from: {config_file_path}")
                return config
        else:
            logger.debug(f"Configuration file not found: {config_file_path}")
            return {}
    except Exception as e:
        logger.warning(f"Error loading configuration from {config_file_path}: {e}")
        return {}


def save_app_config(config: Dict[str, Any], config_file_path: Optional[str] = None) -> bool:
    """
    Save application configuration to JSON file
    
    Args:
        config: Configuration dictionary to save
        config_file_path: Optional custom path, uses default if not provided
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not config_file_path:
            config_file_path = get_app_config_file_path()
        
        # Ensure directory exists
        config_dir = os.path.dirname(config_file_path)
        os.makedirs(config_dir, exist_ok=True)
        
        # Add metadata
        config_with_meta = config.copy()
        config_with_meta.update({
            'last_updated': datetime.now().isoformat(),
            'platform': platform.system(),
            'version': '1.0'
        })
        
        with open(config_file_path, 'w') as f:
            json.dump(config_with_meta, f, indent=2)
        
        logger.info(f"Saved configuration to: {config_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False


def get_storage_configuration() -> str:
    """
    Get PDF storage path with priority order:
    1. Explicit environment variable (PDF_STORAGE_ROOT)
    2. Application-specific config file setting
    3. Development mode detection (for testing)
    4. Platform-specific default
    
    Returns:
        str: Configured storage path
    """
    # Priority 1: Explicit environment variable
    env_path = os.getenv('PDF_STORAGE_ROOT')
    if env_path:
        logger.info(f"Using environment variable storage path: {env_path}")
        return env_path
    
    # Priority 2: Check if running in development mode
    # Detect if we're running server scripts or in development
    if is_development_mode():
        dev_path = get_development_storage_path()
        logger.info(f"Development mode detected, using: {dev_path}")
        return dev_path
    
    # Priority 3: Application-specific config file
    config_file = get_app_config_file_path()
    if os.path.exists(config_file):
        config = load_app_config(config_file)
        stored_path = config.get('pdf_storage_root')
        if stored_path and os.path.exists(os.path.dirname(stored_path)):
            logger.info(f"Using stored configuration path: {stored_path}")
            return stored_path
    
    # Priority 4: Platform-specific default
    default_path = get_default_storage_path()
    logger.info(f"Using platform default storage path: {default_path}")
    return default_path


def is_development_mode() -> bool:
    """
    Detect if application is running in development mode
    
    Returns:
        bool: True if in development mode
    """
    # Check for common development indicators
    dev_indicators = [
        # Running from source directory structure
        'eto_server/src' in os.path.abspath(__file__),
        # Environment variables
        os.getenv('FLASK_ENV') == 'development',
        os.getenv('FLASK_DEBUG') == '1',
        # Development server detection
        'flask' in sys.argv[0].lower() if sys.argv else False,
        'python' in sys.executable.lower(),
    ]
    
    is_dev = any(dev_indicators)
    logger.debug(f"Development mode detection: {is_dev} (indicators: {dev_indicators})")
    return is_dev


def get_fallback_storage() -> str:
    """
    Get fallback storage location if primary fails
    
    Returns:
        str: Fallback storage path
    """
    # Use temp directory as absolute fallback
    fallback_path = os.path.join(tempfile.gettempdir(), 'eto_system', 'pdf_storage')
    logger.info(f"Using fallback storage path: {fallback_path}")
    return fallback_path


def setup_first_run_storage() -> str:
    """
    Setup storage on first application run
    
    Returns:
        str: Configured storage path
        
    Raises:
        Exception: If storage setup fails completely
    """
    storage_path = get_storage_configuration()
    
    try:
        # Test storage location by creating directory and test file
        os.makedirs(storage_path, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(storage_path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.unlink(test_file)
        
        # Save successful configuration for future runs
        config = {
            'pdf_storage_root': storage_path,
            'first_run_completed': True,
            'configured_at': datetime.now().isoformat(),
            'platform': platform.system()
        }
        
        save_app_config(config)
        
        logger.info(f"First-run storage setup completed successfully: {storage_path}")
        return storage_path
        
    except PermissionError as e:
        logger.error(f"Permission denied creating storage directory: {storage_path}")
        fallback_path = get_fallback_storage()
        
        # Try fallback location
        try:
            os.makedirs(fallback_path, exist_ok=True)
            logger.info(f"Using fallback storage location: {fallback_path}")
            return fallback_path
        except Exception as fallback_error:
            logger.error(f"Fallback storage setup also failed: {fallback_error}")
            raise Exception(f"Unable to create storage directory. Tried: {storage_path}, {fallback_path}")
            
    except Exception as e:
        logger.error(f"Storage setup failed: {e}")
        raise Exception(f"Failed to setup storage at {storage_path}: {e}")


def validate_storage_path(path: str) -> bool:
    """
    Validate that a storage path is usable
    
    Args:
        path: Storage path to validate
        
    Returns:
        bool: True if path is valid and writable
    """
    try:
        # Check if path exists or can be created
        os.makedirs(path, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(path, '.permission_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.unlink(test_file)
        
        return True
        
    except Exception as e:
        logger.debug(f"Storage path validation failed for {path}: {e}")
        return False