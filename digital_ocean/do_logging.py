# Renamed from logging.py to do_logging.py to avoid shadowing the standard library
import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

def get_logger(name="digital_ocean"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(LEVELS.get(LOG_LEVEL, logging.INFO))
    return logger

logger = get_logger()

def log_info_query_start():
    logger.info("[info/query] Starting info/query operation.")

def log_info_query_success(namespaces, domains, resources):
    logger.info(f"[info/query] Success. Namespaces: {namespaces}, Domains: {domains}, Resources: {resources}")

def log_info_query_error(error):
    logger.error(f"[info/query] Error: {error}")

def log_exec_start(target, command):
    logger.info(f"[exec] Starting exec on {target}: {command}")

def log_exec_success(target, command, result):
    logger.info(f"[exec] Success on {target}: {command} → {result}")

def log_exec_error(target, command, error):
    logger.error(f"[exec] Error on {target}: {command} → {error}")
