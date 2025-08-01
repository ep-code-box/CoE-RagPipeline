import socket
import logging

logger = logging.getLogger(__name__)


def find_available_port(start_port: int = 8001, max_attempts: int = 10) -> int:
    """
    주어진 시작 포트부터 사용 가능한 포트를 찾아 반환합니다.
    
    Args:
        start_port: 검색을 시작할 포트 번호
        max_attempts: 최대 시도 횟수
        
    Returns:
        사용 가능한 포트 번호
        
    Raises:
        RuntimeError: 사용 가능한 포트를 찾지 못한 경우
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('127.0.0.1', port))
                logger.info(f"Found available port: {port}")
                return port
        except OSError:
            logger.debug(f"Port {port} is already in use, trying next port...")
            continue
    
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")