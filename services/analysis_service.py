import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# 모듈 레벨 logger 정의
logger = logging.getLogger(__name__)

from core.database import (
    AnalysisRequest, RepositoryAnalysis, CodeFile, ASTNode, 
    TechDependency, CorrelationAnalysis, DocumentAnalysis,
    DevelopmentStandard, VectorEmbedding,
    AnalysisStatus, RepositoryStatus, DependencyType, 
    DocumentType, SourceType, StandardType,
    get_db, SessionLocal
)

class RagAnalysisService:
    """RAG 파이프라인 분석 서비스"""
    
    @staticmethod
    def create_analysis_request(
        db: Session, 
        repositories: List[Dict[str, Any]], 
        include_ast: bool = True,
        include_tech_spec: bool = True,
        include_correlation: bool = True,
        analysis_id: Optional[str] = None
    ) -> AnalysisRequest:
        """새로운 분석 요청을 생성합니다."""
        try:
            if not analysis_id:
                analysis_id = str(uuid.uuid4())
            
            db_analysis = AnalysisRequest(
                analysis_id=analysis_id,
                repositories=repositories,
                include_ast=include_ast,
                include_tech_spec=include_tech_spec,
                include_correlation=include_correlation,
                status=AnalysisStatus.PENDING
            )
            
            db.add(db_analysis)
            db.commit()
            db.refresh(db_analysis)
            
            return db_analysis
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Analysis with ID '{analysis_id}' already exists")
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create analysis request: {str(e)}")
    
    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: str) -> Optional[AnalysisRequest]:
        """분석 ID로 분석 요청을 조회합니다."""
        return db.query(AnalysisRequest).filter(AnalysisRequest.analysis_id == analysis_id).first()
    
    @staticmethod
    def get_all_analyses(db: Session, limit: int = 100, offset: int = 0) -> List[AnalysisRequest]:
        """모든 분석 요청을 조회합니다."""
        return db.query(AnalysisRequest).order_by(AnalysisRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def update_analysis_status(
        db: Session, 
        analysis_id: str, 
        status: AnalysisStatus,
        error_message: Optional[str] = None
    ) -> Optional[AnalysisRequest]:
        """분석 상태를 업데이트합니다."""
        try:
            db_analysis = RagAnalysisService.get_analysis_by_id(db, analysis_id)
            if not db_analysis:
                return None
            
            db_analysis.status = status
            db_analysis.updated_at = datetime.utcnow()
            
            if status == AnalysisStatus.COMPLETED:
                db_analysis.completed_at = datetime.utcnow()
            
            if error_message:
                db_analysis.error_message = error_message
            
            db.commit()
            db.refresh(db_analysis)
            
            return db_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update analysis status: {str(e)}")
    
    @staticmethod
    def start_analysis(db: Session, analysis_id: str) -> Optional[AnalysisRequest]:
        """분석을 시작 상태로 변경합니다."""
        return RagAnalysisService.update_analysis_status(db, analysis_id, AnalysisStatus.RUNNING)
    
    @staticmethod
    def complete_analysis(db: Session, analysis_id: str) -> Optional[AnalysisRequest]:
        """분석을 완료 상태로 변경합니다."""
        return RagAnalysisService.update_analysis_status(db, analysis_id, AnalysisStatus.COMPLETED)
    
    @staticmethod
    def fail_analysis(db: Session, analysis_id: str, error_message: str) -> Optional[AnalysisRequest]:
        """분석을 실패 상태로 변경합니다."""
        return RagAnalysisService.update_analysis_status(db, analysis_id, AnalysisStatus.FAILED, error_message)

class RagRepositoryAnalysisService:
    """RAG 레포지토리 분석 결과 관리 서비스"""
    
    @staticmethod
    def create_repository_analysis(
        db: Session,
        analysis_id: str,
        repository_url: str,
        repository_name: Optional[str] = None,
        branch: str = "main",
        clone_path: Optional[str] = None
    ) -> RepositoryAnalysis:
        """새로운 레포지토리 분석을 생성합니다."""
        try:
            db_repo_analysis = RepositoryAnalysis(
                analysis_id=analysis_id,
                repository_url=repository_url,
                repository_name=repository_name,
                branch=branch,
                clone_path=clone_path,
                status=RepositoryStatus.PENDING
            )
            
            db.add(db_repo_analysis)
            db.commit()
            db.refresh(db_repo_analysis)
            
            return db_repo_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create repository analysis: {str(e)}")
    
    @staticmethod
    def update_repository_status(
        db: Session,
        repo_analysis_id: int,
        status: RepositoryStatus
    ) -> Optional[RepositoryAnalysis]:
        """레포지토리 분석 상태를 업데이트합니다."""
        try:
            db_repo_analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.id == repo_analysis_id).first()
            if not db_repo_analysis:
                return None
            
            db_repo_analysis.status = status
            db_repo_analysis.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_repo_analysis)
            
            return db_repo_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update repository status: {str(e)}")
    
    @staticmethod
    def save_analysis_results(
        db: Session,
        repo_analysis_id: int,
        files_count: int = 0,
        lines_of_code: int = 0,
        languages: Optional[List[str]] = None,
        frameworks: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        ast_data: Optional[str] = None,
        tech_specs: Optional[Dict[str, Any]] = None,
        code_metrics: Optional[Dict[str, Any]] = None,
        documentation_files: Optional[List[str]] = None,
        config_files: Optional[List[str]] = None
    ) -> Optional[RepositoryAnalysis]:
        """레포지토리 분석 결과를 저장합니다."""
        try:
            db_repo_analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.id == repo_analysis_id).first()
            if not db_repo_analysis:
                return None
            
            db_repo_analysis.files_count = files_count
            db_repo_analysis.lines_of_code = lines_of_code
            db_repo_analysis.languages = languages or []
            db_repo_analysis.frameworks = frameworks or []
            db_repo_analysis.dependencies = dependencies or []
            db_repo_analysis.ast_data = ast_data
            db_repo_analysis.tech_specs = tech_specs or {}
            db_repo_analysis.code_metrics = code_metrics or {}
            db_repo_analysis.documentation_files = documentation_files or []
            db_repo_analysis.config_files = config_files or []
            db_repo_analysis.status = RepositoryStatus.COMPLETED
            db_repo_analysis.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_repo_analysis)
            
            return db_repo_analysis
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to save analysis results: {str(e)}")
    
    @staticmethod
    def get_repositories_by_analysis_id(db: Session, analysis_id: str) -> List[RepositoryAnalysis]:
        """분석 ID로 레포지토리 분석 결과들을 조회합니다."""
        return db.query(RepositoryAnalysis).filter(RepositoryAnalysis.analysis_id == analysis_id).all()

