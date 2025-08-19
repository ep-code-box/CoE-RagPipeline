import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from core.database import AnalysisRequest, AnalysisStatus

logger = logging.getLogger(__name__)

class RagAnalysisService:
    """RAG 파이프라인 분석 서비스"""
    
    @staticmethod
    def create_analysis_request(
        db: Session, 
        repositories: List[Dict[str, Any]], 
        include_ast: bool = True,
        include_tech_spec: bool = True,
        include_correlation: bool = True,
        group_name: Optional[str] = None,
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
                group_name=group_name,
                status=AnalysisStatus.PENDING,
                
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