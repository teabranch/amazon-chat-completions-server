import logging
from typing import Any

from ..core.bedrock_models import RequestFormat

logger = logging.getLogger(__name__)


class RequestFormatDetector:
    """Utility class for detecting the format of incoming requests"""

    @staticmethod
    def detect_format(request_data: dict[str, Any]) -> RequestFormat:
        """
        Detect the format of incoming request based on its structure and fields.

        Priority order:
        1. Bedrock Claude (most specific indicators)
        2. Bedrock Titan (specific indicators)
        3. OpenAI (default for common patterns)
        4. Unknown (if no patterns match)
        """
        if not request_data:
            return RequestFormat.UNKNOWN

        # Check for Bedrock Claude format first (highest priority due to specificity)
        if RequestFormatDetector.is_bedrock_claude_format(request_data):
            return RequestFormat.BEDROCK_CLAUDE

        # Check for Bedrock Titan format
        if RequestFormatDetector.is_bedrock_titan_format(request_data):
            return RequestFormat.BEDROCK_TITAN

        # Check for OpenAI format
        if RequestFormatDetector.is_openai_format(request_data):
            return RequestFormat.OPENAI

        # If we have messages but no clear format indicators, default to OpenAI
        if "messages" in request_data and isinstance(request_data["messages"], list):
            logger.debug("Ambiguous format detected, defaulting to OpenAI")
            return RequestFormat.OPENAI

        return RequestFormat.UNKNOWN

    @staticmethod
    def is_openai_format(request_data: dict[str, Any]) -> bool:
        """
        Check if request follows OpenAI Chat Completions format.

        Key indicators:
        - Has 'model' field
        - Has 'messages' field with list of message objects
        - Messages have 'role' and 'content' fields
        - Optional: tools with 'type' and 'function' structure
        """
        if not isinstance(request_data, dict):
            return False

        # Exclude clear Bedrock indicators
        if "anthropic_version" in request_data:
            return False
        if "inputText" in request_data and "textGenerationConfig" in request_data:
            return False

        # Strong OpenAI indicators
        has_model = "model" in request_data
        has_messages = "messages" in request_data and isinstance(
            request_data["messages"], list
        )

        # Check for OpenAI-specific tool format
        has_openai_tools = False
        if "tools" in request_data and isinstance(request_data["tools"], list):
            for tool in request_data["tools"]:
                if (
                    isinstance(tool, dict)
                    and tool.get("type") == "function"
                    and "function" in tool
                ):
                    has_openai_tools = True
                    break

        # OpenAI-specific parameters
        openai_params = {
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "stream",
            "logit_bias",
            "user",
        }
        has_openai_params = any(param in request_data for param in openai_params)

        # Must have model and messages for OpenAI format
        if has_model and has_messages:
            return True

        # If has messages and OpenAI-specific indicators but no model, still likely OpenAI
        return bool(has_messages and (has_openai_tools or has_openai_params))

    @staticmethod
    def is_bedrock_claude_format(request_data: dict[str, Any]) -> bool:
        """
        Check if request follows Bedrock Claude format.

        Key indicators:
        - Has 'anthropic_version' field
        - Has 'max_tokens' field (required in Claude)
        - Has 'messages' field
        - Optional: 'system' field for system prompt
        - Tools have 'name', 'description', 'input_schema' structure
        """
        if not isinstance(request_data, dict):
            return False

        # Strong Claude indicators
        has_anthropic_version = "anthropic_version" in request_data
        has_max_tokens = "max_tokens" in request_data
        has_messages = "messages" in request_data and isinstance(
            request_data["messages"], list
        )

        # Claude-specific fields
        claude_specific_fields = {"system", "top_k", "stop_sequences"}
        has_claude_fields = any(
            field in request_data for field in claude_specific_fields
        )

        # Check for Claude-specific tool format
        has_claude_tools = False
        if "tools" in request_data and isinstance(request_data["tools"], list):
            for tool in request_data["tools"]:
                if (
                    isinstance(tool, dict)
                    and "name" in tool
                    and "description" in tool
                    and "input_schema" in tool
                ):
                    has_claude_tools = True
                    break

        # Check for Claude-specific tool_choice format
        has_claude_tool_choice = False
        if "tool_choice" in request_data:
            tool_choice = request_data["tool_choice"]
            if isinstance(tool_choice, dict) and "type" in tool_choice:
                has_claude_tool_choice = True

        # anthropic_version is the strongest indicator
        if has_anthropic_version:
            return True

        # Combination of max_tokens + messages + Claude-specific features
        return bool(has_max_tokens and has_messages and (has_claude_fields or has_claude_tools or has_claude_tool_choice))

    @staticmethod
    def is_bedrock_titan_format(request_data: dict[str, Any]) -> bool:
        """
        Check if request follows Bedrock Titan format.

        Key indicators:
        - Has 'inputText' field
        - Has 'textGenerationConfig' field with Titan-specific structure
        """
        if not isinstance(request_data, dict):
            return False

        has_input_text = "inputText" in request_data
        has_text_gen_config = "textGenerationConfig" in request_data

        # Check textGenerationConfig structure
        valid_config = False
        if has_text_gen_config:
            config = request_data["textGenerationConfig"]
            if isinstance(config, dict):
                # Check for Titan-specific config fields
                titan_config_fields = {
                    "maxTokenCount",
                    "temperature",
                    "topP",
                    "stopSequences",
                }
                if "maxTokenCount" in config or any(
                    field in config for field in titan_config_fields
                ):
                    valid_config = True

        return has_input_text and valid_config

    @staticmethod
    def get_format_confidence(
        request_data: dict[str, Any],
    ) -> dict[RequestFormat, float]:
        """
        Get confidence scores for each format type.
        Useful for debugging and logging.
        """
        if not isinstance(request_data, dict):
            return dict.fromkeys(RequestFormat, 0.0)

        confidence = {
            RequestFormat.OPENAI: 0.0,
            RequestFormat.BEDROCK_CLAUDE: 0.0,
            RequestFormat.BEDROCK_TITAN: 0.0,
            RequestFormat.UNKNOWN: 0.0,
        }

        # OpenAI confidence scoring
        if "model" in request_data:
            confidence[RequestFormat.OPENAI] += 0.4
        if "messages" in request_data:
            confidence[RequestFormat.OPENAI] += 0.3
        if any(
            param in request_data for param in ["temperature", "max_tokens", "top_p"]
        ):
            confidence[RequestFormat.OPENAI] += 0.2
        if "tools" in request_data and isinstance(request_data.get("tools"), list):
            tools = request_data["tools"]
            if (
                tools
                and isinstance(tools[0], dict)
                and tools[0].get("type") == "function"
            ):
                confidence[RequestFormat.OPENAI] += 0.1

        # Claude confidence scoring
        if "anthropic_version" in request_data:
            confidence[RequestFormat.BEDROCK_CLAUDE] += 0.5
        if "max_tokens" in request_data and "messages" in request_data:
            confidence[RequestFormat.BEDROCK_CLAUDE] += 0.3
        if "system" in request_data:
            confidence[RequestFormat.BEDROCK_CLAUDE] += 0.1
        if "tools" in request_data and isinstance(request_data.get("tools"), list):
            tools = request_data["tools"]
            if tools and isinstance(tools[0], dict) and "input_schema" in tools[0]:
                confidence[RequestFormat.BEDROCK_CLAUDE] += 0.1

        # Titan confidence scoring
        if "inputText" in request_data:
            confidence[RequestFormat.BEDROCK_TITAN] += 0.5
        if "textGenerationConfig" in request_data:
            config = request_data["textGenerationConfig"]
            if isinstance(config, dict) and "maxTokenCount" in config:
                confidence[RequestFormat.BEDROCK_TITAN] += 0.5

        # Normalize confidence scores to max 1.0
        for format_type in confidence:
            confidence[format_type] = min(confidence[format_type], 1.0)

        # If no format has high confidence, mark as unknown
        max_confidence = max(confidence.values())
        if max_confidence < 0.5:
            confidence[RequestFormat.UNKNOWN] = 1.0 - max_confidence

        return confidence