class RagCodeFileService:
    """RAG 코드 파일 관리 서비스"""
    
    @staticmethod
    def create_code_files_batch(
        db: Session,
        repository_analysis_id: int,
        files_data: List[Dict[str, Any]]
    ) -> List[CodeFile]:
        """코드 파일들을 배치로 생성합니다."""
        try:
            db_code_files = []
            for file_data in files_data:
                db_code_file = CodeFile(
                    repository_analysis_id=repository_analysis_id,
                    file_path=file_data.get('path', ''),
                    file_name=file_data.get('name', ''),
                    file_size=file_data.get('size', 0),
                    language=file_data.get('language'),
                    lines_of_code=file_data.get('lines_of_code', 0),
                    complexity_score=file_data.get('complexity_score'),
                    last_modified=file_data.get('last_modified'),
                    file_hash=file_data.get('file_hash')
                )
                db_code_files.append(db_code_file)
            
            db.add_all(db_code_files)
            db.commit()
            
            for db_code_file in db_code_files:
                db.refresh(db_code_file)
            
            return db_code_files
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create code files batch: {str(e)}")

class RagTechDependencyService:
    """RAG 기술 의존성 관리 서비스"""
    
    @staticmethod
    def create_tech_dependencies_batch(
        db: Session,
        repository_analysis_id: int,
        dependencies_data: List[Dict[str, Any]]
    ) -> List[TechDependency]:
        """기술 의존성들을 배치로 생성합니다."""
        try:
            db_dependencies = []
            for dep_data in dependencies_data:
                db_dependency = TechDependency(
                    repository_analysis_id=repository_analysis_id,
                    dependency_type=DependencyType(dep_data.get('type', 'library')),
                    name=dep_data.get('name', ''),
                    version=dep_data.get('version'),
                    package_manager=dep_data.get('package_manager'),
                    is_dev_dependency=dep_data.get('is_dev_dependency', False),
                    license=dep_data.get('license'),
                    vulnerability_count=dep_data.get('vulnerability_count', 0)
                )
                db_dependencies.append(db_dependency)
            
            db.add_all(db_dependencies)
            db.commit()
            
            for db_dependency in db_dependencies:
                db.refresh(db_dependency)
            
            return db_dependencies
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create tech dependencies batch: {str(e)}")

