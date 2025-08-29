import logging
import logging.handlers

# Uvicorn's default format for access logs, with slight modification for clarity
# See: https://github.com/encode/uvicorn/blob/master/uvicorn/logging.py
ACCESS_LOG_FORMAT = '%(levelname)s: %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s'

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False, # Keep existing loggers like uvicorn's
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelname)s:     %(asctime)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": ACCESS_LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file_app": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/app.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
        },
        "file_access": {
            "formatter": "access",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/access.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "": { # Root logger
            "handlers": ["default", "file_app"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False
        },
        "uvicorn.access": {
            "handlers": ["access", "file_access"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        }
    },
}