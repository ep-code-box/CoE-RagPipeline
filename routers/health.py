from fastapi import APIRouter
from datetime import datetime

from models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    return HealthResponse(status="healthy", timestamp=datetime.now())