import logging
import uvicorn
from config.settings import settings
from utils.server_utils import find_available_port
from core.logging_config import get_simple_logging_config

logger = logging.getLogger(__name__)

def run_server():
    """Uvicorn 서버를 실행합니다."""
    try:
        # 사용 가능한 포트 찾기
        available_port = find_available_port(start_port=settings.PORT)
        logger.info(f"Starting server on port {available_port}")
        
        # 간단한 로깅 설정 사용
        log_config = get_simple_logging_config()
        
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=available_port,
            reload=settings.RELOAD,
            reload_dirs=["analyzers", "config","routers", "services", "models", "core", "utils"],  # 감시할 디렉토리 지정
            reload_excludes=[".*", ".py[cod]", "__pycache__", ".env", ".venv", ".git", "output","gitsync"],  # 감시를 제외할 파일 지정
            log_config=log_config,
            access_log=True,
            log_level="info"
        )
    except RuntimeError as e:
        logger.error(f"Failed to start server: {e}")
        logger.info("Please check if other processes are using ports in the range 8001-8010")
        exit(1)
