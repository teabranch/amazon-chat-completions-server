# Mapping of generic model identifiers to specific Bedrock model IDs
# This can be expanded or loaded from a configuration file.

BEDROCK_MODEL_ID_MAP = {
    # Amazon Nova Models
    "nova-canvas": "amazon.nova-canvas-v1:0",
    "nova-lite": "amazon.nova-lite-v1:0",
    "nova-micro": "amazon.nova-micro-v1:0",
    "nova-premier": "amazon.nova-premier-v1:0",
    "nova-pro": "amazon.nova-pro-v1:0",
    "nova-reel": "amazon.nova-reel-v1:1",  # Latest version
    "nova-sonic": "amazon.nova-sonic-v1:0",
    # Amazon Titan Models
    "titan-embed-text": "amazon.titan-embed-text-v1",
    "titan-image-gen-v2": "amazon.titan-image-generator-v2:0",
    "titan-multimodal-embed": "amazon.titan-embed-image-v1",
    # Amazon Rerank Models
    "rerank": "amazon.rerank-v1:0",
    # AI21 Labs Models
    "jamba-large": "ai21.jamba-1-5-large-v1:0",
    "jamba-mini": "ai21.jamba-1-5-mini-v1:0",
    # Anthropic Claude Models
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0": "anthropic.us.anthropic.claude-3-5-haiku-20241022-v1:0-20240307-v1:0",
    "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    # Cohere Models
    "command": "cohere.command-text-v14",
    "command-light": "cohere.command-light-text-v14",
    # Meta Models
    "llama2-13b-chat": "meta.llama2-13b-chat-v1",
    "llama2-70b-chat": "meta.llama2-70b-chat-v1",
    # Mistral Models
    "mistral-large-2402": "mistral.mistral-large-2402-v1:0",
    "mistral-large-2407": "mistral.mistral-large-2407-v1:0",
    "mistral-small-2402": "mistral.mistral-small-2402-v1:0",
    "mixtral-8x7b": "mistral.mixtral-8x7b-instruct-v0:1",
    "pixtral-large": "mistral.pixtral-large-2502-v1:0",
    # Stability AI Models
    "sd3-5-large": "stability.sd3-5-large-v1:0",
    "stable-image-core": "stability.stable-image-core-v1:1",
    "stable-image-ultra": "stability.stable-image-ultra-v1:1",
    # Writer Models
    "palmyra-x4": "writer.palmyra-x4-v1:0",
    "palmyra-x5": "writer.palmyra-x5-v1:0",
}


def get_bedrock_model_id(generic_model_name: str) -> str:
    """Returns the specific Bedrock model ID for a generic name."""
    return BEDROCK_MODEL_ID_MAP.get(generic_model_name, generic_model_name)


# Default parameters for different model families
def get_claude_default_params():
    return {
        "max_tokens": 4096,  # Updated for Claude 3
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 250,
    }


def get_nova_default_params():
    return {"maxTokens": 4096, "temperature": 0.7, "topP": 0.9, "stopSequences": []}


def get_mistral_default_params():
    return {"max_tokens": 4096, "temperature": 0.7, "top_p": 0.9}


SUPPORTED_BEDROCK_MODELS = list(BEDROCK_MODEL_ID_MAP.keys()) + list(
    BEDROCK_MODEL_ID_MAP.values()
)
