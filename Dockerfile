# 1. 베이스 이미지 설정
# 가볍고 안정적인 python 3.11-slim 버전을 사용합니다.
FROM python:3.11-slim

# 2. 시스템 의존성 설치
# Git 레포지토리 클론을 위해 git을 설치합니다.
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. Python 의존성 설치
# requirements.txt를 먼저 복사하여 의존성 변경이 없을 경우 캐시를 활용합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
# 나머지 프로젝트 파일을 이미지에 복사합니다.
COPY . .

# 6. 포트 노출
# CoE-RagPipeline은 8001 포트를 사용합니다.
EXPOSE 8001

# 7. 애플리케이션 실행
# uvicorn을 사용하여 FastAPI 애플리케이션을 실행합니다.
# main.py 파일 안에 FastAPI 인스턴스가 'app'으로 정의되어 있다고 가정합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--log-config", "core/logging_config.py"]