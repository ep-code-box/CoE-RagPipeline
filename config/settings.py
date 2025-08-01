import os
from typing import Optional


class Settings:
    """애플리케이션 설정 클래스"""
    
    # 서버 설정
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
    # 디렉토리 설정
    RESULTS_DIR: str = "output/results"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    
    # 데이터베이스 설정
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # OpenAI 설정
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Git 설정
    GIT_TOKEN: Optional[str] = os.getenv("GIT_TOKEN")
    
    # 분석 설정
    MAX_REPO_SIZE_MB: int = int(os.getenv("MAX_REPO_SIZE_MB", "1000"))
    ANALYSIS_TIMEOUT_MINUTES: int = int(os.getenv("ANALYSIS_TIMEOUT_MINUTES", "60"))
    PARALLEL_ANALYSIS_WORKERS: int = int(os.getenv("PARALLEL_ANALYSIS_WORKERS", "4"))
    
    def __init__(self):
        # 필요한 디렉토리 생성
        os.makedirs(self.RESULTS_DIR, exist_ok=True)
        os.makedirs(self.CHROMA_PERSIST_DIRECTORY, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()