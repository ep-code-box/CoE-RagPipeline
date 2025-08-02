from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", 
    tags=["🔍 Vector Search"],
    responses={
        200: {"description": "검색 성공"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"}
    }
)


@router.post(
    "/search", 
    response_model=List[dict],
    summary="벡터 유사도 검색",
    description="""
    **ChromaDB 벡터 데이터베이스에서 유사한 문서를 검색합니다.**
    
    ### 🔍 검색 기능
    - **의미적 검색**: 텍스트의 의미를 이해하여 관련 문서 검색
    - **메타데이터 필터링**: 파일 타입, 언어, 태그 등으로 결과 필터링
    - **유사도 점수**: 각 결과의 관련성 점수 제공
    
    ### 📝 사용 예시
    ```bash
    curl -X POST "http://localhost:8001/api/v1/search" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "Python 함수 정의",
        "k": 5,
        "filter_metadata": {
          "file_type": "python"
        }
      }'
    ```
    
    ### 🎯 검색 팁
    - 구체적인 키워드 사용 (예: "FastAPI 라우터" vs "웹 개발")
    - 메타데이터 필터로 결과 범위 제한
    - k 값 조정으로 결과 수 조절 (기본값: 5)
    """,
    response_description="유사한 문서 목록과 유사도 점수"
)
async def search_embeddings(query: str, k: int = 5, filter_metadata: Optional[Dict] = None):
    """벡터 유사도 검색 - 의미적 검색으로 관련 문서를 찾습니다."""
    try:
        from services.embedding_service import EmbeddingService
        from config.settings import settings
        
        embedding_service = EmbeddingService(chroma_persist_directory=settings.CHROMA_PERSIST_DIRECTORY)
        results = embedding_service.search_similar_documents(query, k=k, filter_metadata=filter_metadata)
        return results
    except Exception as e:
        logger.error(f"Failed to search embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.get(
    "/stats", 
    response_model=dict,
    summary="벡터 데이터베이스 통계",
    description="""
    **ChromaDB 벡터 데이터베이스의 통계 정보를 조회합니다.**
    
    ### 📊 제공 정보
    - **총 문서 수**: 저장된 문서의 개수
    - **벡터 차원**: 임베딩 벡터의 차원 수
    - **컬렉션 정보**: 데이터베이스 컬렉션 상태
    - **인덱스 상태**: 검색 인덱스 정보
    
    ### 📝 사용 예시
    ```bash
    curl -X GET "http://localhost:8001/api/v1/stats"
    ```
    
    ### 💡 활용 방법
    - 데이터베이스 상태 모니터링
    - 검색 성능 최적화 참고
    - 저장 용량 관리
    """,
    response_description="벡터 데이터베이스 통계 정보"
)
async def get_embedding_stats():
    """벡터 데이터베이스 통계 조회 - ChromaDB의 상태와 통계를 확인합니다."""
    try:
        from services.embedding_service import EmbeddingService
        from config.settings import settings
        
        embedding_service = EmbeddingService(chroma_persist_directory=settings.CHROMA_PERSIST_DIRECTORY)
        stats = embedding_service.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")