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
        title="🔍 CoE RAG Pipeline",
        description="""
        ## CoE RAG Pipeline - Git 분석 및 RAG 시스템
        
        Git 레포지토리들을 **심층 분석**하여 개발 가이드를 자동 생성하는 RAG 파이프라인입니다.
        
        ### 🚀 주요 기능
        - **Git 레포지토리 분석**: 소스코드 자동 클론 및 분석 (`/api/v1/analyze`)
        - **AST 분석**: Python, JavaScript, Java, TypeScript 등 주요 언어 지원
        - **기술스펙 분석**: 의존성, 프레임워크, 라이브러리 자동 감지
        - **레포지토리간 연관도**: 공통 의존성, 코드 패턴, 아키텍처 유사성 분석
        - **벡터 검색**: ChromaDB 기반 고성능 검색 (`/api/v1/search`)
        - **문서 자동 수집**: README, doc 폴더, 참조 URL 자동 수집
        
        ### 📊 분석 결과
        - **개발 표준 문서**: 코딩 스타일, 아키텍처 패턴 가이드
        - **공통 함수 가이드**: 재사용 가능한 함수 및 컴포넌트 추천
        - **JSON 결과**: 구조화된 분석 결과 저장 (`/api/v1/results`)
        
        ### 🔧 사용 방법
        1. **분석 시작**: `/api/v1/analyze`로 Git URL 제출
        2. **결과 확인**: `/api/v1/results/{analysis_id}`로 분석 결과 조회
        3. **벡터 검색**: `/api/v1/search`로 코드/문서 검색
        4. **통계 확인**: `/api/v1/stats`로 임베딩 통계 확인
        
        ### 🔗 연동 서비스
        - **CoE-Backend**: `http://localhost:8000` (AI 에이전트 서버)
        - **ChromaDB**: 벡터 데이터베이스 (포트 6666)
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc", 
        openapi_url="/openapi.json",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "defaultModelExpandDepth": 2,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True
        }
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