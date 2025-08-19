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
from analyzers.enhanced import EnhancedAnalyzer, TreeSitterAnalyzer
from analyzers.tech_spec_analyzer import TechSpecAnalyzer

# LLM 서비스 import 추가
from services.llm_service import LLMDocumentService, DocumentType as LLMDocumentType
from services.source_summary_service import SourceSummaryService
from services.embedding_service import EmbeddingService
from services.analysis_result_service import AnalysisResultService
from services.document_generation_service import DocumentGenerationService

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
from services.rag_analysis_service import RagAnalysisService
from services.rag_repository_analysis_service import RagRepositoryAnalysisService
from services.rag_code_file_service import RagCodeFileService
from services.rag_tech_dependency_service import RagTechDependencyService
from services.rag_document_analysis_service import RagDocumentAnalysisService

# 메인 분석 서비스 클래스
class AnalysisService:
    """메인 분석 서비스 - 전체 분석 프로세스를 관리합니다."""
    
    def __init__(self):
        self.rag_analysis_service = RagAnalysisService()
        self.analysis_result_service = AnalysisResultService()
    
    async def perform_analysis(self, analysis_id: str, request, analysis_results: dict, db: Session):
        """백그라운드에서 분석을 수행합니다."""
        from models.schemas import AnalysisStatus
        from core.database import save_analysis_to_db
        
        logger.info(f"Starting analysis for {analysis_id}")
        
        # Git 분석기 인스턴스를 메서드 전체에서 사용하기 위해 여기서 초기화
        git_analyzer = None

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
                git_analyzer = GitAnalyzer()
                await git_analyzer.perform_repository_analysis(analysis_id, request, analysis_results)
                
                # AST 분석 수행 (요청된 경우)
                if hasattr(request, 'include_ast') and request.include_ast:
                    logger.info(f"Starting AST analysis for {analysis_id}")
                    ast_analyzer = ASTAnalyzer()
                    await ast_analyzer.perform_analysis(analysis_id, request, analysis_results)
                
                # 기술스펙 분석 수행 (요청된 경우)
                if hasattr(request, 'include_tech_spec') and request.include_tech_spec:
                    logger.info(f"Starting tech spec analysis for {analysis_id}")
                    tech_spec_analyzer = TechSpecAnalyzer()
                    await tech_spec_analyzer.perform_analysis(analysis_id, request, analysis_results)
                
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
                                    ast_data_json = json.dumps(repo.ast_analysis, default=lambda o: o.__dict__, indent=2) if repo.ast_analysis else None

                                    RagRepositoryAnalysisService.save_analysis_results(
                                        db=db,
                                        repo_analysis_id=repo_analysis.id,
                                        files_count=len(repo.files),
                                        lines_of_code=repo.code_metrics.lines_of_code if repo.code_metrics else 0,
                                        languages=languages,
                                        config_files=repo.config_files,
                                        documentation_files=repo.documentation_files,
                                        commit_info=repo.commit_info,  # commit 정보 전달
                                        ast_data=ast_data_json
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
                    document_generation_service = DocumentGenerationService()
                    await document_generation_service.generate_documents(analysis_id, analysis_result)
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
        finally:
            # 모든 분석이 완료된 후 클론된 레포지토리 정리
            if git_analyzer:
                try:
                    git_analyzer.cleanup()
                    logger.info(f"Cleaned up cloned repositories for analysis {analysis_id}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup repositories for analysis {analysis_id}: {cleanup_error}")
