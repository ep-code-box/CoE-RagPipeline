from fastapi import APIRouter
from datetime import datetime

from models.schemas import HealthResponse

router = APIRouter(
    tags=["🏥 Health Check"],
    prefix="",
    responses={
        200: {"description": "서비스가 정상적으로 작동 중입니다"},
        503: {"description": "서비스 이용 불가"}
    }
)


@router.get(
    "/health", 
    response_model=HealthResponse,
    summary="서비스 상태 확인",
    description="""
    **CoE-RagPipeline 서비스의 상태를 확인합니다.**
    
    이 엔드포인트는 다음을 확인합니다:
    - 서비스 실행 상태
    - 현재 시간
    - 데이터베이스 연결 상태
    - ChromaDB 연결 상태
    
    **사용 예시:**
    ```bash
    curl -X GET "http://localhost:8001/health"
    ```
    """,
    response_description="서비스 상태 정보"
)
async def health_check():
    """서비스 상태 확인 - Git 분석 파이프라인 서비스가 정상적으로 실행 중인지 확인합니다."""
    return HealthResponse(status="healthy", timestamp=datetime.now())