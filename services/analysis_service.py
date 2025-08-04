import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# 실제 분석기 import 추가
from analyzers.git_analyzer import GitAnalyzer
from analyzers.ast_analyzer import ASTAnalyzer

# LLM 서비스 import 추가
from services.llm_service import LLMDocumentService, DocumentType as LLMDocumentType
from services.source_summary_service import SourceSummaryService
from services.embedding_service import EmbeddingService

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
    def find_existing_repository_analysis(
        db: Session,
        repository_url: str,
        branch: str = "main"
    ) -> Optional[RepositoryAnalysis]:
        """기존 레포지토리 분석 결과를 찾습니다."""
        try:
            # 같은 URL과 브랜치로 완료된 분석이 있는지 확인
            return db.query(RepositoryAnalysis).filter(
                RepositoryAnalysis.repository_url == repository_url,
                RepositoryAnalysis.branch == branch,
                RepositoryAnalysis.status == RepositoryStatus.COMPLETED
            ).order_by(RepositoryAnalysis.updated_at.desc()).first()
        except Exception as e:
            logger.error(f"Failed to find existing repository analysis: {e}")
            return None
    
    @staticmethod
    def check_if_analysis_needed(
        db: Session,
        repository_url: str,
        branch: str = "main",
        latest_commit_hash: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        분석이 필요한지 확인합니다.
        
        Returns:
            tuple[bool, Optional[str]]: (분석 필요 여부, 기존 분석 ID)
        """
        try:
            existing_analysis = RagRepositoryAnalysisService.find_existing_repository_analysis(
                db, repository_url, branch
            )
            
            if not existing_analysis:
                # 기존 분석이 없으면 새로운 분석 필요
                logger.info(f"No existing analysis found for {repository_url}:{branch}")
                return True, None
            
            if not latest_commit_hash:
                # commit hash를 확인할 수 없으면 기존 분석 재사용
                logger.info(f"Cannot check commit hash, reusing existing analysis: {existing_analysis.analysis_id}")
                return False, existing_analysis.analysis_id
            
            if not existing_analysis.commit_hash:
                # 기존 분석에 commit hash가 없으면 새로운 분석 필요
                logger.info(f"Existing analysis has no commit hash, new analysis needed for {repository_url}:{branch}")
                return True, None
            
            if existing_analysis.commit_hash != latest_commit_hash:
                # commit hash가 다르면 새로운 분석 필요
                logger.info(f"Commit hash changed for {repository_url}:{branch} - "
                          f"existing: {existing_analysis.commit_hash[:8]}, "
                          f"latest: {latest_commit_hash[:8]}")
                return True, None
            
            # commit hash가 같으면 기존 분석 재사용
            logger.info(f"Same commit hash found, reusing existing analysis: {existing_analysis.analysis_id}")
            return False, existing_analysis.analysis_id
            
        except Exception as e:
            logger.error(f"Failed to check if analysis needed: {e}")
            # 에러 발생 시 안전하게 새로운 분석 수행
            return True, None
    
    @staticmethod
    def get_analysis_by_repository_url(
        db: Session,
        repository_url: str,
        branch: str = "main"
    ) -> Optional[str]:
        """레포지토리 URL로 최신 완료된 분석 ID를 조회합니다."""
        try:
            repo_analysis = RagRepositoryAnalysisService.find_existing_repository_analysis(
                db, repository_url, branch
            )
            return repo_analysis.analysis_id if repo_analysis else None
        except Exception as e:
            logger.error(f"Failed to get analysis by repository URL: {e}")
            return None
    
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
        config_files: Optional[List[str]] = None,
        commit_info: Optional[Dict[str, Any]] = None
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
            
            # Commit 정보 저장
            if commit_info:
                db_repo_analysis.commit_hash = commit_info.get('commit_hash')
                if commit_info.get('commit_date'):
                    from datetime import datetime as dt
                    # ISO 형식의 문자열을 datetime 객체로 변환
                    commit_date_str = commit_info.get('commit_date')
                    if isinstance(commit_date_str, str):
                        try:
                            # ISO 형식 파싱 (timezone 정보 포함)
                            db_repo_analysis.commit_date = dt.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                        except ValueError:
                            logger.warning(f"Failed to parse commit date: {commit_date_str}")
                    else:
                        db_repo_analysis.commit_date = commit_date_str
                db_repo_analysis.commit_author = commit_info.get('author')
                db_repo_analysis.commit_message = commit_info.get('message')
            
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
        
        logger.info(f"Starting analysis for {analysis_id}")

        try:
            # 분석 상태 확인 및 업데이트
            if analysis_id not in analysis_results:
                logger.error(f"Analysis {analysis_id} not found in analysis_results")
                return
            
            analysis_result = analysis_results[analysis_id]
            
            # 분석 상태를 RUNNING으로 변경
            analysis_result.status = AnalysisStatus.RUNNING
            
            # 실제 분석 로직 수행
            try:
                # Git 분석 수행
                logger.info(f"Starting Git analysis for {analysis_id}")
                await self._perform_git_analysis(analysis_id, request, analysis_results)
                
                # AST 분석 수행 (요청된 경우)
                if hasattr(request, 'include_ast') and request.include_ast:
                    logger.info(f"Starting AST analysis for {analysis_id}")
                    await self._perform_ast_analysis(analysis_id, request, analysis_results)
                
                # 기술스펙 분석 수행 (요청된 경우)
                if hasattr(request, 'include_tech_spec') and request.include_tech_spec:
                    logger.info(f"Starting tech spec analysis for {analysis_id}")
                    await self._perform_tech_spec_analysis(analysis_id, request, analysis_results)
                
                # 분석 완료 처리
                analysis_result.status = AnalysisStatus.COMPLETED
                analysis_result.completed_at = datetime.now()
                
                # 데이터베이스에 저장
                try:
                    # 먼저 기본 분석 결과 저장
                    save_analysis_to_db(analysis_result)
                    logger.info(f"Analysis {analysis_id} saved to database")
                    
                    # 각 레포지토리의 상세 분석 결과를 데이터베이스에 저장 (commit 정보 포함)
                    with SessionLocal() as db:
                        for repo in analysis_result.repositories:
                            if hasattr(repo, 'commit_info') and repo.commit_info:
                                try:
                                    # 레포지토리 분석 레코드 생성
                                    repo_analysis = RagRepositoryAnalysisService.create_repository_analysis(
                                        db=db,
                                        analysis_id=analysis_id,
                                        repository_url=str(repo.repository.url),
                                        repository_name=repo.repository.name,
                                        branch=repo.repository.branch or "main",
                                        clone_path=repo.clone_path
                                    )
                                    
                                    # 분석 결과 저장 (commit 정보 포함)
                                    languages = list(set(f.language for f in repo.files if f.language))
                                    RagRepositoryAnalysisService.save_analysis_results(
                                        db=db,
                                        repo_analysis_id=repo_analysis.id,
                                        files_count=len(repo.files),
                                        lines_of_code=repo.code_metrics.lines_of_code if repo.code_metrics else 0,
                                        languages=languages,
                                        config_files=repo.config_files,
                                        documentation_files=repo.documentation_files,
                                        commit_info=repo.commit_info  # commit 정보 전달
                                    )
                                    
                                    logger.info(f"Repository analysis saved with commit info: {repo.repository.url} - {repo.commit_info.get('commit_hash', 'unknown')[:8]}")
                                    
                                except Exception as repo_save_error:
                                    logger.error(f"Failed to save repository analysis for {repo.repository.url}: {repo_save_error}")
                                    continue
                    
                except Exception as e:
                    logger.error(f"Failed to save analysis {analysis_id} to database: {e}")
                    # 데이터베이스 저장 실패는 전체 분석 실패로 처리하지 않음
                
                # LLM 문서 생성 (분석 완료 후 자동 실행)
                try:
                    await self._generate_analysis_documents(analysis_id, analysis_result)
                    logger.info(f"Document generation completed for analysis {analysis_id}")
                except Exception as e:
                    logger.error(f"Document generation failed for analysis {analysis_id}: {e}")
                    # 문서 생성 실패는 전체 분석 실패로 처리하지 않음
                
                logger.info(f"Analysis {analysis_id} completed successfully")
                
            except Exception as e:
                # 분석 중 발생한 오류 처리
                logger.error(f"Error during analysis {analysis_id}: {e}")
                analysis_result.status = AnalysisStatus.FAILED
                analysis_result.error_message = str(e)
                analysis_result.completed_at = datetime.now()
                # 저장 시도
                try:
                    save_analysis_to_db(analysis_result)
                except Exception as save_error:
                    logger.error(f"Failed to save failed analysis to database: {save_error}")
                raise e
                
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {e}")
            if analysis_id in analysis_results:
                analysis_results[analysis_id].status = AnalysisStatus.FAILED
                analysis_results[analysis_id].error_message = str(e)
                analysis_results[analysis_id].completed_at = datetime.now()
                # 저장 시도
                try:
                    save_analysis_to_db(analysis_results[analysis_id])
                except Exception as save_error:
                    logger.error(f"Failed to save failed analysis to database: {save_error}")
            raise

    async def _perform_git_analysis(self, analysis_id: str, request, analysis_results: dict):
        """Git 분석 수행"""
        try:
            logger.info(f"Performing Git analysis for {analysis_id}")
            
            if not hasattr(request, 'repositories') or not request.repositories:
                logger.error("No repositories provided for analysis")
                raise ValueError("No repositories provided for analysis")
            
            # Git 분석 로직 구현
            for repo_info in request.repositories:
                try:
                    # GitRepository 객체의 속성에 접근
                    git_url = str(repo_info.url)  # HttpUrl을 문자열로 변환
                    branch = repo_info.branch if hasattr(repo_info, 'branch') else "main"  # branch가 없으면 기본값 "main" 사용
                    repo_name = repo_info.name if hasattr(repo_info, 'name') else None  # name이 없으면 None
                    
                    if not git_url:  # URL이 비어있으면 건너뛰기
                        logger.warning(f"Empty repository URL found, skipping")
                        continue
                    
                    logger.info(f"Analyzing Git repository: {git_url} (branch: {branch})")
                    
                    # 임시 분석 결과 (실제 구현 시 대체)
                    repo_analysis = {
                        "git_url": git_url,
                        "branch": branch,
                        "name": repo_name,
                        "total_files": 100,  # 실제 파일 수로 대체
                        "total_lines": 5000,  # 실제 라인 수로 대체
                        "languages": ["Python", "JavaScript"],  # 실제 언어 분석 결과로 대체
                        "last_commit": "2024-01-01",  # 실제 마지막 커밋 날짜로 대체
                    }
                    
                    if analysis_id in analysis_results:
                        analysis_results[analysis_id].repositories.append(repo_analysis)
                        logger.info(f"Added analysis results for repository: {git_url}")
                
                except Exception as e:
                    logger.error(f"Error processing repository: {str(e)}")
                    continue
                        
        except Exception as e:
            logger.error(f"Git analysis failed for {analysis_id}: {e}")
            raise
            
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
            
            if not hasattr(request, 'repositories') or not request.repositories:
                logger.error("No repositories provided for analysis")
                raise ValueError("No repositories provided for analysis")
            
            # 실제 Git 분석기 사용
            git_analyzer = GitAnalyzer()
            
            try:
                # Git 분석 로직 구현
                for repo_info in request.repositories:
                    try:
                        # GitRepository 객체의 속성에 접근
                        git_url = str(repo_info.url)  # HttpUrl을 문자열로 변환
                        branch = repo_info.branch or "main"  # branch가 없으면 기본값 "main" 사용
                        repo_name = repo_info.name  # name이 없어도 괜찮음

                        if not git_url:  # URL이 비어있으면 건너뛰기
                            logger.warning(f"Empty repository URL found, skipping")
                            continue

                        logger.info(f"Cloning Git repository: {git_url} (branch: {branch})")
                        
                        # 실제 Git 클론 수행
                        from models.schemas import GitRepository
                        git_repo = GitRepository(url=git_url, branch=branch, name=repo_name)
                        clone_path = git_analyzer.clone_repository(git_repo)
                        
                        # 클론된 레포지토리에서 commit 정보 가져오기
                        commit_info = git_analyzer.get_commit_info_from_cloned_repo(clone_path)
                        logger.info(f"Retrieved commit info for {git_url}: {commit_info.get('commit_hash', 'unknown')[:8]}")
                        
                        # 레포지토리 구조 분석
                        files = git_analyzer.analyze_repository_structure(clone_path)
                        
                        # 설정 파일 찾기
                        config_files = git_analyzer.find_config_files(clone_path)
                        
                        # 문서 파일 찾기
                        doc_files = git_analyzer.find_documentation_files(clone_path)
                        
                        # 실제 분석 결과 생성
                        from models.schemas import RepositoryAnalysis, CodeMetrics
                        repo_analysis = RepositoryAnalysis(
                            repository=git_repo,
                            clone_path=clone_path,
                            files=files,
                            code_metrics=CodeMetrics(
                                lines_of_code=sum(f.lines_of_code or 0 for f in files)
                            ),
                            config_files=config_files,
                            documentation_files=doc_files
                        )
                        
                        # commit 정보를 repo_analysis에 추가 (임시 저장)
                        repo_analysis.commit_info = commit_info
                        
                        if analysis_id in analysis_results:
                            analysis_results[analysis_id].repositories.append(repo_analysis)
                            logger.info(f"Added analysis results for repository: {git_url} ({len(files)} files)")
                    
                    except Exception as e:
                        logger.error(f"Error processing repository {git_url}: {str(e)}")
                        continue
            finally:
                # 분석 완료 후 정리
                git_analyzer.cleanup()
                        
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
        
            if analysis_id in analysis_results and analysis_results[analysis_id].repositories:
                # 실제 AST 분석기 사용
                ast_analyzer = ASTAnalyzer()
                
                updated_repositories = []
                for repo in analysis_results[analysis_id].repositories:
                    try:
                        # RepositoryAnalysis 객체인지 확인
                        if not hasattr(repo, 'clone_path') or not hasattr(repo, 'files'):
                            logger.warning(f"Invalid repository object for AST analysis: {repo}")
                            continue
                        
                        logger.info(f"Performing AST analysis for repository: {repo.repository.url}")
                        
                        # 실제 AST 분석 수행
                        ast_results = ast_analyzer.analyze_files(repo.clone_path, repo.files)
                        
                        # AST 분석 결과를 저장소에 저장
                        repo.ast_analysis = ast_results
                        
                        # 코드 메트릭스 계산
                        total_complexity = 0
                        total_functions = 0
                        
                        for file_path, ast_nodes in ast_results.items():
                            for node in ast_nodes:
                                if hasattr(node, 'metadata') and node.metadata:
                                    complexity = node.metadata.get('complexity_score', 0)
                                    if complexity:
                                        total_complexity += complexity
                                        total_functions += 1
                        
                        # 평균 복잡도 계산
                        if total_functions > 0:
                            avg_complexity = total_complexity / total_functions
                            repo.code_metrics.cyclomatic_complexity = avg_complexity
                        
                        updated_repositories.append(repo)
                        logger.info(f"AST analysis completed for repository: {repo.repository.url} ({len(ast_results)} files analyzed)")
                    
                    except Exception as e:
                        logger.error(f"Error processing AST analysis for repository: {str(e)}")
                        # 실패한 경우에도 원본 repo를 유지
                        updated_repositories.append(repo)
                        continue
            
                # 업데이트된 저장소 목록으로 교체
                analysis_results[analysis_id].repositories = updated_repositories
                
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
            if analysis_id in analysis_results and analysis_results[analysis_id].repositories:
                from models.schemas import GitRepository, RepositoryAnalysis, TechSpec, CodeMetrics
                updated_repositories = []

                for repo_dict in analysis_results[analysis_id].repositories:
                    try:
                        # Dictionary를 RepositoryAnalysis 객체로 변환
                        if isinstance(repo_dict, dict):
                            git_repo = GitRepository(
                                url=repo_dict["git_url"],
                                branch=repo_dict.get("branch", "main"),
                                name=repo_dict.get("name")
                            )
                            repo = RepositoryAnalysis(
                                repository=git_repo,
                                clone_path="",  # 실제 클론 경로로 대체 필요
                                code_metrics=CodeMetrics()
                            )
                        else:
                            repo = repo_dict

                        # 기술 스펙 분석 수행
                        tech_spec = TechSpec(
                            language="Python",
                            framework="FastAPI",
                            dependencies=["sqlalchemy", "pydantic", "fastapi"],
                            version="3.9",
                            package_manager="pip"
                        )
                        
                        # tech_specs 리스트에 추가
                        repo.tech_specs.append(tech_spec)
                        
                        # 코드 메트릭스 업데이트
                        repo.code_metrics.maintainability_index = 85.0  # 실제 값으로 대체
                        repo.code_metrics.cyclomatic_complexity = 7.5   # 실제 값으로 대체
                        
                        updated_repositories.append(repo)
                        logger.info(f"Tech spec analysis completed for repository: {repo.repository.url}")
                        
                    except Exception as e:
                        logger.error(f"Error processing tech spec analysis for repository: {str(e)}")
                        continue
                
                # 업데이트된 저장소 목록으로 교체
                analysis_results[analysis_id].repositories = updated_repositories
                    
        except Exception as e:
            logger.error(f"Tech spec analysis failed for {analysis_id}: {e}")
            raise
    
    async def _generate_analysis_documents(self, analysis_id: str, analysis_result):
        """분석 완료 후 LLM을 사용하여 문서를 자동 생성합니다 (소스코드 요약 포함)."""
        try:
            logger.info(f"Starting enhanced document generation for analysis {analysis_id}")
            
            # 서비스 초기화
            llm_service = LLMDocumentService()
            summary_service = SourceSummaryService()
            embedding_service = EmbeddingService()
            
            # 분석 결과를 딕셔너리로 변환
            analysis_data = {
                "analysis_id": analysis_id,
                "repositories": [],
                "tech_specs": [],
                "ast_analysis": {},
                "code_metrics": {}
            }
            
            # 저장소 정보 추출 및 소스코드 요약 수행
            source_summaries = None
            clone_paths = []
            
            if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
                for repo in analysis_result.repositories:
                    repo_data = {
                        "url": repo.repository.url if hasattr(repo, 'repository') else "Unknown",
                        "branch": repo.repository.branch if hasattr(repo, 'repository') else "main",
                        "name": repo.repository.name if hasattr(repo, 'repository') else None
                    }
                    analysis_data["repositories"].append(repo_data)
                    
                    # 클론 경로 수집 (소스코드 요약용)
                    if hasattr(repo, 'clone_path') and repo.clone_path:
                        clone_paths.append(repo.clone_path)
                    
                    # 기술 스펙 정보 추가
                    if hasattr(repo, 'tech_specs') and repo.tech_specs:
                        for tech_spec in repo.tech_specs:
                            tech_data = {
                                "name": tech_spec.language if hasattr(tech_spec, 'language') else "Unknown",
                                "version": tech_spec.version if hasattr(tech_spec, 'version') else "Unknown",
                                "framework": tech_spec.framework if hasattr(tech_spec, 'framework') else None,
                                "dependencies": tech_spec.dependencies if hasattr(tech_spec, 'dependencies') else []
                            }
                            analysis_data["tech_specs"].append(tech_data)
                    
                    # AST 분석 정보 추가
                    if hasattr(repo, 'ast_analysis') and repo.ast_analysis:
                        analysis_data["ast_analysis"].update(repo.ast_analysis)
                    
                    # 코드 메트릭 정보 추가
                    if hasattr(repo, 'code_metrics') and repo.code_metrics:
                        metrics = repo.code_metrics
                        analysis_data["code_metrics"] = {
                            "total_files": metrics.total_files if hasattr(metrics, 'total_files') else 0,
                            "total_lines": metrics.total_lines if hasattr(metrics, 'total_lines') else 0,
                            "cyclomatic_complexity": metrics.cyclomatic_complexity if hasattr(metrics, 'cyclomatic_complexity') else 0,
                            "maintainability_index": metrics.maintainability_index if hasattr(metrics, 'maintainability_index') else 0
                        }
            
            # 소스코드 요약 수행 (첫 번째 클론 경로 사용)
            if clone_paths:
                try:
                    logger.info(f"Starting source code summarization for analysis {analysis_id}")
                    source_summaries = await summary_service.summarize_repository_sources(
                        clone_path=clone_paths[0],
                        analysis_id=analysis_id,
                        max_files=100,  # 성능을 위해 최대 100개 파일로 제한
                        batch_size=5
                    )
                    
                    # 소스코드 요약을 vectorDB에 저장
                    if source_summaries and source_summaries.get("summaries"):
                        embedding_result = embedding_service.embed_source_summaries(
                            summaries=source_summaries,
                            analysis_id=analysis_id
                        )
                        logger.info(f"Source summaries embedded: {embedding_result}")
                    
                except Exception as e:
                    logger.error(f"Failed to summarize source code for analysis {analysis_id}: {str(e)}")
                    # 요약 실패해도 기존 방식으로 문서 생성 계속 진행
                    source_summaries = None
            
            # 기본 문서 타입들 자동 생성
            default_document_types = [
                LLMDocumentType.DEVELOPMENT_GUIDE,
                LLMDocumentType.TECHNICAL_SPECIFICATION,
                LLMDocumentType.ARCHITECTURE_OVERVIEW
            ]
            
            # 소스코드 요약이 있으면 향상된 방식으로, 없으면 기존 방식으로 문서 생성
            generated_documents = []
            
            for doc_type in default_document_types:
                try:
                    if source_summaries and source_summaries.get("summaries"):
                        # 소스코드 요약을 포함한 향상된 문서 생성
                        doc = await llm_service.generate_document_with_source_summaries(
                            analysis_data=analysis_data,
                            source_summaries=source_summaries,
                            document_type=doc_type,
                            language="korean"
                        )
                    else:
                        # 기존 방식으로 문서 생성
                        doc = await llm_service.generate_document(
                            analysis_data=analysis_data,
                            document_type=doc_type,
                            language="korean"
                        )
                    
                    generated_documents.append(doc)
                    
                except Exception as e:
                    logger.error(f"Failed to generate document {doc_type}: {str(e)}")
                    # 실패한 문서도 결과에 포함 (오류 정보와 함께)
                    generated_documents.append({
                        "document_type": doc_type,
                        "language": "korean",
                        "error": str(e),
                        "generated_at": datetime.now().isoformat(),
                        "analysis_id": analysis_id
                    })
            
            # 생성된 문서들을 파일로 저장
            import os
            documents_dir = f"output/documents/{analysis_id}"
            os.makedirs(documents_dir, exist_ok=True)
            
            for doc in generated_documents:
                if "error" not in doc:  # 성공적으로 생성된 문서만 저장
                    doc_filename = f"{doc['document_type']}_{doc['language']}.md"
                    doc_path = os.path.join(documents_dir, doc_filename)
                    
                    with open(doc_path, 'w', encoding='utf-8') as f:
                        f.write(doc['content'])
                    
                    logger.info(f"Enhanced document saved: {doc_path}")
                else:
                    logger.error(f"Failed to generate document {doc['document_type']}: {doc.get('error')}")
            
            # 문서 생성 결과를 분석 결과에 추가
            analysis_result.generated_documents = generated_documents
            
            # 백워드 호환성을 위해 source_summaries_used 필드가 있는지 확인 후 설정
            try:
                # Pydantic 모델에서 안전하게 필드 설정
                if hasattr(analysis_result, 'source_summaries_used'):
                    analysis_result.source_summaries_used = source_summaries is not None
                else:
                    # 필드가 없는 경우 새로운 AnalysisResult 객체 생성
                    from models.schemas import AnalysisResult
                    
                    # 기존 데이터를 딕셔너리로 변환
                    result_dict = analysis_result.model_dump() if hasattr(analysis_result, 'model_dump') else analysis_result.dict()
                    
                    # source_summaries_used 필드 추가
                    result_dict['source_summaries_used'] = source_summaries is not None
                    
                    # 새로운 객체로 교체
                    analysis_result = AnalysisResult(**result_dict)
                    
                    # 메모리 캐시 업데이트 (analysis_results가 전역 변수인 경우)
                    try:
                        from routers.analysis import analysis_results
                        if analysis_id in analysis_results:
                            analysis_results[analysis_id] = analysis_result
                    except ImportError:
                        pass  # analysis_results를 import할 수 없는 경우 무시
                        
            except Exception as e:
                logger.warning(f"Could not set source_summaries_used field: {e}")
                # 필드 설정에 실패해도 문서 생성은 계속 진행
            
            logger.info(f"Document generation completed for analysis {analysis_id}. Generated {len([d for d in generated_documents if 'error' not in d])} documents.")
            
        except Exception as e:
            logger.error(f"Document generation failed for analysis {analysis_id}: {e}")
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
                
                # 백워드 호환성을 위해 source_summaries_used 필드가 없으면 기본값 설정
                if 'source_summaries_used' not in data:
                    data['source_summaries_used'] = False
                
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
                    error_message=db_result.error_message,
                    source_summaries_used=False  # 기존 데이터는 소스 요약을 사용하지 않았으므로 False로 설정
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