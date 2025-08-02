import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import health, analysis, embedding
from config.settings import settings
from utils.server_utils import find_available_port
from utils.app_initializer import initialize_services
from config.database import init_database

# 로깅 설정 - uvicorn과 중복 방지
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # 기존 설정 덮어쓰기
)
logger = logging.getLogger(__name__)

# uvicorn 로거 설정 조정 (중복 로그 방지)
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.disabled = False  # uvicorn 로그는 유지


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 생성 및 설정"""
    app = FastAPI(
        title="CoE RAG Pipeline",
        description="Git 레포지토리들을 분석하여 레포지토리간 연관도, AST 분석, 기술스펙 정적 분석을 수행하는 RAG 파이프라인",
        version="1.0.0"
    )

    # CORS 미들웨어 추가
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(health.router)
    app.include_router(analysis.router)
    app.include_router(embedding.router)

    return app


# FastAPI 앱 생성
app = create_app()

# 데이터베이스 초기화
print("🔄 Initializing database...")
if init_database():
    print("✅ Database initialized successfully")
else:
    print("❌ Database initialization failed")

# 서비스 초기화
initialize_services()


if __name__ == "__main__":
    try:
        # 사용 가능한 포트 찾기
        available_port = find_available_port(start_port=settings.PORT)
        logger.info(f"Starting server on port {available_port}")
        
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=available_port,
            reload=settings.RELOAD,
            log_level=settings.LOG_LEVEL
        )
    except RuntimeError as e:
        logger.error(f"Failed to start server: {e}")
        logger.info("Please check if other processes are using ports in the range 8001-8010")
        exit(1)