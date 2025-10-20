import logging
import logging.handlers
import os
from pathlib import Path

# Uvicorn's default format for access logs, with slight modification for clarity
# See: https://github.com/encode/uvicorn/blob/master/uvicorn/logging.py
ACCESS_LOG_FORMAT = '%(levelname)s: %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s'

def get_log_directory():
    """로그 디렉토리 경로를 반환합니다."""
    # Docker 환경에서는 /app/logs, 로컬에서는 ./logs 사용
    if os.path.exists("/app/logs"):
        return "/app/logs"
    else:
        return "./logs"

def ensure_log_directory():
    """로그 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    log_dir = get_log_directory()
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    return log_dir

# 로그 디렉토리 확인 및 생성
LOG_DIR = ensure_log_directory()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False, # Keep existing loggers like uvicorn's
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelname)s: %(asctime)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": ACCESS_LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "fmt": "%(levelname)s: %(asctime)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s",
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
            "filename": f"{LOG_DIR}/app.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "file_access": {
            "formatter": "access",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/access.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "file_error": {
            "formatter": "detailed",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/error.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "level": "ERROR",
        },
    },
    "loggers": {
        "": { # Root logger
            "handlers": ["default", "file_app", "file_error"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default", "file_error"],
            "propagate": False
        },
        "uvicorn.access": {
            "handlers": ["access", "file_access"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default", "file_app"],
            "level": "INFO",
            "propagate": False
        }
    },
}

# 간단한 로깅 설정을 반환하는 함수
def get_simple_logging_config():
    """간단한 로깅 설정을 반환합니다."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
        "default": {
                "format": "%(levelname)s: %(asctime)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        "access": {
                "format": "%(levelname)s: %(asctime)s - %(client_addr)s - \"%(request_line)s\" %(status_code)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "INFO",
            },
            "file_app": {
                "class": "logging.FileHandler",
                "filename": f"{LOG_DIR}/app.log",
                "formatter": "default",
                "level": "INFO",
                "encoding": "utf-8",
            },
            "file_access": {
                "class": "logging.FileHandler",
                "filename": f"{LOG_DIR}/access.log",
                "formatter": "access",
                "level": "INFO",
                "encoding": "utf-8",
            },
            "file_error": {
                "class": "logging.FileHandler",
                "filename": f"{LOG_DIR}/error.log",
                "formatter": "default",
                "level": "ERROR",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "file_app", "file_error"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["file_access"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "file_app", "file_error"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
