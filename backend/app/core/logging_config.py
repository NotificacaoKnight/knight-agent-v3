"""
Logging configuration for the application
Includes fix for uvicorn process ID formatting issue
"""
import logging
import sys
from logging import LogRecord


class UvicornLogFilter(logging.Filter):
    """
    Filter to fix uvicorn's process ID formatting issue
    Converts string process IDs to integers where needed
    """

    def filter(self, record: LogRecord) -> bool:
        # Fix the specific "Started server process [%d]" error
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, tuple):
                # Convert string process IDs to integers
                fixed_args = []
                for arg in record.args:
                    if isinstance(arg, str) and arg.isdigit():
                        fixed_args.append(int(arg))
                    else:
                        fixed_args.append(arg)
                record.args = tuple(fixed_args)
        return True


def configure_logging():
    """Configure logging for the application"""
    # Get uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")

    # Add our filter to fix the process ID issue
    log_filter = UvicornLogFilter()

    # Apply filter to all uvicorn handlers
    for handler in uvicorn_logger.handlers:
        handler.addFilter(log_filter)

    for handler in uvicorn_access_logger.handlers:
        handler.addFilter(log_filter)

    # Also apply to root logger to catch any other instances
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(log_filter)

    # Configure our application logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce noise from some libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logging.getLogger(__name__)