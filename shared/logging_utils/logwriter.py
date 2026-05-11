"""Log writer for structured logging"""
import logging
import sys

class LogWriter:
    """Simple log writer with structured output."""
    
    def __init__(self):
        self.logger = logging.getLogger("shadow_network")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        extra = " ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""
        self.logger.info(f"{message} {extra}".strip())
    
    def error(self, message: str, **kwargs):
        extra = " ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""
        self.logger.error(f"{message} {extra}".strip())
    
    def warning(self, message: str, **kwargs):
        extra = " ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""
        self.logger.warning(f"{message} {extra}".strip())

_log_writer = LogWriter()

def info(message: str, **kwargs):
    _log_writer.info(message, **kwargs)

def error(message: str, **kwargs):
    _log_writer.error(message, **kwargs)

def warning(message: str, **kwargs):
    _log_writer.warning(message, **kwargs)
