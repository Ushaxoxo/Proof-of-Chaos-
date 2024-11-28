import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name, log_file="blockchain.log", level=logging.INFO, max_bytes=5 * 1024 * 1024, backup_count=3):
   
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent duplicate logs if using root logger

    # Formatter for logs
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Log Helper Functions
def log_transaction(logger, transaction):
  
    logger.info(f"Transaction logged: {transaction}")

def log_block(logger, block):
 
    logger.info(f"Block created: Index {block.index}, Hash {block.hash}")

def log_entropy(logger, node_id, entropy):
  
    logger.debug(f"Node {node_id} generated entropy: {entropy}")

def log_error(logger, error_message):
  
    logger.error(f"Error occurred: {error_message}")

def safe_log(logger, level, message):

    if logger:
        getattr(logger, level)(message)
    else:
        getattr(default_logger, level)(message)