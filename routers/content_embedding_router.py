from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
import logging

from models.schemas import EmbedContentRequest
from services.content_embedding_service import ContentEmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["✨ Content Embedding"],
    responses={
        200: {"description": "콘텐츠 임베딩 성공"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"}
    }
)

content_embedding_service = ContentEmbeddingService()

@router.post(
    "/embed-content",
    response_model=Dict[str, Any],
    summary="콘텐츠 임베딩 및 벡터 DB 저장",
    description="""
    **파일, URL 또는 직접 제공된 텍스트 콘텐츠를 임베딩하여 벡터 데이터베이스에 저장합니다.**

    ### 📝 기능
    - **파일 임베딩**: 로컬 파일 경로를 받아 내용을 읽고 임베딩합니다.
    - **URL 임베딩**: URL을 받아 웹 페이지 내용을 가져와 임베딩합니다.
    - **텍스트 임베딩**: 직접 텍스트를 받아 임베딩합니다.
    - **그룹화**: `group_name`을 지정하여 임베딩된 콘텐츠를 그룹화할 수 있습니다.
    - **메타데이터**: 추가 메타데이터를 포함할 수 있습니다.

    ### 💡 사용 예시

    **1. 파일 임베딩:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/embed-content" \
      -H "Content-Type: application/json" \
      -d '''{
        "source_type": "file",
        "source_data": "/path/to/your/document.txt",
        "group_name": "my_project_docs",
        "title": "My Project Document",
        "metadata": {"author": "Gemini", "version": "1.0"}
      }'''
    ```

    **2. URL 임베딩:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/embed-content" \
      -H "Content-Type: application/json" \
      -d '''{
        "source_type": "url",
        "source_data": "https://www.example.com/some-article",
        "group_name": "web_articles",
        "title": "Interesting Article",
        "metadata": {"category": "AI", "published_date": "2023-01-01"}
      }'''
    ```

    **3. 텍스트 임베딩:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/embed-content" \
      -H "Content-Type: application/json" \
      -d '''{
        "source_type": "text",
        "source_data": "This is a sample text content that I want to embed into the vector database.",
        "group_name": "misc_notes",
        "title": "Sample Text Note"
      }'''
    ```
    """)
async def embed_content_endpoint(request: EmbedContentRequest = Body(...)):
    try:
        result = await content_embedding_service.embed_content(request)
        return result
    except (FileNotFoundError, ConnectionError, ValueError) as e:
        logger.error(f"Bad request for embed-content: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal server error during embed-content: {e}")
        raise HTTPException(status_code=500, detail=f"콘텐츠 임베딩 중 오류가 발생했습니다: {str(e)}")


curl -X POST "http://localhost:8001/api/v1/search" \
     -H "Content-Type: application/json" \
     -d '{
           "query": "프로젝트 문서의 주요 기능은 무엇인가요?",
           "k": 3,
           "group_name": "my_project_docs"
        }'



curl -X POST "http://localhost:8001/api/v1/embed-content" \
     -H "Content-Type: application/json" \
     -d '{
             "source_type": "file",
             "source_data": "/Users/a08418/Documents/CoE/CoE-RagPipeline/output/documents/8535e4c4-493f-4b3e-9243-dab923e1ca74/DocumentType.ARCHITECTURE_OVERVIEW_korean.md",
             "group_name": "my_project_docs",
             "title": "CoE Project README",
             "metadata": {"author": "Gemini", "version": "1.0"}
         }'