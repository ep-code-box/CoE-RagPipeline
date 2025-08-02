import logging
from services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)


def initialize_services():
    """서비스 초기화"""
    # 서버 시작 시 기존 결과 로드
    analysis_service = AnalysisService()
    analysis_results = analysis_service.load_all_analysis_results()
    
    # 분석 결과를 라우터에서 사용할 수 있도록 설정
    from routers import analysis
    analysis.analysis_results = analysis_results
    
    # 데이터베이스 초기화 (선택적) - main.py에서 이미 초기화되므로 제거
    # 데이터베이스 초기화는 main.py에서 처리됨
    logger.info("Services initialized successfully")