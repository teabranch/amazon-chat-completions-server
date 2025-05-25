import logging
from typing import Optional, Dict, Any
import os
from functools import lru_cache

from .llm_service_abc import AbstractLLMService
from ..adapters.base_adapter import BaseLLMAdapter
from ..adapters.openai_adapter import OpenAIAdapter
from ..adapters.bedrock.bedrock_adapter import BedrockAdapter
from ..adapters.bedrock.bedrock_models import get_bedrock_model_id, SUPPORTED_BEDROCK_MODELS
from ..core.exceptions import ModelNotFoundError, ConfigurationError
from .openai_service import OpenAIService
from .bedrock_service import BedrockService
# Import BedrockService once it's created
# from .bedrock_service import BedrockService 

logger = logging.getLogger(__name__)

# In-memory cache for service instances to avoid re-initializing adapters for the same model.
# Key: (provider_name, model_id_or_key_for_provider, frozenset(kwargs.items()))
_service_cache: Dict[tuple, AbstractLLMService] = {}

class LLMServiceFactory:
    """Factory for creating LLM service instances."""

    @staticmethod
    @lru_cache(maxsize=None) # Cache service instances for efficiency
    def get_service(provider_name: str, model_id: Optional[str] = None, **kwargs: Any) -> AbstractLLMService:
        """
        Gets an LLM service instance for the specified provider and model.

        Args:
            provider_name: Name of the LLM provider (e.g., "openai", "bedrock").
            model_id: The specific model ID to use. 
                      For OpenAI, this is the model name (e.g., "gpt-4-turbo").
                      For Bedrock, this can be a generic name (e.g., "claude-3-sonnet") 
                      or a specific Bedrock model ID (e.g., "anthropic.claude-3-sonnet-20240229-v1:0").
            **kwargs: Additional configuration arguments to pass to the adapter/service initialization.
                      These could include provider-specific parameters like `aws_region` (though region is usually from config)
                      or common ones like `temperature` if they are to be fixed for the service instance.

        Returns:
            An instance of a class that implements AbstractLLMService.

        Raises:
            ModelNotFoundError: If the provider or model is not supported.
            ConfigurationError: If essential configurations are missing for the provider.
        """
        provider_name_lower = provider_name.lower()
        logger.info(f"LLMServiceFactory: Requesting service for provider '{provider_name_lower}', model '{model_id}'.")

        if provider_name_lower == "openai":
            logger.debug(f"Creating/getting OpenAIService. Passed kwargs: {kwargs}")
            return OpenAIService(**kwargs)
        
        elif provider_name_lower == "bedrock":
            logger.debug(f"Creating/getting BedrockService. Passed kwargs: {kwargs}")
            return BedrockService(**kwargs) 
            
        else:
            # This part is from the original factory file, attempting to use an adapter pattern.
            # It seems to expect local imports of "concrete_services" and adapters.
            # If a provider other than "openai" or "bedrock" is requested, it might hit this.
            logger.info(f"Provider '{provider_name_lower}' not 'openai' or 'bedrock', falling back to original factory logic if applicable.")
            
            # The following is based on the original structure seen in the file before my changes.
            # It requires `_service_cache` and specific adapter/service classes that might not all be present
            # or fully compatible with the AbstractLLMService I'm using for OpenAI/Bedrock directly.
            cache_key_model_id = model_id if model_id else provider_name_lower
            cache_key_kwargs = frozenset(kwargs.items())
            cache_key = (provider_name_lower, cache_key_model_id, cache_key_kwargs)

            if cache_key in _service_cache:
                logger.debug(f"Returning cached LLM service (original cache) for {provider_name_lower} - {cache_key_model_id}")
                return _service_cache[cache_key]

            logger.info(f"Creating new LLM service (original factory path) for provider: {provider_name_lower}, model: {model_id}, kwargs: {kwargs}")

            service_instance: Optional[AbstractLLMService] = None
            adapter_instance: Optional[Any] = None # Original type was BaseLLMAdapter

            # This section needs to be restored with actual adapter/service imports from original design if used
            if provider_name_lower == "openai_adapter_path": # Example of how original might have been structured
                if not model_id:
                    raise ModelNotFoundError("model_id is required for OpenAI provider (adapter path).")
                from .concrete_services import OpenAIService as ConcreteOpenAIService # Assuming this was the structure
                from ..adapters.openai_adapter import OpenAIAdapter
                adapter_instance = OpenAIAdapter(model_id=model_id, **kwargs)
                service_instance = ConcreteOpenAIService(adapter=adapter_instance) # This service would take an adapter

            elif provider_name_lower == "bedrock_adapter_path": # Example
                if not model_id:
                    raise ModelNotFoundError("model_id is required for Bedrock provider (adapter path).")
                from .concrete_services import BedrockService as ConcreteBedrockService 
                from ..adapters.bedrock.bedrock_adapter import BedrockAdapter
                adapter_instance = BedrockAdapter(model_id=model_id, **kwargs)
                service_instance = ConcreteBedrockService(adapter=adapter_instance)
            
            else:
                raise ModelNotFoundError(f"Unsupported LLM provider in factory's original logic path: {provider_name_lower}")

            if service_instance:
                _service_cache[cache_key] = service_instance
                return service_instance
            else:
                raise ConfigurationError(f"Failed to create service instance (original factory path) for {provider_name_lower} with model {model_id}")

    @staticmethod
    def clear_cache():
        """Clears the service instance cache."""
        global _service_cache
        _service_cache = {}
        logger.info("LLMServiceFactory cache cleared.")

    @staticmethod
    def get_service_for_model(model_id: str, **kwargs: Any) -> AbstractLLMService:
        """
        Determines the provider from the model_id and returns the appropriate service.
        This is a heuristic and might need a more robust model-to-provider mapping.
        kwargs are passed to the underlying get_service call.
        """
        logger.info(f"LLMServiceFactory: Requesting service for model_id '{model_id}'.")
        # Simple heuristic (expand this list or use a more robust mapping)
        # Ensure this list is comprehensive for known model prefixes/patterns.
        
        provider = None
        model_id_parts = model_id.split('.')

        if model_id.startswith("gpt-") or \
           model_id.startswith("text-") or \
           "openai" in model_id.lower() or \
           model_id in ["dall-e-2", "dall-e-3"]: # Example specific OpenAI models
            provider = "openai"
        elif model_id.startswith("anthropic.") or \
             model_id.startswith("ai21.") or \
             model_id.startswith("cohere.") or \
             model_id.startswith("amazon.") or \
             model_id.startswith("meta.") or \
             "bedrock" in model_id.lower():
            provider = "bedrock"
        elif len(model_id_parts) > 1 and model_id_parts[1] in ["anthropic", "ai21", "cohere", "amazon", "meta"]:
            # Handles cases like 'us.anthropic.claude...' or ARNs that might include these
            provider = "bedrock"
        
        if provider is None:
            # Fallback or error if provider cannot be determined
            logger.warning(
                f"Could not reliably determine provider for model '{model_id}'. Attempting to use 'openai' as a default. This may fail."
            )
            # Defaulting to OpenAI can be risky. Consider raising an error or having a configurable default provider.
            # For now, let's try OpenAI and let it fail if the model is incompatible.
            provider = "openai" 
            # raise ValueError(f"Could not determine provider for model ID: {model_id}. Please specify provider explicitly.")

        logger.debug(f"Determined provider '{provider}' for model '{model_id}'.")
        return LLMServiceFactory.get_service(provider, model_id=model_id, **kwargs)

# Example of how Concrete Services would make this cleaner:
# if provider_name == "openai":
#     if not model_id:
#         raise ModelNotFoundError("model_id is required for OpenAI provider.")
#     from .concrete_services import OpenAIService # Local import
#     adapter = OpenAIAdapter(model_id=model_id, **kwargs)
#     service_instance = OpenAIService(adapter=adapter)
# elif provider_name == "bedrock":
#     if not model_id:
#         raise ModelNotFoundError("model_id is required for Bedrock provider.")
#     from .concrete_services import BedrockService # Local import
#     adapter = BedrockAdapter(model_id=model_id, **kwargs)
#     service_instance = BedrockService(adapter=adapter) 

# Example how settings might influence this (e.g., from a config file or env vars)
# class ConfiguredLLMServiceFactory:
#     def __init__(self, settings: AppSettings):
#         self.settings = settings 
#         self._openai_api_key = settings.OPENAI_API_KEY
#         # ... load other settings for AWS etc.

#     @lru_cache(maxsize=None)
#     def get_service(self, provider_name: str) -> BaseLLMService:
#         if provider_name == "openai":
#             return OpenAIService(api_key=self._openai_api_key)
#         # ... etc.
#         raise ValueError("Unsupported provider") 