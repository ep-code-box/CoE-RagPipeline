import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
load_dotenv()


class Settings:
    """애플리케이션 설정 클래스"""
    
    # 서버 설정
    APP_ENV: str = os.getenv("APP_ENV", "").lower()
    ENABLE_DOCS: bool = os.getenv("ENABLE_DOCS", "").lower() in {"1", "true", "yes", "on"}
    # 컨테이너/프록시 환경 호환을 위해 기본은 0.0.0.0
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = 8001
    RELOAD: bool = True
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").lower()
    
    # 애플리케이션 루트 경로(프록시 하위 경로에서 서비스할 때 사용)
    # 예: Nginx에서 /rag/로 프록시되는 경우 ROOT_PATH=/rag
    ROOT_PATH: str = os.getenv("ROOT_PATH", "")
    
    # 디렉토리 설정
    RESULTS_DIR: str = "output/results"
    DOCUMENTS_DIR: str = "output/documents"
    
    # ChromaDB 설정
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "coe_documents")
    
    # 데이터베이스 설정
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # OpenAI 설정
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # SKAX API 설정
    SKAX_API_KEY: Optional[str] = os.getenv("SKAX_API_KEY")
    SKAX_API_BASE: str = os.getenv("SKAX_API_BASE", "https://guest-api.sktax.chat/v1")
    SKAX_MODEL_NAME: str = os.getenv("SKAX_MODEL_NAME", "ax4")
    
    # Git 설정
    GIT_TOKEN: Optional[str] = os.getenv("GIT_TOKEN")
    
    # 분석 설정
    MAX_REPO_SIZE_MB: int = int(os.getenv("MAX_REPO_SIZE_MB", "1000"))
    ANALYSIS_TIMEOUT_MINUTES: int = int(os.getenv("ANALYSIS_TIMEOUT_MINUTES", "60"))
    PARALLEL_ANALYSIS_WORKERS: int = int(os.getenv("PARALLEL_ANALYSIS_WORKERS", "4"))
    
    # 토큰 관리 설정
    MAX_TOKENS_PER_CHUNK: int = int(os.getenv("MAX_TOKENS_PER_CHUNK", "100000"))
    MAX_ANALYSIS_DATA_TOKENS: int = int(os.getenv("MAX_ANALYSIS_DATA_TOKENS", "8000"))
    TOKEN_SAFETY_MARGIN: int = int(os.getenv("TOKEN_SAFETY_MARGIN", "2000"))
    ENABLE_AUTO_CHUNKING: bool = os.getenv("ENABLE_AUTO_CHUNKING", "true").lower() == "true"
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

    # 검색 리랭킹 설정 (성능/비용 최적화용)
    ENABLE_RERANKING: bool = os.getenv("ENABLE_RERANKING", "false").lower() == "true"
    RERANK_MULTIPLIER: int = int(os.getenv("RERANK_MULTIPLIER", "5"))
    RERANK_MAX_CANDIDATES: int = int(os.getenv("RERANK_MAX_CANDIDATES", "30"))
    RERANK_CONTENT_CHARS: int = int(os.getenv("RERANK_CONTENT_CHARS", "1000"))
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "gpt-4o-mini")

    # 임베딩/요약 커버리지 설정 (대형 레포지토리 제어)
    EMBEDDING_CHUNK_SIZE: int = int(os.getenv("EMBEDDING_CHUNK_SIZE", "1000"))
    EMBEDDING_CHUNK_OVERLAP: int = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", "200"))

    CONTENT_EMBEDDING_CHUNK_SIZE: int = int(os.getenv("CONTENT_EMBEDDING_CHUNK_SIZE", str(EMBEDDING_CHUNK_SIZE)))
    CONTENT_EMBEDDING_CHUNK_OVERLAP: int = int(os.getenv("CONTENT_EMBEDDING_CHUNK_OVERLAP", str(EMBEDDING_CHUNK_OVERLAP)))

    SUMMARY_MAX_FILES_DEFAULT: int = int(os.getenv("SUMMARY_MAX_FILES_DEFAULT", "100"))
    SUMMARY_BATCH_SIZE_DEFAULT: int = int(os.getenv("SUMMARY_BATCH_SIZE_DEFAULT", "5"))
    SUMMARY_MAX_FILE_TOKENS: int = int(os.getenv("SUMMARY_MAX_FILE_TOKENS", "6000"))
    SUMMARY_MAX_CONCURRENT_REQUESTS: int = int(os.getenv("SUMMARY_MAX_CONCURRENT_REQUESTS", "3"))
    SUMMARY_RETRY_ATTEMPTS: int = int(os.getenv("SUMMARY_RETRY_ATTEMPTS", "3"))
    SUMMARY_RETRY_DELAY: float = float(os.getenv("SUMMARY_RETRY_DELAY", "1.0"))
    
    def __init__(self):
        # 필요한 디렉토리 생성
        os.makedirs(self.RESULTS_DIR, exist_ok=True)
        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()
