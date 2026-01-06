"""
Email Integration Registry
Registry pattern for managing email provider integrations
Replaces factory pattern with self-registering providers
"""
import logging
from typing import Type

from .base_integration import BaseEmailIntegration

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """
    Registry for email integration providers.

    Providers self-register using the @IntegrationRegistry.register() decorator.
    This pattern allows:
    - Adding new providers without modifying this file (Open/Closed Principle)
    - Dynamic discovery of available providers
    - Decoupled provider implementations
    - Plugin-style architecture

    Example usage:
        @IntegrationRegistry.register("outlook_com")
        class OutlookComIntegration(BaseEmailIntegration):
            def __init__(self, email_address: str | None = None, folder_name: str = "Inbox"):
                # ...

        # Create instance
        integration = IntegrationRegistry.create(
            provider_type="outlook_com",
            email_address="test@example.com",
            folder_name="Inbox"
        )
    """

    # Class-level registry mapping provider_type -> integration class
    _integrations: dict[str, Type[BaseEmailIntegration]] = {}

    # Provider metadata for discovery and UI
    _metadata: dict[str, dict] = {}

    @classmethod
    def register(cls, provider_type: str, **metadata):
        """
        Decorator to register an integration implementation.

        Args:
            provider_type: Unique identifier for this provider (e.g., "outlook_com", "gmail_api")
            **metadata: Optional metadata about the provider (name, description, etc.)

        Returns:
            Decorator function that registers the class

        Example:
            @IntegrationRegistry.register(
                "outlook_com",
                name="Microsoft Outlook (Local)",
                description="Connect to locally installed Outlook",
                requires_local_install=True,
                platforms=["windows"]
            )
            class OutlookComIntegration(BaseEmailIntegration):
                pass
        """
        def decorator(integration_class: Type):
            if provider_type in cls._integrations:
                logger.warning(
                    f"Provider '{provider_type}' is already registered. "
                    f"Overwriting with {integration_class.__name__}"
                )

            cls._integrations[provider_type] = integration_class
            cls._metadata[provider_type] = metadata

            logger.debug(
                f"Registered email integration provider: {provider_type} "
                f"({integration_class.__name__})"
            )

            return integration_class

        return decorator

    @classmethod
    def create(cls, provider_type: str, **config) -> BaseEmailIntegration:
        """
        Create an integration instance by provider type.

        Args:
            provider_type: The provider to create (e.g., "outlook_com")
            **config: Configuration parameters passed to the integration constructor

        Returns:
            Instance of the integration class (BaseEmailIntegration subclass)

        Raises:
            ValueError: If provider_type is not registered

        Example:
            integration = IntegrationRegistry.create(
                provider_type="outlook_com",
                email_address="user@example.com",
                folder_name="Inbox"
            )
        """
        integration_class = cls._integrations.get(provider_type)

        if not integration_class:
            available = ', '.join(cls.get_available_providers())
            raise ValueError(
                f"Unknown email provider '{provider_type}'. "
                f"Available providers: {available or 'none'}"
            )

        logger.debug(f"Creating integration for provider: {provider_type}")

        try:
            return integration_class(**config)
        except TypeError as e:
            logger.error(
                f"Failed to create integration '{provider_type}' with config: {config}. "
                f"Error: {e}"
            )
            raise ValueError(
                f"Invalid configuration for provider '{provider_type}': {e}"
            ) from e

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        Get list of all registered provider types.

        Returns:
            List of provider type strings

        Example:
            providers = IntegrationRegistry.get_available_providers()
            # ['outlook_com', 'gmail_api', 'imap']
        """
        return list(cls._integrations.keys())

    @classmethod
    def is_supported(cls, provider_type: str) -> bool:
        """
        Check if a provider type is supported (registered).

        Args:
            provider_type: Provider type to check

        Returns:
            True if provider is registered

        Example:
            if IntegrationRegistry.is_supported("outlook_com"):
                # ...
        """
        return provider_type in cls._integrations

    @classmethod
    def get_provider_metadata(cls, provider_type: str) -> dict | None:
        """
        Get metadata for a specific provider.

        Args:
            provider_type: Provider type to get metadata for

        Returns:
            Dictionary of metadata or None if provider not found

        Example:
            metadata = IntegrationRegistry.get_provider_metadata("outlook_com")
            # {'name': 'Microsoft Outlook', 'platforms': ['windows'], ...}
        """
        return cls._metadata.get(provider_type)

    @classmethod
    def get_all_provider_info(cls) -> dict[str, dict]:
        """
        Get information about all registered providers.

        Returns:
            Dictionary mapping provider_type to metadata

        Example:
            providers = IntegrationRegistry.get_all_provider_info()
            for provider_type, info in providers.items():
                print(f"{provider_type}: {info.get('name')}")
        """
        result = {}
        for provider_type in cls._integrations.keys():
            result[provider_type] = {
                'class_name': cls._integrations[provider_type].__name__,
                **(cls._metadata.get(provider_type) or {})
            }
        return result

    @classmethod
    def clear_registry(cls):
        """
        Clear all registered providers.
        Primarily used for testing.
        """
        cls._integrations.clear()
        cls._metadata.clear()
        logger.debug("Cleared integration registry")
