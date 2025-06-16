import logging
import sys

from .config_loader import app_config


def setup_logging():
    """Configures logging for the application."""
    log_level = getattr(logging, app_config.LOG_LEVEL, logging.INFO)

    # Basic configuration for the root logger
    # This will apply to all loggers unless they have specific handlers/formatters
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)  # Log to console
            # Add FileHandler here if needed for production:
            # logging.FileHandler("app.log"),
            # logging.handlers.RotatingFileHandler("app_rotated.log", maxBytes=1024*1024*5, backupCount=5) # 5MB per file, 5 backups
        ],
    )

    # Example of setting a specific logger's level (e.g., for a noisy library)
    # logging.getLogger("noisy_library_name").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {app_config.LOG_LEVEL}")


# Call setup_logging when this module is imported so logging is configured early.
setup_logging()

# To use in other modules:
# import logging
# logger = logging.getLogger(__name__)
# logger.info("This is an info message.")
# logger.debug("This is a debug message.")
