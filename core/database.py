"""
CoE-RagPipeline 데이터베이스 모델 정의
CoE-Backend와 호환되는 통합 데이터베이스 모델을 사용합니다.
"""

import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey, Enum, DECIMAL, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import enum

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정
DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "coe_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "coe_password")
DB_NAME = os.getenv("DB_NAME", "coe_db")

# MariaDB 연결 URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 및 세션 설정 (최적화)
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # 프로덕션에서는 False로 설정
    pool_pre_ping=True, 
    pool_recycle=300,
    pool_size=10,  # 연결 풀 크기
    max_overflow=20,  # 최대 오버플로우 연결 수
    pool_timeout=30,  # 연결 대기 시간
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enum 정의 (CoE-Backend와 동일)
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

class DependencyType(enum.Enum):
    FRAMEWORK = "FRAMEWORK"
    LIBRARY = "LIBRARY"
    TOOL = "TOOL"
    LANGUAGE = "LANGUAGE"

class DocumentType(enum.Enum):
    README = "README"
    API_DOC = "API_DOC"
    WIKI = "WIKI"
    CHANGELOG = "CHANGELOG"
    CONTRIBUTING = "CONTRIBUTING"
    OTHER = "OTHER"

class SourceType(enum.Enum):
    CODE = "CODE"
    DOCUMENT = "DOCUMENT"
    AST_NODE = "AST_NODE"

class StandardType(enum.Enum):
    CODING_STYLE = "CODING_STYLE"
    ARCHITECTURE_PATTERN = "ARCHITECTURE_PATTERN"
    COMMON_FUNCTIONS = "COMMON_FUNCTIONS"
    BEST_PRACTICES = "BEST_PRACTICES"

class HTTPMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

# 데이터베이스 모델 정의 (CoE-Backend와 동일한 모델 사용)

# 분석 요청 테이블
class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"
    extend_existing=True

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), unique=True, index=True, nullable=False)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    repositories = Column(JSON, nullable=False)
    include_ast = Column(Boolean, default=True)
    include_tech_spec = Column(Boolean, default=True)
    include_correlation = Column(Boolean, default=True)
    group_name = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 관계 설정
    repository_analyses = relationship("RepositoryAnalysis", back_populates="analysis_request", cascade="all, delete-orphan")
    correlation_analyses = relationship("CorrelationAnalysis", back_populates="analysis_request", cascade="all, delete-orphan")
    development_standards = relationship("DevelopmentStandard", back_populates="analysis_request", cascade="all, delete-orphan")

# 코드 파일 정보 테이블
class CodeFile(Base):
    __tablename__ = "code_files"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    repository_analysis_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    language = Column(String(50))
    complexity_score = Column(DECIMAL(5, 2))
    last_modified = Column(DateTime)
    file_hash = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    repository_analysis = relationship("RepositoryAnalysis", back_populates="code_files")
    ast_nodes = relationship("ASTNode", back_populates="code_file", cascade="all, delete-orphan")

# AST 노드 테이블
class ASTNode(Base):
    __tablename__ = "ast_nodes"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    code_file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False)
    node_type = Column(String(100), nullable=False)
    node_name = Column(String(255))
    line_start = Column(Integer)
    line_end = Column(Integer)
    parent_id = Column(Integer, ForeignKey("ast_nodes.id"))
    node_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    code_file = relationship("CodeFile", back_populates="ast_nodes")
    parent = relationship("ASTNode", remote_side=[id])

# 레포지토리 간 연관도 분석 테이블
class CorrelationAnalysis(Base):
    __tablename__ = "correlation_analyses"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_requests.analysis_id"), nullable=False)
    repository1_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    repository2_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    common_dependencies = Column(JSON)
    similar_patterns = Column(JSON)
    architecture_similarity = Column(DECIMAL(5, 4), default=0.0000)
    shared_technologies = Column(JSON)
    similarity_score = Column(DECIMAL(5, 4), default=0.0000)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    analysis_request = relationship("AnalysisRequest", back_populates="correlation_analyses")

