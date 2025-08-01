from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
import logging

from models.schemas import (
    AnalysisRequest, 
    AnalysisResult, 
    AnalysisStatus
)
from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])

# 메모리 캐시 (성능 향상을 위해 유지, 데이터베이스와 함께 사용)
analysis_results = {}

@router.post("/analyze", response_model=dict)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Git 주소 목록을 받아 전체 분석 수행"""
    try:
        from services.analysis_service import AnalysisService
        
        # 분석 ID 생성
        analysis_id = request.analysis_id or str(uuid.uuid4())
        
        # 분석 결과 초기화
        analysis_result = AnalysisResult(
            analysis_id=analysis_id,
            status=AnalysisStatus.PENDING,
            created_at=datetime.now(),
            repositories=[],
            correlation_analysis=None
        )
        
        # 메모리 캐시에 저장
        analysis_results[analysis_id] = analysis_result
        
        # 백그라운드에서 분석 실행 (데이터베이스 세션도 전달)
        analysis_service = AnalysisService()
        background_tasks.add_task(analysis_service.perform_analysis, analysis_id, request, analysis_results, db)
        
        return {
            "analysis_id": analysis_id,
            "status": "started",
            "message": "분석이 시작되었습니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요."
        }
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}")
        raise HTTPException(status_code=500, detail=f"분석 시작 중 오류가 발생했습니다: {str(e)}")


@router.get("/results/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_result(analysis_id: str, db: Session = Depends(get_db)):
    """분석 결과 조회"""
    try:
        from services.analysis_service import AnalysisService
        
        analysis_service = AnalysisService()
        
        # 먼저 메모리 캐시에서 확인
        if analysis_id in analysis_results:
            return analysis_results[analysis_id]
        
        # 메모리에 없으면 데이터베이스에서 로드 시도
        result = analysis_service.load_analysis_result_from_db(analysis_id, db)
        if result:
            analysis_results[analysis_id] = result  # 메모리에 캐시
            return result
        
        # 데이터베이스에도 없으면 디스크에서 로드 시도 (백워드 호환성)
        result = analysis_service.load_analysis_result(analysis_id)
        if result:
            analysis_results[analysis_id] = result  # 메모리에 캐시
            return result
        
        # 모든 곳에서 찾지 못하면 404 에러
        available_ids = list(analysis_results.keys())
        error_detail = {
            "message": "분석 결과를 찾을 수 없습니다.",
            "analysis_id": analysis_id,
            "available_analysis_ids": available_ids[:5],  # 최대 5개만 표시
            "total_available": len(available_ids),
            "suggestions": [
                "1. 올바른 analysis_id를 사용하고 있는지 확인하세요.",
                "2. /results 엔드포인트로 사용 가능한 분석 결과 목록을 확인하세요.",
                "3. 분석이 아직 진행 중이거나 실패했을 수 있습니다.",
                "4. 분석 ID 형식이 올바른지 확인하세요 (UUID 형식)."
            ]
        }
        raise HTTPException(status_code=404, detail=error_detail)
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis result for {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=f"분석 결과 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/results", response_model=List[dict])
async def list_analysis_results(db: Session = Depends(get_db)):
    """모든 분석 결과 목록 조회"""
    try:
        from services.analysis_service import AnalysisService
        
        analysis_service = AnalysisService()
        
        # 데이터베이스에서 모든 분석 결과 조회
        db_results = analysis_service.get_all_analysis_results_from_db(db)
        
        # 메모리 캐시의 결과와 병합
        all_results = {}
        
        # 데이터베이스 결과 추가
        for result in db_results:
            all_results[result.analysis_id] = {
                "analysis_id": result.analysis_id,
                "status": result.status,
                "created_at": result.analysis_date,
                "completed_at": result.completed_at,
                "repository_count": result.repository_count,
                "source": "database"
            }
        
        # 메모리 캐시 결과 추가/업데이트
        for result in analysis_results.values():
            all_results[result.analysis_id] = {
                "analysis_id": result.analysis_id,
                "status": result.status,
                "created_at": result.created_at,
                "completed_at": result.completed_at,
                "repository_count": len(result.repositories),
                "source": "memory"
            }
        
        return list(all_results.values())
    except Exception as e:
        logger.error(f"Failed to list analysis results: {e}")
        raise HTTPException(status_code=500, detail=f"분석 결과 목록 조회 중 오류가 발생했습니다: {str(e)}")