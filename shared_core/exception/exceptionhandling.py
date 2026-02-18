import sys
from typing import Optional

# To perform relative import of logger, we might need path adjustment if this is run as script
# But intended usage is library import.
# Assuming shared_core is in python path.

class CustomException(Exception):
    def __init__(self, error_message, error_detail:sys):
        super().__init__(error_message)
        self.error_message = CustomException.get_detailed_error_message(error_message=error_message, error_detail=error_detail)

    @staticmethod
    def get_detailed_error_message(error_message, error_detail:sys):
        _, _, exc_tb = error_detail.exc_info()
        file_name = exc_tb.tb_frame.f_code.co_filename
        error_message = "Error occurred in python script name [{0}] line number [{1}] error message [{2}]".format(
            file_name, exc_tb.tb_lineno, str(error_message))
        return error_message

    def __str__(self):
        return self.error_message

# Async or Sync types
from functools import wraps
from ..logger.logging import logger

def log_exceptions(func):
    """
    Decorator to handle and log exceptions for any function.
    """
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Raise as CustomException for detailed trace
                ce = CustomException(e, sys)
                logger.error(f"Exception in {func.__name__}: {ce}")
                raise ce
        return async_wrapper
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ce = CustomException(e, sys)
                logger.error(f"Exception in {func.__name__}: {ce}")
                raise ce
        return wrapper

import asyncio
