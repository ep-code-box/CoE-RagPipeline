import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey, Enum, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import enum

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "coe_db")

# MariaDB 연결 URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enum 정의 (CoE-Backend와 동일하게 유지)
class AnalysisStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RepositoryStatus(enum.Enum):
    PENDING = "PENDING"
    CLONING = "CLONING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# RAG Pipeline 분석 결과 테이블 모델
class RagAnalysisResult(Base):
    __tablename__ = "rag_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(255), unique=True, index=True, nullable=False)
    git_url = Column(String(500), index=True, nullable=False)  # Git URL을 키로 사용
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False)  # 분석일자
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    repository_count = Column(Integer, default=0)
    total_files = Column(Integer, default=0)
    total_lines_of_code = Column(Integer, default=0)
    
    # 분석 결과 데이터 (JSON 형태로 저장)
    repositories_data = Column(Text, nullable=True)  # RepositoryAnalysis 목록을 JSON으로 저장
    correlation_data = Column(Text, nullable=True)   # CorrelationAnalysis를 JSON으로 저장
    tech_specs_summary = Column(Text, nullable=True) # 기술스펙 요약을 JSON으로 저장
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 인덱스 추가
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )

# 데이터베이스 테이블 생성
def create_tables():
    """데이터베이스 테이블을 생성합니다."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ RAG Pipeline 데이터베이스 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류 발생: {e}")

# 데이터베이스 세션 의존성
def get_db():
    """데이터베이스 세션을 반환합니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 연결 테스트
def test_connection():
    """데이터베이스 연결을 테스트합니다."""
    try:
        # 먼저 데이터베이스 없이 연결 테스트
        test_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
        test_engine = create_engine(test_url)
        
        with test_engine.connect() as connection:
            # 데이터베이스 생성
            from sqlalchemy import text
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            print(f"✅ 데이터베이스 '{DB_NAME}' 생성/확인 완료")
        
        # 이제 실제 데이터베이스에 연결
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ MariaDB 연결 성공!")
            return True
    except Exception as e:
        print(f"❌ MariaDB 연결 실패: {e}")
        return False

# 데이터베이스 초기화
def init_database():
    """데이터베이스를 초기화합니다."""
    print("🔄 RAG Pipeline 데이터베이스 초기화 중...")
    
    # 연결 테스트
    if not test_connection():
        return False
    
    # 테이블 생성
    create_tables()
    return True

# 분석 결과를 데이터베이스에 저장하는 함수
def save_analysis_to_db(analysis_result):
    """분석 결과를 데이터베이스에 저장합니다."""
    try:
        db = SessionLocal()
        
        # Git URL 추출 (첫 번째 레포지토리의 URL 사용)
        git_url = ""
        if analysis_result.repositories:
            git_url = str(analysis_result.repositories[0].repository.url)
        
        # 통계 계산
        total_files = sum(len(repo.files) for repo in analysis_result.repositories)
        total_lines = sum(repo.code_metrics.lines_of_code for repo in analysis_result.repositories)
        
        # 데이터베이스 레코드 생성
        db_record = RagAnalysisResult(
            analysis_id=analysis_result.analysis_id,
            git_url=git_url,
            analysis_date=analysis_result.created_at,
            status=analysis_result.status.value,
            repository_count=len(analysis_result.repositories),
            total_files=total_files,
            total_lines_of_code=total_lines,
            repositories_data=json.dumps([repo.model_dump() for repo in analysis_result.repositories], default=str, ensure_ascii=False),
            correlation_data=json.dumps(analysis_result.correlation_analysis.model_dump() if analysis_result.correlation_analysis else None, default=str, ensure_ascii=False),
            tech_specs_summary=json.dumps([spec.model_dump() for repo in analysis_result.repositories for spec in repo.tech_specs], default=str, ensure_ascii=False),
            created_at=analysis_result.created_at,
            completed_at=analysis_result.completed_at,
            error_message=analysis_result.error_message
        )
        
        # 기존 레코드가 있으면 업데이트, 없으면 새로 생성
        existing = db.query(RagAnalysisResult).filter(RagAnalysisResult.analysis_id == analysis_result.analysis_id).first()
        if existing:
            # 업데이트
            for key, value in db_record.__dict__.items():
                if not key.startswith('_'):
                    setattr(existing, key, value)
            db.commit()
            print(f"✅ 분석 결과 업데이트 완료: {analysis_result.analysis_id}")
        else:
            # 새로 생성
            db.add(db_record)
            db.commit()
            print(f"✅ 분석 결과 저장 완료: {analysis_result.analysis_id}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 저장 실패: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False