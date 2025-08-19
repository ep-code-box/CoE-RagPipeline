from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional, Dict, Any
import os
import logging

from models.schemas import SearchRequest # SearchRequest 모델 임포트

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
    - **분석 결과별 검색**: analysis_id로 특정 분석 결과만 검색
    - **최신 commit 우선 검색**: repository_url로 최신 commit 분석 결과 우선 검색 ⭐ **NEW**
    - **그룹명으로 검색**: group_name으로 특정 그룹에 속한 레포지토리 분석 결과 검색 ⭐ **NEW**
    - **유사도 점수**: 각 결과의 관련성 점수 제공
    
    ### 📝 사용 예시
    ```bash
    # 일반 검색
    curl -X POST "http://localhost:8001/api/v1/search" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "Python 함수 정의",
        "k": 5,
        "filter_metadata": {
          "file_type": "python"
        }
      }'
    
    # 특정 분석 결과에서만 검색
    curl -X POST "http://localhost:8001/api/v1/search" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "Python 함수 정의",
        "k": 5,
        "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c"
      }'
    
    # 특정 레포지토리의 최신 commit 분석 결과에서 검색 (NEW!)
    curl -X POST "http://localhost:8001/api/v1/search" \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "Python 함수 정의",
        "k": 5,
        "repository_url": "https://github.com/octocat/Hello-World.git"
      }

    # 특정 그룹명으로 검색 (NEW!)
    curl -X POST "http://localhost:8001/api/v1/search" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "결제 모듈",
        "k": 5,
        "group_name": "PaymentServiceTeam"
      }'
    
    ### 🎯 검색 팁
    - 구체적인 키워드 사용 (예: "FastAPI 라우터" vs "웹 개발")
    - analysis_id로 특정 분석 결과만 검색하여 정확도 향상
    - group_name으로 특정 그룹에 속한 레포지토리 분석 결과만 검색 ⭐ **NEW** # <-- 설명 추가
    - 메타데이터 필터로 결과 범위 제한
    - k 값 조정으로 결과 수 조절 (기본값: 5)
    """,
    response_description="유사한 문서 목록과 유사도 점수"
)
async def search_embeddings(request: SearchRequest = Body(...)):
    """벡터 유사도 검색 - 의미적 검색으로 관련 문서를 찾습니다."""
    try:
        from services.embedding_service import EmbeddingService
        from config.settings import settings
        
        query = request.query
        k = request.k
        filter_metadata = request.filter_metadata
        analysis_id = request.analysis_id
        repository_url = request.repository_url
        group_name = request.group_name

        # analysis_id가 제공된 경우 필터에 추가
        if analysis_id:
            if filter_metadata is None:
                filter_metadata = {}
            filter_metadata["analysis_id"] = analysis_id
            logger.info(f"Searching with analysis_id filter: {analysis_id}")
        
        # group_name이 제공된 경우 필터에 추가
        if group_name:
            if filter_metadata is None:
                filter_metadata = {}
            filter_metadata["group_name"] = group_name
            logger.info(f"Searching with group_name filter: {group_name}")

        embedding_service = EmbeddingService()
        results = embedding_service.search_similar_documents(
            query, 
            k=k, 
            filter_metadata=filter_metadata, 
            repository_url=repository_url  # 최신 commit 분석 결과 우선 검색
        )
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
        
        embedding_service = EmbeddingService()
        stats = embedding_service.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")

@router.post(
    "/embed_rdb_schema",
    response_model=Dict[str, Any],
    summary="RDB 스키마 임베딩",
    description="""
    **MariaDB 데이터베이스의 스키마(테이블, 컬럼) 정보를 추출하여 임베딩하고 ChromaDB에 저장합니다.**
    
    이 작업을 통해 RDB의 구조를 자연어 쿼리로 검색할 수 있게 됩니다.
    """,
    response_description="임베딩 작업 결과"
)
async def embed_rdb_schema():
    """RDB 스키마를 임베딩하여 벡터 저장소에 추가합니다."""
    try:
        from services.rdb_embedding_service import RDBEmbeddingService
        rdb_embedding_service = RDBEmbeddingService()
        result = rdb_embedding_service.extract_and_embed_schema()
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        return result
    except Exception as e:
        logger.error(f"Failed to embed RDB schema: {e}")
        raise HTTPException(status_code=500, detail=f"RDB 스키마 임베딩 중 오류가 발생했습니다: {str(e)}")

@router.post("/embeddings", response_model=EmbeddingResponse, summary="텍스트 임베딩 생성 (OpenAI 호환)")
async def create_text_embeddings(request: EmbeddingRequest):
    """
    OpenAI 호환 형식으로 텍스트 임베딩을 생성합니다.
    """
    try:
        if isinstance(request.input, str):
            texts = [request.input]
        else:
            texts = request.input

        embedding_service = EmbeddingService()
        
        # Use the new create_embeddings method
        embeddings_vectors = embedding_service.create_embeddings(texts)
        
        embedding_data = []
        total_tokens = 0

        for i, embedding_vector in enumerate(embeddings_vectors):
            embedding_data.append(EmbeddingData(embedding=embedding_vector, index=i))
            total_tokens += len(texts[i].split()) # Simple token estimation

        return EmbeddingResponse(
            data=embedding_data,
            model=request.model,
            usage=EmbeddingUsage(prompt_tokens=total_tokens, total_tokens=total_tokens)
        )
    except Exception as e:
        logger.error(f"Failed to create text embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 임베딩 생성 중 오류가 발생했습니다: {str(e)}")