# 벡터 임베딩 메타데이터 테이블
class VectorEmbedding(Base):
    __tablename__ = "vector_embeddings"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(Enum(SourceType), nullable=False)
    source_id = Column(Integer, nullable=False)
    chunk_id = Column(String(100), nullable=False)
    collection_name = Column(String(255), nullable=False)
    embedding_model = Column(String(100), default="default")
    chunk_text = Column(Text)
    node_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# 개발 표준 문서 테이블
class DevelopmentStandard(Base):
    __tablename__ = "development_standards"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_requests.analysis_id"), nullable=False)
    standard_type = Column(Enum(StandardType), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    examples = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    analysis_request = relationship("AnalysisRequest", back_populates="development_standards")

# 백워드 호환성을 위한 RAG 분석 결과 테이블 (기존 config/database.py와 호환)
class RagAnalysisResult(Base):
    __tablename__ = "rag_analysis_results"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(255), unique=True, index=True, nullable=False)
    git_url = Column(String(500), index=True, nullable=False)
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    repository_count = Column(Integer, default=0)
    total_files = Column(Integer, default=0)
    total_lines_of_code = Column(Integer, default=0)
    
    # 분석 결과 데이터 (JSON 형태로 저장)
    repositories_data = Column(Text, nullable=True)
    correlation_data = Column(Text, nullable=True)
    tech_specs_summary = Column(Text, nullable=True)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 인덱스 추가
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )

# 데이터베이스 모델 정의 (CoE-Backend와 동일한 모델 사용)

# 레포지토리 분석 결과 테이블
class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_requests.analysis_id"), nullable=False)
    repository_url = Column(String(500), nullable=False)
    repository_name = Column(String(255))
    branch = Column(String(100), default="main")
    clone_path = Column(String(500))
    status = Column(Enum(RepositoryStatus), default=RepositoryStatus.PENDING)
    # Commit 정보 필드 추가
    commit_hash = Column(String(40), nullable=True, index=True)  # Git commit hash (SHA-1)
    commit_date = Column(DateTime, nullable=True)
    commit_author = Column(String(255), nullable=True)
    commit_message = Column(Text, nullable=True)
    files_count = Column(Integer, default=0)
    lines_of_code = Column(Integer, default=0)
    languages = Column(JSON)
    frameworks = Column(JSON)
    dependencies = Column(JSON)
    ast_data = Column(Text)
    tech_specs = Column(JSON)
    code_metrics = Column(JSON)
    documentation_files = Column(JSON)
    config_files = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    analysis_request = relationship("AnalysisRequest", back_populates="repository_analyses")
    code_files = relationship("CodeFile", back_populates="repository_analysis", cascade="all, delete-orphan")
    tech_dependencies = relationship("TechDependency", back_populates="repository_analysis", cascade="all, delete-orphan")
    document_analyses = relationship("DocumentAnalysis", back_populates="repository_analysis", cascade="all, delete-orphan")



# 기술 스택 및 의존성 테이블
class TechDependency(Base):
    __tablename__ = "tech_dependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_analysis_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    dependency_type = Column(Enum(DependencyType), nullable=False)
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    package_manager = Column(String(50))
    is_dev_dependency = Column(Boolean, default=False)
    license = Column(String(100))
    vulnerability_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    repository_analysis = relationship("RepositoryAnalysis", back_populates="tech_dependencies")

# 문서 분석 결과 테이블
class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"
    extend_existing=True
    
    id = Column(Integer, primary_key=True, index=True)
    repository_analysis_id = Column(Integer, ForeignKey("repository_analyses.id"), nullable=False)
    document_path = Column(String(1000), nullable=False)
    document_type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    title = Column(String(500))
    content = Column(Text)
    extracted_sections = Column(JSON)
    code_examples = Column(JSON)
    api_endpoints = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    repository_analysis = relationship("RepositoryAnalysis", back_populates="document_analyses")

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

