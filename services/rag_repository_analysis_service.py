import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import json

from core.database import RepositoryAnalysis, RepositoryStatus, DependencyType

logger = logging.getLogger(__name__)

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