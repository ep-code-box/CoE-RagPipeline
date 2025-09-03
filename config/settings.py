import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
load_dotenv()


class Settings:
    """애플리케이션 설정 클래스"""
    
    # 서버 설정
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
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
    
    def __init__(self):
        # 필요한 디렉토리 생성
        os.makedirs(self.RESULTS_DIR, exist_ok=True)
        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()