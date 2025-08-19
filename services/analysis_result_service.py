import os
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from models.schemas import AnalysisResult, AnalysisStatus
from core.database import SessionLocal, RagAnalysisResult

logger = logging.getLogger(__name__)

class AnalysisResultService:
    """분석 결과를 로드하고 관리하는 서비스"""

    def __init__(self):
        pass

    def load_analysis_result(self, analysis_id: str) -> Optional[AnalysisResult]:
        """분석 결과를 로드합니다 (데이터베이스 우선, JSON 파일 백워드 호환성)."""
        # 먼저 데이터베이스에서 로드 시도
        try:
            with SessionLocal() as db:
                db_result = self.load_analysis_result_from_db(analysis_id, db)
                if db_result:
                    logger.info(f"Analysis result loaded from database: {analysis_id} with {len(db_result.repositories)} repositories")
                    return db_result
        except Exception as e:
            logger.warning(f"Failed to load analysis result from database: {e}")
        
        # 데이터베이스에서 로드 실패 시 JSON 파일에서 로드 시도 (백워드 호환성)
        try:
            output_dir = "output/results"
            filepath = os.path.join(output_dir, f"{analysis_id}.json")
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 백워드 호환성을 위해 source_summaries_used 필드가 없으면 기본값 설정
                if 'source_summaries_used' not in data:
                    data['source_summaries_used'] = False
                
                logger.info(f"Analysis result loaded from JSON file: {analysis_id}")
                return AnalysisResult(**data)
            
            logger.warning(f"Analysis result not found in database or JSON file: {analysis_id}")
            return None
        except Exception as e:
            logger.error(f"Error loading analysis result from disk: {e}")
            return None
    
    def load_analysis_result_from_db(self, analysis_id: str, db: Session) -> Optional[AnalysisResult]:
        """데이터베이스에서 분석 결과를 로드합니다."""
        try:
            db_result = db.query(RagAnalysisResult).filter(
                RagAnalysisResult.analysis_id == analysis_id
            ).first()
            
            if db_result:
                # 저장소 데이터 파싱
                repositories_data = []
                if db_result.repositories_data:
                    try:
                        repositories_data = json.loads(db_result.repositories_data)
                        logger.debug(f"Raw repositories_data from DB: {db_result.repositories_data}")
                        logger.debug(f"Parsed {len(repositories_data)} repositories from database for analysis {analysis_id}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse repositories_data for analysis {analysis_id}: {e}")
                        repositories_data = []
                else:
                    logger.warning(f"repositories_data is None or empty for analysis {analysis_id}")
                
                # 연관성 분석 데이터 파싱
                correlation_analysis = None
                if db_result.correlation_data:
                    try:
                        correlation_analysis = json.loads(db_result.correlation_data)
                        logger.debug(f"Loaded correlation analysis from database for analysis {analysis_id}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse correlation_data for analysis {analysis_id}: {e}")
                
                # 상태 값 변환 (데이터베이스의 enum과 스키마의 enum 매핑)
                status_mapping = {
                    'PENDING': 'pending',
                    'RUNNING': 'running', 
                    'COMPLETED': 'completed',
                    'FAILED': 'failed'
                }
                
                # 데이터베이스 상태를 스키마 상태로 변환
                db_status = db_result.status.value if hasattr(db_result.status, 'value') else str(db_result.status)
                schema_status = status_mapping.get(db_status, db_status.lower())
                
                # 데이터베이스 결과를 AnalysisResult 모델로 변환
                result = AnalysisResult(
                    analysis_id=db_result.analysis_id,
                    status=AnalysisStatus(schema_status),
                    created_at=db_result.analysis_date,
                    completed_at=db_result.completed_at,
                    repositories=repositories_data,
                    correlation_analysis=correlation_analysis,
                    error_message=db_result.error_message,
                    source_summaries_used=False  # 기존 데이터는 소스 요약을 사용하지 않았으므로 False로 설정
                )
                
                logger.info(f"Successfully loaded analysis result from database: {analysis_id} with {len(repositories_data)} repositories")
                return result
            
            logger.warning(f"No analysis result found in database for analysis_id: {analysis_id}")
            return None
        except Exception as e:
            logger.error(f"Error loading analysis result from database for {analysis_id}: {e}")
            return None
    
    def get_all_analysis_results_from_db(self, db: Session) -> List[RagAnalysisResult]:
        """데이터베이스에서 모든 분석 결과를 조회합니다."""
        try:
            return db.query(RagAnalysisResult).all()
        except Exception as e:
            logger.error(f"Error loading all analysis results from database: {e}")
            return []
    
    def load_all_analysis_results(self) -> Dict[str, AnalysisResult]:
        """모든 분석 결과를 로드합니다 (디스크에서)."""
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
            logger.error(f"Error loading all analysis results: {e}")
        
        return results