# 데이터베이스 초기화 상태 추적 (테이블 확인)
def _is_database_initialized():
    """데이터베이스가 이미 초기화되었는지 확인합니다."""
    try:
        inspector = inspect(engine)
        # 필수 테이블이 있는지 확인하여 초기화 여부 판단
        # 'rag_analysis_results'는 백워드 호환용으로 선택 사항이므로 부트 조건에서 제외합니다.
        required_tables = {'analysis_requests', 'repository_analyses'}
        existing_tables = set(inspector.get_table_names())
        print(f"🔍 현재 데이터베이스에 존재하는 테이블: {existing_tables}")
        return required_tables.issubset(existing_tables)
    except Exception as e:
        # 데이터베이스 연결 실패 등 예외 발생 시 초기화되지 않은 것으로 간주
        print(f"⚠️ 데이터베이스 확인 중 오류 발생 (초기화 필요 가능성): {e}")
        return False

# 데이터베이스 초기화
def init_database():
    """데이터베이스를 초기화합니다."""
    # 이미 초기화되었다면 건너뛰기
    if _is_database_initialized():
        print("✅ 데이터베이스가 이미 초기화되었습니다. 건너뜁니다.")
        return True
        
    print("🔄 RAG Pipeline 데이터베이스 초기화 중...")
    
    # 연결 테스트
    if not test_connection():
        return False
    
    # Alembic이 마이그레이션을 처리하므로, 여기서는 테이블을 직접 생성하지 않습니다.
    # create_tables()
    
    # 초기화 완료 후 다시 확인
    if not _is_database_initialized():
        print("❌ 초기화 후에도 데이터베이스 테이블이 확인되지 않았습니다.")
        return False
        
    print("✅ 데이터베이스 초기화가 성공적으로 완료되었습니다.")
    return True

