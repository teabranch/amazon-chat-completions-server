import asyncio
import logging

from .core.exceptions import ConfigurationError, LLMIntegrationError
from .core.models import Message
from .services.llm_service_factory import LLMServiceFactory

# Ensure logger_setup and config_loader are imported early if they do global setup.
# The logger_setup already calls setup_logging() on import.
from .utils import config_loader

# Logger for this main module
logger = logging.getLogger(__name__)  # Gets the logger configured by logger_setup


async def run_openai_example():
    logger.info("--- Running OpenAI Example ---")
    if not config_loader.app_config.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured. Skipping OpenAI example.")
        return
    try:
        # Get the service for a specific OpenAI model
        # openai_service = LLMServiceFactory.get_service("openai", model_id="gpt-3.5-turbo-instruct") # Example for completions model
        openai_service = LLMServiceFactory.get_service(
            "openai", model_id="gpt-4o-mini"
        )  # Chat model

        messages = [
            Message(role="system", content="You are a helpful and concise assistant."),
            Message(role="user", content="Hello! What is the capital of France?"),
        ]

        # Non-streaming example
        logger.info("OpenAI Non-Streaming Request:")
        response = await openai_service.chat_completion(
            model_id="gpt-4o-mini", messages=messages, max_tokens=50
        )
        if response.choices and response.choices[0].message:
            logger.info(
                f"OpenAI Response (Non-Stream): {response.choices[0].message.content}"
            )
            logger.info(f"OpenAI Usage: {response.usage}")
        else:
            logger.error("OpenAI Non-Stream response had no choices or message.")

        # Streaming example
        logger.info("\nOpenAI Streaming Request:")
        full_streamed_content = ""
        async for chunk in await openai_service.chat_completion(
            model_id="gpt-4o-mini", messages=messages, max_tokens=60, stream=True
        ):
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                print(chunk.choices[0].delta.content, end="", flush=True)
                full_streamed_content += chunk.choices[0].delta.content
            if chunk.choices and chunk.choices[0].finish_reason:
                logger.info(
                    f"\nOpenAI Stream finished. Reason: {chunk.choices[0].finish_reason}"
                )
        logger.info(f"\nFull OpenAI Streamed Content: {full_streamed_content}")

    except ConfigurationError as e:
        logger.error(f"OpenAI Configuration Error: {e}")
    except LLMIntegrationError as e:
        logger.error(f"OpenAI LLM Integration Error: {e}")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during OpenAI example: {e}", exc_info=True
        )


async def run_bedrock_claude_example():
    logger.info("\n--- Running Bedrock Claude Example ---")
    if not (
        config_loader.app_config.AWS_ACCESS_KEY_ID
        and config_loader.app_config.AWS_SECRET_ACCESS_KEY
    ):
        logger.warning(
            "AWS credentials not configured. Skipping Bedrock Claude example."
        )
        return
    try:
        # model_id can be generic like "us.anthropic.claude-3-5-haiku-20241022-v1:0" or specific like "anthropic.us.anthropic.claude-3-5-haiku-20241022-v1:0-20240307-v1:0"
        bedrock_claude_service = LLMServiceFactory.get_service(
            "bedrock", model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0"
        )

        messages = [
            Message(
                role="system",
                content="You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.",
            ),
            Message(
                role="user",
                content="Compose a short poem about asynchronous programming.",
            ),
        ]

        # Non-streaming example
        logger.info("Bedrock Claude Non-Streaming Request:")
        response = await bedrock_claude_service.chat_completion(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        if response.choices and response.choices[0].message:
            logger.info(
                f"Bedrock Claude Response (Non-Stream):\n{response.choices[0].message.content}"
            )
            logger.info(f"Bedrock Claude Usage: {response.usage}")
        else:
            logger.error(
                "Bedrock Claude Non-Stream response had no choices or message."
            )

        # Streaming example
        logger.info("\nBedrock Claude Streaming Request:")
        full_streamed_content = ""
        async for chunk in await bedrock_claude_service.chat_completion(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            messages=messages,
            max_tokens=160,
            temperature=0.7,
            stream=True,
        ):
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                print(chunk.choices[0].delta.content, end="", flush=True)
                full_streamed_content += chunk.choices[0].delta.content
            if chunk.choices and chunk.choices[0].finish_reason:
                logger.info(
                    f"\nBedrock Claude Stream finished. Reason: {chunk.choices[0].finish_reason}"
                )
        logger.info(f"\nFull Bedrock Claude Streamed Content:\n{full_streamed_content}")

    except ConfigurationError as e:
        logger.error(f"Bedrock Claude Configuration Error: {e}")
    except LLMIntegrationError as e:
        logger.error(f"Bedrock Claude LLM Integration Error: {e}")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during Bedrock Claude example: {e}",
            exc_info=True,
        )