class RagDocumentAnalysisService:
    """RAG 문서 분석 관리 서비스"""
    
    @staticmethod
    def create_document_analyses_batch(
        db: Session,
        repository_analysis_id: int,
        documents_data: List[Dict[str, Any]]
    ) -> List[DocumentAnalysis]:
        """문서 분석들을 배치로 생성합니다."""
        try:
            db_documents = []
            for doc_data in documents_data:
                db_document = DocumentAnalysis(
                    repository_analysis_id=repository_analysis_id,
                    document_path=doc_data.get('path', ''),
                    document_type=DocumentType(doc_data.get('type', 'other')),
                    title=doc_data.get('title'),
                    content=doc_data.get('content'),
                    extracted_sections=doc_data.get('extracted_sections', {}),
                    code_examples=doc_data.get('code_examples', {}),
                    api_endpoints=doc_data.get('api_endpoints', {})
                )
                db_documents.append(db_document)
            
            db.add_all(db_documents)
            db.commit()
            
            for db_document in db_documents:
                db.refresh(db_document)
            
            return db_documents
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create document analyses batch: {str(e)}")

# 메인 분석 서비스 클래스
class AnalysisService:
    """메인 분석 서비스 - 전체 분석 프로세스를 관리합니다."""
    
    def __init__(self):
        self.rag_analysis_service = RagAnalysisService()
    
    async def perform_analysis(self, analysis_id: str, request, analysis_results: dict, db: Session):
        """백그라운드에서 분석을 수행합니다."""
        from models.schemas import AnalysisStatus
        from core.database import save_analysis_to_db
        
        try:
            # 분석 상태를 RUNNING으로 변경
            if analysis_id in analysis_results:
                analysis_results[analysis_id].status = AnalysisStatus.RUNNING
                
            logger.info(f"Starting analysis for {analysis_id}")
            
            # 실제 분석 로직 수행
            # Git 분석, AST 분석, 기술스펙 분석 로직 구현
            await self._perform_git_analysis(analysis_id, request, analysis_results)
            await self._perform_ast_analysis(analysis_id, request, analysis_results)
            await self._perform_tech_spec_analysis(analysis_id, request, analysis_results)
            
            # 분석 완료 상태로 변경
            if analysis_id in analysis_results:
                analysis_results[analysis_id].status = AnalysisStatus.COMPLETED
                analysis_results[analysis_id].completed_at = datetime.now()
                
                # 데이터베이스에 저장
                try:
                    save_analysis_to_db(analysis_results[analysis_id])
                    logger.info(f"Analysis {analysis_id} saved to database")
                except Exception as e:
                    logger.error(f"Failed to save analysis {analysis_id} to database: {e}")
            
            logger.info(f"Analysis {analysis_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {e}")
            
            # 분석 실패 상태로 변경
            if analysis_id in analysis_results:
                analysis_results[analysis_id].status = AnalysisStatus.FAILED
                analysis_results[analysis_id].error_message = str(e)
                analysis_results[analysis_id].completed_at = datetime.now()
    
    async def _perform_git_analysis(self, analysis_id: str, request, analysis_results: dict):
        """Git 분석 수행"""
        try:
            logger.info(f"Performing Git analysis for {analysis_id}")
            
            # Git 분석 로직 구현
            for repo_info in request.repositories:
                git_url = repo_info.get('git_url', '')
                if git_url:
                    # 실제 Git 분석 로직을 여기에 구현
                    # 예: git clone, 파일 구조 분석, 커밋 히스토리 분석 등
                    logger.info(f"Analyzing Git repository: {git_url}")
                    
                    # 임시 분석 결과 (실제 구현 시 대체)
                    repo_analysis = {
                        "git_url": git_url,
                        "total_files": 100,  # 실제 파일 수로 대체
                        "total_lines": 5000,  # 실제 라인 수로 대체
                        "languages": ["Python", "JavaScript"],  # 실제 언어 분석 결과로 대체
                        "last_commit": "2024-01-01",  # 실제 마지막 커밋 날짜로 대체
                    }
                    
                    if analysis_id in analysis_results:
                        analysis_results[analysis_id].repositories.append(repo_analysis)
                        
        except Exception as e:
            logger.error(f"Git analysis failed for {analysis_id}: {e}")
            raise
    
    async def _perform_ast_analysis(self, analysis_id: str, request, analysis_results: dict):
        """AST 분석 수행"""
        try:
            if not request.include_ast:
                logger.info(f"AST analysis skipped for {analysis_id}")
                return
                
            logger.info(f"Performing AST analysis for {analysis_id}")
            
            # AST 분석 로직 구현
            # 예: 코드 구조 분석, 함수/클래스 추출, 의존성 분석 등
            
            # 임시 분석 결과 (실제 구현 시 대체)
            ast_analysis = {
                "functions_count": 50,  # 실제 함수 수로 대체
                "classes_count": 20,    # 실제 클래스 수로 대체
                "complexity_score": 7.5,  # 실제 복잡도 점수로 대체
                "dependencies": ["fastapi", "sqlalchemy", "pydantic"]  # 실제 의존성으로 대체
            }
            
            if analysis_id in analysis_results:
                if not hasattr(analysis_results[analysis_id], 'ast_analysis'):
                    analysis_results[analysis_id].ast_analysis = ast_analysis
                    
        except Exception as e:
            logger.error(f"AST analysis failed for {analysis_id}: {e}")
            raise
    
    async def _perform_tech_spec_analysis(self, analysis_id: str, request, analysis_results: dict):
        """기술스펙 분석 수행"""
        try:
            if not request.include_tech_spec:
                logger.info(f"Tech spec analysis skipped for {analysis_id}")
                return
                
            logger.info(f"Performing tech spec analysis for {analysis_id}")
            
            # 기술스펙 분석 로직 구현
            # 예: 사용된 기술 스택 분석, 아키텍처 패턴 분석, 보안 취약점 분석 등
            
            # 임시 분석 결과 (실제 구현 시 대체)
            tech_spec_analysis = {
                "tech_stack": ["Python", "FastAPI", "SQLAlchemy", "MariaDB"],
                "architecture_patterns": ["REST API", "Microservices", "MVC"],
                "security_score": 8.0,  # 실제 보안 점수로 대체
                "performance_score": 7.5,  # 실제 성능 점수로 대체
                "maintainability_score": 8.5  # 실제 유지보수성 점수로 대체
            }
            
            if analysis_id in analysis_results:
                if not hasattr(analysis_results[analysis_id], 'tech_spec_analysis'):
                    analysis_results[analysis_id].tech_spec_analysis = tech_spec_analysis
                    
        except Exception as e:
            logger.error(f"Tech spec analysis failed for {analysis_id}: {e}")
            raise
    
    def load_analysis_result(self, analysis_id: str):
        """디스크에서 분석 결과를 로드합니다 (백워드 호환성)."""
        import os
        from models.schemas import AnalysisResult
        
        try:
            output_dir = "output/results"
            filepath = os.path.join(output_dir, f"{analysis_id}.json")
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AnalysisResult(**data)
            return None
        except Exception as e:
            print(f"Error loading analysis result from disk: {e}")
            return None
    
    def load_analysis_result_from_db(self, analysis_id: str, db: Session):
        """데이터베이스에서 분석 결과를 로드합니다."""
        from core.database import RagAnalysisResult
        from models.schemas import AnalysisResult, AnalysisStatus
        
        try:
            db_result = db.query(RagAnalysisResult).filter(
                RagAnalysisResult.analysis_id == analysis_id
            ).first()
            
            if db_result:
                # 데이터베이스 결과를 AnalysisResult 모델로 변환
                return AnalysisResult(
                    analysis_id=db_result.analysis_id,
                    status=AnalysisStatus(db_result.status),
                    created_at=db_result.analysis_date,
                    completed_at=db_result.completed_at,
                    repositories=json.loads(db_result.repositories_data) if db_result.repositories_data else [],
                    correlation_analysis=json.loads(db_result.correlation_data) if db_result.correlation_data else None,
                    error_message=db_result.error_message
                )
            return None
        except Exception as e:
            print(f"Error loading analysis result from database: {e}")
            return None
    
    def get_all_analysis_results_from_db(self, db: Session):
        """데이터베이스에서 모든 분석 결과를 조회합니다."""
        from core.database import RagAnalysisResult
        
        try:
            return db.query(RagAnalysisResult).all()
        except Exception as e:
            print(f"Error loading all analysis results from database: {e}")
            return []
    
    def load_all_analysis_results(self):
        """모든 분석 결과를 로드합니다 (디스크에서)."""
        import os
        from models.schemas import AnalysisResult
        
        results = {}
        try:
            output_dir = "output/results"
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    if filename.endswith('.json'):
                        analysis_id = filename[:-5]  # .json 제거
                        result = self.load_analysis_result(analysis_id)
                        if result:
                            results[analysis_id] = result
        except Exception as e:
            print(f"Error loading all analysis results: {e}")
        
        return results

# 편의 함수들
def get_rag_analysis_service() -> RagAnalysisService:
    """RagAnalysisService 인스턴스를 반환합니다."""
    return RagAnalysisService()

def get_rag_repository_analysis_service() -> RagRepositoryAnalysisService:
    """RagRepositoryAnalysisService 인스턴스를 반환합니다."""
    return RagRepositoryAnalysisService()

def get_rag_code_file_service() -> RagCodeFileService:
    """RagCodeFileService 인스턴스를 반환합니다."""
    return RagCodeFileService()

def get_rag_tech_dependency_service() -> RagTechDependencyService:
    """RagTechDependencyService 인스턴스를 반환합니다."""
    return RagTechDependencyService()

def get_rag_document_analysis_service() -> RagDocumentAnalysisService:
    """RagDocumentAnalysisService 인스턴스를 반환합니다."""
    return RagDocumentAnalysisService()