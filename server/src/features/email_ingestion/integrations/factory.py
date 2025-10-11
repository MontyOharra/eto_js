"""
Email Integration Factory
Factory for creating email integration instances based on provider type
"""
import logging
from typing import Dict, Any

from shared.types import (
    EmailProvider,
    EmailIntegrationConfig,
    OutlookComConfig,
    GmailApiConfig,
    ImapConfig
)
from .base_integration import BaseEmailIntegration

logger = logging.getLogger(__name__)


class EmailIntegrationFactory:
    """Factory for creating email integration instances"""
    
    @staticmethod
    def create_integration(config: EmailIntegrationConfig) -> BaseEmailIntegration:
        """
        Create integration instance based on configuration type
        
        Args:
            config: Pydantic configuration model
            
        Returns:
            Appropriate integration instance
            
        Raises:
            ValueError: If configuration type is not supported
        """
        if isinstance(config, OutlookComConfig):
            from .outlook_com import OutlookComIntegration
            logger.info("Creating Outlook COM integration")
            return OutlookComIntegration(config)
            
        elif isinstance(config, GmailApiConfig):
            # Future implementation
            raise NotImplementedError("Gmail API integration not yet implemented")
            # from .gmail_api import GmailApiIntegration
            # return GmailApiIntegration(config)
            
        elif isinstance(config, ImapConfig):
            # Future implementation
            raise NotImplementedError("Generic IMAP integration not yet implemented")
            # from .imap_generic import ImapGenericIntegration
            # return ImapGenericIntegration(config)
            
        else:
            raise ValueError(f"Unsupported configuration type: {type(config).__name__}")
    
    @staticmethod
    def create_from_dict(provider_type: str, config_dict: Dict[str, Any]) -> BaseEmailIntegration:
        """
        Create integration from provider type string and configuration dictionary
        
        Args:
            provider_type: Provider type string (e.g., "outlook_com", "gmail_api")
            config_dict: Configuration dictionary with provider-specific settings
            
        Returns:
            Appropriate integration instance
            
        Raises:
            ValueError: If provider type is not recognized
        """
        # Ensure provider_type is in config_dict
        config_dict['provider_type'] = provider_type
        
        if provider_type == EmailProvider.OUTLOOK_COM.value:
            config = OutlookComConfig(**config_dict)
            
        elif provider_type == EmailProvider.GMAIL_API.value:
            config = GmailApiConfig(**config_dict)
            
        elif provider_type == EmailProvider.IMAP_GENERIC.value:
            config = ImapConfig(**config_dict)
            
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        return EmailIntegrationFactory.create_integration(config)
    
    @staticmethod
    def get_supported_providers() -> Dict[str, Dict[str, Any]]:
        """
        Get information about supported email providers
        
        Returns:
            Dictionary with provider information
        """
        return {
            EmailProvider.OUTLOOK_COM.value: {
                "name": "Microsoft Outlook (Local)",
                "description": "Connect to locally installed Microsoft Outlook using COM interface",
                "requires_local_install": True,
                "supported_platforms": ["windows"],
                "authentication": "Uses existing Outlook profile",
                "implemented": True
            },
            EmailProvider.GMAIL_API.value: {
                "name": "Gmail API",
                "description": "Connect to Gmail using Google's API with OAuth2",
                "requires_local_install": False,
                "supported_platforms": ["windows", "mac", "linux"],
                "authentication": "OAuth2",
                "implemented": False
            },
            EmailProvider.IMAP_GENERIC.value: {
                "name": "Generic IMAP",
                "description": "Connect to any email provider supporting IMAP protocol",
                "requires_local_install": False,
                "supported_platforms": ["windows", "mac", "linux"],
                "authentication": "Username/Password",
                "implemented": False
            },
            EmailProvider.OUTLOOK_GRAPH.value: {
                "name": "Microsoft Graph API",
                "description": "Connect to Microsoft 365/Outlook.com using Graph API",
                "requires_local_install": False,
                "supported_platforms": ["windows", "mac", "linux"],
                "authentication": "OAuth2",
                "implemented": False
            },
            EmailProvider.EXCHANGE.value: {
                "name": "Exchange Web Services",
                "description": "Connect to Exchange Server using EWS protocol",
                "requires_local_install": False,
                "supported_platforms": ["windows", "mac", "linux"],
                "authentication": "Username/Password or OAuth2",
                "implemented": False
            }
        }
    
    @staticmethod
    def create_default_config(provider_type: str) -> EmailIntegrationConfig:
        """
        Create a default configuration for the specified provider
        
        Args:
            provider_type: Provider type string
            
        Returns:
            Default configuration for the provider
            
        Raises:
            ValueError: If provider type is not recognized
        """
        if provider_type == EmailProvider.OUTLOOK_COM.value:
            return OutlookComConfig(
                provider_type=EmailProvider.OUTLOOK_COM,
                account_identifier=None,  # Will use default account
                default_folder="Inbox"
            )
            
        elif provider_type == EmailProvider.GMAIL_API.value:
            return GmailApiConfig(
                provider_type=EmailProvider.GMAIL_API,
                credentials_path="credentials.json",
                token_path="token.json",
                account_identifier=None
            )
            
        elif provider_type == EmailProvider.IMAP_GENERIC.value:
            return ImapConfig(
                provider_type=EmailProvider.IMAP_GENERIC,
                server="imap.example.com",
                port=993,
                username="",
                password="",
                use_ssl=True,
                account_identifier=None
            )
            
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")