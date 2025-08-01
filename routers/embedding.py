from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["embedding"])


@router.post("/search", response_model=List[dict])
async def search_embeddings(query: str, k: int = 5, filter_metadata: Optional[Dict] = None):
    """Chroma 벡터 데이터베이스에서 유사한 문서 검색"""
    try:
        from services.embedding_service import EmbeddingService
        from config.settings import settings
        
        embedding_service = EmbeddingService(chroma_persist_directory=settings.CHROMA_PERSIST_DIRECTORY)
        results = embedding_service.search_similar_documents(query, k=k, filter_metadata=filter_metadata)
        return results
    except Exception as e:
        logger.error(f"Failed to search embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats", response_model=dict)
async def get_embedding_stats():
    """Chroma 벡터 데이터베이스 통계 정보 조회"""
    try:
        from services.embedding_service import EmbeddingService
        from config.settings import settings
        
        embedding_service = EmbeddingService(chroma_persist_directory=settings.CHROMA_PERSIST_DIRECTORY)
        stats = embedding_service.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")