# 분석 결과를 데이터베이스에 저장하는 함수 (백워드 호환성)
def save_analysis_to_db(analysis_result):
    """분석 결과를 데이터베이스에 저장합니다."""
    try:
        db = SessionLocal()
        
        # Git URL 추출 (첫 번째 레포지토리의 URL 사용)
        git_url = ""
        if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
            if hasattr(analysis_result.repositories[0], 'repository'):
                git_url = str(analysis_result.repositories[0].repository.url)
            else:
                git_url = "unknown"
        
        # 통계 계산
        total_files = 0
        total_lines = 0
        if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
            total_files = sum(len(getattr(repo, 'files', [])) for repo in analysis_result.repositories)
            total_lines = sum(getattr(getattr(repo, 'code_metrics', None), 'lines_of_code', 0) for repo in analysis_result.repositories)
        
        # 데이터베이스 레코드 생성
        db_record = RagAnalysisResult(
            analysis_id=analysis_result.analysis_id,
            git_url=git_url,
            analysis_date=analysis_result.created_at,
            status=analysis_result.status,
            repository_count=len(getattr(analysis_result, 'repositories', [])),
            total_files=total_files,
            total_lines_of_code=total_lines,
            repositories_data=json.dumps([repo.model_dump() if hasattr(repo, 'model_dump') else str(repo) for repo in getattr(analysis_result, 'repositories', [])], default=str, ensure_ascii=False),
            correlation_data=json.dumps(analysis_result.correlation_analysis.model_dump() if hasattr(analysis_result, 'correlation_analysis') and analysis_result.correlation_analysis else None, default=str, ensure_ascii=False),
            tech_specs_summary=json.dumps([], default=str, ensure_ascii=False),
            created_at=analysis_result.created_at,
            completed_at=getattr(analysis_result, 'completed_at', None),
            error_message=getattr(analysis_result, 'error_message', None)
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

# 데이터베이스 테이블 생성
def create_tables():
    """데이터베이스에 모든 테이블을 생성합니다."""
    print("🔄 데이터베이스 테이블 생성을 시작합니다...")
    try:
        # Base에 정의된 모든 테이블을 생성
        Base.metadata.create_all(bind=engine)
        print("✅ 모든 데이터베이스 테이블이 성공적으로 확인 또는 생성되었습니다.")
        
        # (선택 사항) 각 테이블 생성 여부 확인 로그
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        print(f"🔍 현재 데이터베이스에 존재하는 테이블: {table_names}")
        
    except Exception as e:
        print(f"❌ 테이블 생성 중 심각한 오류 발생: {e}")

# 데이터베이스 초기화 상태 추적 (테이블 확인)
def _is_database_initialized():
    """데이터베이스가 이미 초기화되었는지 확인합니다."""
    try:
        inspector = inspect(engine)
        # 필수 테이블이 있는지 확인하여 초기화 여부 판단
        # 'rag_analysis_results'는 백워드 호환용으로 선택 사항이므로 부트 조건에서 제외합니다.
        required_tables = {'analysis_requests', 'repository_analyses'}
        existing_tables = set(inspector.get_table_names())
        print(f"🔍 현재 데이터베이스에 존재하는 테이블: {existing_tables}")
        return required_tables.issubset(existing_tables)
    except Exception as e:
        # 데이터베이스 연결 실패 등 예외 발생 시 초기화되지 않은 것으로 간주
        print(f"⚠️ 데이터베이스 확인 중 오류 발생 (초기화 필요 가능성): {e}")
        return False

# 데이터베이스 초기화
def init_database():
    """데이터베이스를 초기화합니다."""
    # 이미 초기화되었다면 건너뛰기
    if _is_database_initialized():
        print("✅ 데이터베이스가 이미 초기화되었습니다. 건너뜁니다.")
        return True
        
    print("🔄 RAG Pipeline 데이터베이스 초기화 중...")
    
    # 연결 테스트
    if not test_connection():
        return False
    
    # Alembic이 마이그레이션을 처리하므로, 여기서는 테이블을 직접 생성하지 않습니다.
    # create_tables()
    
    # 초기화 완료 후 다시 확인
    if not _is_database_initialized():
        print("❌ 초기화 후에도 데이터베이스 테이블이 확인되지 않았습니다.")
        return False
        
    print("✅ 데이터베이스 초기화가 성공적으로 완료되었습니다.")
    return True

# 분석 결과를 데이터베이스에 저장하는 함수 (백워드 호환성)
def save_analysis_to_db(analysis_result):
    """분석 결과를 데이터베이스에 저장합니다."""
    try:
        db = SessionLocal()
        
        # Git URL 추출 (첫 번째 레포지토리의 URL 사용)
        git_url = ""
        if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
            if hasattr(analysis_result.repositories[0], 'repository'):
                git_url = str(analysis_result.repositories[0].repository.url)
            else:
                git_url = "unknown"
        
        # 통계 계산
        total_files = 0
        total_lines = 0
        if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
            total_files = sum(len(getattr(repo, 'files', [])) for repo in analysis_result.repositories)
            total_lines = sum(getattr(getattr(repo, 'code_metrics', None), 'lines_of_code', 0) for repo in analysis_result.repositories)
        
        # 데이터베이스 레코드 생성
        db_record = RagAnalysisResult(
            analysis_id=analysis_result.analysis_id,
            git_url=git_url,
            analysis_date=analysis_result.created_at,
            status=analysis_result.status,
            repository_count=len(getattr(analysis_result, 'repositories', [])),
            total_files=total_files,
            total_lines_of_code=total_lines,
            repositories_data=json.dumps([repo.model_dump() if hasattr(repo, 'model_dump') else str(repo) for repo in getattr(analysis_result, 'repositories', [])], default=str, ensure_ascii=False),
            correlation_data=json.dumps(analysis_result.correlation_analysis.model_dump() if hasattr(analysis_result, 'correlation_analysis') and analysis_result.correlation_analysis else None, default=str, ensure_ascii=False),
            tech_specs_summary=json.dumps([], default=str, ensure_ascii=False),
            created_at=analysis_result.created_at,
            completed_at=getattr(analysis_result, 'completed_at', None),
            error_message=getattr(analysis_result, 'error_message', None)
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
