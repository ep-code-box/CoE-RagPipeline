# 1. 베이스 이미지 설정
# 가볍고 안정적인 python 3.11-slim 버전을 사용합니다.
FROM python:3.11-slim

# 2. 시스템 의존성 설치
# Git 레포지토리 클론을 위해 git을 설치합니다.
RUN apt-get update && apt-get install -y git build-essential curl && rm -rf /var/lib/apt/lists/*

# uv를 설치합니다.
RUN pip install uv

# requirements.txt 파일을 복사합니다.
COPY requirements.txt .

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. Python 의존성 설치
# requirements.txt를 먼저 복사하여 의존성 변경이 없을 경우 캐시를 활용합니다.
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# 5. 로그 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/logs && \
    chmod 777 /app/logs && \
    touch /app/logs/app.log /app/logs/access.log /app/logs/error.log && \
    chmod 666 /app/logs/*.log

# 6. 소스 코드 복사
# 나머지 프로젝트 파일을 이미지에 복사합니다.
COPY . .

# 7. 로그 설정 스크립트 실행 권한 부여
RUN chmod +x /app/scripts/setup_logs.sh

# 8. 포트 노출
# CoE-RagPipeline은 8001 포트를 사용합니다.
EXPOSE 8001

# 9. 애플리케이션 실행
# uvicorn을 사용하여 FastAPI 애플리케이션을 실행합니다.
# main.py 파일 안에 FastAPI 인스턴스가 'app'으로 정의되어 있다고 가정합니다.
CMD ["sh", "-c", "/app/scripts/setup_logs.sh && uvicorn main:app --host 0.0.0.0 --port 8001"]