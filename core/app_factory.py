import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from routers import health, analysis, embedding, document_generation, source_summary, content_embedding_router
from config.settings import settings
from core.database import init_database
from utils.app_initializer import initialize_services

logger = logging.getLogger(__name__)

class AppFactory:
    """FastAPI 애플리케이션 생성 및 초기화를 담당하는 팩토리 클래스"""
    
    def __init__(self):
        self.app = None
    
    def initialize_database(self):
        """데이터베이스 초기화"""
        logger.info("🔄 Initializing database...")
        if init_database():
            logger.info("✅ Database initialized successfully")
            return True
        else:
            logger.error("❌ Database initialization failed")
            return False
    
    def initialize_services(self):
        """서비스 초기화"""
        logger.info("🔄 Initializing services...")
        try:
            initialize_services()
            logger.info("✅ Services initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            return False
    
    def create_app(self) -> FastAPI:
        """FastAPI 애플리케이션 생성 및 설정"""
        # 데이터베이스 초기화
        if not self.initialize_database():
            raise RuntimeError("Database initialization failed")
        
        # 서비스 초기화
        if not self.initialize_services():
            raise RuntimeError("Service initialization failed")
        
        # FastAPI 앱 생성
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
            - **LLM 문서 생성**: 분석 결과 기반 개발 가이드, API 문서 등 자동 생성 (`/api/v1/documents/generate`)
            
            ### 📊 분석 결과
            - **개발 표준 문서**: 코딩 스타일, 아키텍처 패턴 가이드
            - **공통 함수 가이드**: 재사용 가능한 함수 및 컴포넌트 추천
            - **JSON 결과**: 구조화된 분석 결과 저장 (`/api/v1/results`)
            
            ### 🔧 사용 방법
            1. **분석 시작**: `/api/v1/analyze`로 Git URL 제출
            2. **결과 확인**: `/api/v1/results/{analysis_id}`로 분석 결과 조회
            3. **문서 생성**: `/api/v1/documents/generate`로 LLM 기반 문서 생성
            4. **벡터 검색**: `/api/v1/search`로 코드/문서 검색
            5. **통계 확인**: `/api/v1/stats`로 임베딩 통계 확인
            
            ### 🔗 연동 서비스
            - **CoE-Backend**: `http://localhost:8000` (AI 에이전트 서버)
            - **ChromaDB**: 벡터 데이터베이스 (포트 6666)
            """,
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc", 
            openapi_url="/openapi.json",
            # Nginx 등 프록시 하위 경로(/rag)로 서비스될 때를 위한 루트 경로 설정
            # 환경변수 ROOT_PATH로 제어 (빈 값이면 직접 포트 접근 시에도 문제 없음)
            root_path=settings.ROOT_PATH,
            root_path_in_servers=True,
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

        # 요청 로깅 미들웨어 추가
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            
            # 요청 정보 로깅
            logger.info(f"🌐 {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
            
            # 요청 본문 로깅 (POST 요청의 경우)
            if request.method == "POST":
                try:
                    body = await request.body()
                    if body:
                        logger.info(f"📝 Request body: {body.decode('utf-8')[:500]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Could not read request body: {e}")
            
            # 응답 처리
            response = await call_next(request)
            
            # 응답 시간 계산
            process_time = time.time() - start_time
            logger.info(f"✅ {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
            
            return response

        # 라우터 등록
        app.include_router(health.router)
        app.include_router(analysis.router)
        app.include_router(embedding.router)
        app.include_router(document_generation.router)
        app.include_router(source_summary.router)
        app.include_router(content_embedding_router.router)

        # Startup 이벤트 등록
        @app.on_event("startup")
        async def startup_event():
            logger.info("CoE-RagPipeline application startup event triggered.")

        self.app = app
        return app


def create_app() -> FastAPI:
    """애플리케이션 팩토리를 사용하여 FastAPI 앱 생성"""
    factory = AppFactory()
    return factory.create_app()