async def run_bedrock_titan_example():
    logger.info("\n--- Running Bedrock Titan Example ---")
    if not (
        config_loader.app_config.AWS_ACCESS_KEY_ID
        and config_loader.app_config.AWS_SECRET_ACCESS_KEY
    ):
        logger.warning(
            "AWS credentials not configured. Skipping Bedrock Titan example."
        )
        return
    try:
        bedrock_titan_service = LLMServiceFactory.get_service(
            "bedrock", model_id="amazon.titan-text-express-v1"
        )

        messages = [
            # Titan strategy formats system prompt as part of inputText
            Message(role="system", content="You are a factual and historical expert."),
            Message(
                role="user",
                content="When was the first programmable computer invented?",
            ),
        ]

        # Non-streaming example
        logger.info("Bedrock Titan Non-Streaming Request:")
        response = await bedrock_titan_service.chat_completion(
            model_id="amazon.titan-text-express-v1", messages=messages, max_tokens=100
        )
        if response.choices and response.choices[0].message:
            logger.info(
                f"Bedrock Titan Response (Non-Stream): {response.choices[0].message.content}"
            )
            logger.info(f"Bedrock Titan Usage: {response.usage}")
        else:
            logger.error("Bedrock Titan Non-Stream response had no choices or message.")

        # Streaming example
        logger.info("\nBedrock Titan Streaming Request:")
        full_streamed_content = ""
        async for chunk in await bedrock_titan_service.chat_completion(
            model_id="amazon.titan-text-express-v1",
            messages=messages,
            max_tokens=120,
            stream=True,
        ):
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                print(chunk.choices[0].delta.content, end="", flush=True)
                full_streamed_content += chunk.choices[0].delta.content
            if chunk.choices and chunk.choices[0].finish_reason:
                logger.info(
                    f"\nBedrock Titan Stream finished. Reason: {chunk.choices[0].finish_reason}"
                )
        logger.info(f"\nFull Bedrock Titan Streamed Content: {full_streamed_content}")

    except ConfigurationError as e:
        logger.error(f"Bedrock Titan Configuration Error: {e}")
    except LLMIntegrationError as e:
        logger.error(f"Bedrock Titan LLM Integration Error: {e}")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during Bedrock Titan example: {e}",
            exc_info=True,
        )


async def main():
    # BasicConfig is done in logger_setup.py, but if running this file directly and logger_setup isn't imported elsewhere first,
    # you might need a basicConfig here. However, logger_setup is imported, so it should be fine.
    # logging.basicConfig(level=config_loader.app_config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Starting LLM Integration Examples...")

    # Run examples sequentially
    await run_openai_example()
    await run_bedrock_claude_example()
    await run_bedrock_titan_example()

    logger.info("\nLLM Integration Examples Finished.")


if __name__ == "__main__":
    # To run this main.py directly for testing:
    # Ensure you are in the project root directory and run:
    # python -m src.open_bedrock_server.main
    # Make sure .env file is in the project root.
    asyncio.run(main())
