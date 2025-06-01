import logging
import os

def get_user_logger(username):
    """Tạo logger cho user"""
    logger = logging.getLogger(username)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f'logs/{username}.log', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger 