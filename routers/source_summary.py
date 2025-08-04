from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from services.source_summary_service import SourceSummaryService
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/source-summary",
    tags=["📝 Source Code Summary"],
    responses={
        200: {"description": "요약 성공"},
        400: {"description": "잘못된 요청"},
        404: {"description": "요약 결과를 찾을 수 없음"},
        500: {"description": "서버 오류"}
    }
)

# 서비스 인스턴스
source_summary_service = SourceSummaryService()
embedding_service = EmbeddingService()


@router.post(
    "/summarize-file",
    response_model=Dict[str, Any],
    summary="단일 소스파일 요약",
    description="""
    **단일 소스코드 파일을 LLM을 통해 요약합니다.**
    
    ### 📝 기능
    - 소스코드 구조 분석
    - 주요 함수/클래스 추출
    - 설계 패턴 식별
    - 개발 가이드 관련 특징 요약
    
    ### 지원 언어
    Python, JavaScript, TypeScript, Java, Kotlin, Swift, Go, Rust, C++, C#, PHP, Ruby 등
    """
)
async def summarize_source_file(
    file_path: str = Query(..., description="요약할 소스파일 경로"),
    max_tokens: int = Query(1000, description="최대 토큰 수"),
    use_cache: bool = Query(True, description="캐시 사용 여부")
):
    """단일 소스파일을 요약합니다."""
    try:
        logger.info(f"Starting source file summarization: {file_path}")
        
        result = await source_summary_service.summarize_source_file(
            file_path=file_path,
            max_tokens=max_tokens,
            use_cache=use_cache
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail=f"파일을 요약할 수 없습니다: {file_path}"
            )
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to summarize source file {file_path}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"소스파일 요약 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/summarize-directory",
    response_model=Dict[str, Any],
    summary="디렉토리 내 소스파일들 일괄 요약",
    description="""
    **디렉토리 내의 모든 소스코드 파일을 일괄 요약합니다.**
    
    ### 📝 기능
    - 배치 처리로 효율적인 요약
    - 지원 언어 자동 감지
    - 진행 상황 추적
    - 실패한 파일 리포트
    """
)
async def summarize_directory(
    directory_path: str = Query(..., description="요약할 디렉토리 경로"),
    max_files: int = Query(100, description="최대 처리할 파일 수"),
    batch_size: int = Query(5, description="배치 처리 크기")
):
    """디렉토리 내 소스파일들을 일괄 요약합니다."""
    try:
        logger.info(f"Starting directory summarization: {directory_path}")
        
        result = await source_summary_service.summarize_directory(
            directory_path=directory_path,
            max_files=max_files,
            batch_size=batch_size
        )
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to summarize directory {directory_path}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"디렉토리 요약 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/summarize-repository/{analysis_id}",
    response_model=Dict[str, Any],
    summary="레포지토리 소스코드 요약",
    description="""
    **분석된 레포지토리의 모든 소스코드를 요약하고 vectorDB에 저장합니다.**
    
    ### 📝 기능
    - 레포지토리 전체 소스코드 요약
    - 요약 결과 영구 저장
    - vectorDB 임베딩 저장
    - 통계 정보 생성
    """
)
async def summarize_repository_sources(
    analysis_id: str,
    clone_path: str = Query(..., description="클론된 레포지토리 경로"),
    max_files: int = Query(100, description="최대 처리할 파일 수"),
    batch_size: int = Query(5, description="배치 처리 크기"),
    embed_to_vector_db: bool = Query(True, description="vectorDB에 임베딩 저장 여부")
):
    """레포지토리의 소스코드를 요약하고 vectorDB에 저장합니다."""
    try:
        logger.info(f"Starting repository source summarization for analysis {analysis_id}")
        
        # 소스코드 요약 수행
        summary_result = await source_summary_service.summarize_repository_sources(
            clone_path=clone_path,
            analysis_id=analysis_id,
            max_files=max_files,
            batch_size=batch_size
        )
        
        # vectorDB에 임베딩 저장
        embedding_result = None
        if embed_to_vector_db and summary_result.get("summaries"):
            try:
                embedding_result = await embedding_service.embed_source_summaries(
                    summaries=summary_result,
                    analysis_id=analysis_id
                )
                logger.info(f"Successfully embedded {embedding_result.get('embedded_count', 0)} source summaries to vectorDB")
            except Exception as e:
                logger.error(f"Failed to embed source summaries to vectorDB: {e}")
                # 임베딩 실패해도 요약 결과는 반환
        
        # 통계 정보 생성
        statistics = source_summary_service.get_summary_statistics(summary_result)
        
        return {
            "status": "success",
            "data": {
                "summary_result": summary_result,
                "embedding_result": embedding_result,
                "statistics": statistics
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to summarize repository sources for analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"레포지토리 소스코드 요약 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/summaries/{analysis_id}",
    response_model=Dict[str, Any],
    summary="저장된 요약 결과 조회",
    description="""
    **저장된 레포지토리 소스코드 요약 결과를 조회합니다.**
    
    ### 📝 기능
    - 저장된 요약 결과 로드
    - 통계 정보 포함
    - 캐시된 결과 활용
    """
)
async def get_repository_summaries(analysis_id: str):
    """저장된 레포지토리 요약 결과를 조회합니다."""
    try:
        logger.info(f"Loading repository summaries for analysis {analysis_id}")
        
        summaries = source_summary_service.load_repository_summaries(analysis_id)
        
        if not summaries:
            raise HTTPException(
                status_code=404,
                detail=f"분석 ID {analysis_id}에 대한 요약 결과를 찾을 수 없습니다."
            )
        
        # 통계 정보 생성
        statistics = source_summary_service.get_summary_statistics(summaries)
        
        return {
            "status": "success",
            "data": {
                "summaries": summaries,
                "statistics": statistics
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load repository summaries for analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"요약 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/search/{analysis_id}",
    response_model=Dict[str, Any],
    summary="소스코드 요약 검색",
    description="""
    **vectorDB에서 소스코드 요약을 검색합니다.**
    
    ### 📝 기능
    - 의미적 유사도 검색
    - 관련 소스코드 요약 반환
    - 검색 결과 랭킹
    """
)
async def search_source_summaries(
    analysis_id: str,
    query: str = Query(..., description="검색 쿼리"),
    top_k: int = Query(10, description="반환할 최대 결과 수")
):
    """vectorDB에서 소스코드 요약을 검색합니다."""
    try:
        logger.info(f"Searching source summaries for analysis {analysis_id} with query: {query}")
        
        search_results = await embedding_service.search_source_summaries(
            query=query,
            analysis_id=analysis_id,
            top_k=top_k
        )
        
        return {
            "status": "success",
            "data": {
                "query": query,
                "results": search_results,
                "result_count": len(search_results)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to search source summaries for analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"소스코드 요약 검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/cache/stats",
    response_model=Dict[str, Any],
    summary="캐시 통계 조회",
    description="""
    **소스코드 요약 캐시 통계 정보를 조회합니다.**
    
    ### 📝 기능
    - 메모리 캐시 상태
    - 영구 캐시 상태
    - 캐시 사용량 통계
    """
)
async def get_cache_stats():
    """캐시 통계 정보를 조회합니다."""
    try:
        stats = source_summary_service.get_cache_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"캐시 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/cache/cleanup",
    response_model=Dict[str, Any],
    summary="캐시 정리",
    description="""
    **오래된 캐시 파일들을 정리합니다.**
    
    ### 📝 기능
    - 오래된 캐시 파일 삭제
    - 캐시 공간 확보
    - 정리 결과 리포트
    """
)
async def cleanup_cache(
    max_age_days: int = Query(7, description="캐시 파일 최대 보관 일수")
):
    """오래된 캐시 파일들을 정리합니다."""
    try:
        logger.info(f"Starting cache cleanup with max_age_days: {max_age_days}")
        
        source_summary_service.cleanup_cache(max_age_days=max_age_days)
        
        # 정리 후 통계 조회
        stats = source_summary_service.get_cache_stats()
        
        return {
            "status": "success",
            "message": f"{max_age_days}일 이상된 캐시 파일들을 정리했습니다.",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"캐시 정리 중 오류가 발생했습니다: {str(e)}"
        )