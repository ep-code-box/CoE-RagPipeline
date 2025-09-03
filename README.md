# CoE RAG Pipeline

## 1. 프로젝트 개요

이 프로젝트는 Git 리포지토리, 데이터베이스 스키마, 파일, URL 등 다양한 소스로부터 정보를 분석하고 벡터화하여 RAG(Retrieval-Augmented Generation) 시스템을 구축하는 파이프라인입니다.

추출된 정보는 벡터 데이터베이스(ChromaDB)에 저장되며, 자연어 쿼리를 통해 관련 정보를 검색하거나, 분석된 내용을 바탕으로 기술 문서를 자동으로 생성하는 기능을 제공합니다.

## 목차

- [1. 프로젝트 개요](#1-프로젝트-개요)
- [2. 주요 기능](#2-주요-기능)
- [3. 시작하기](#3-시작하기)
- [4. API 사용 예시](#4-api-사용-예시)
  - [4.1. Git 저장소 분석](#41-git-저장소-분석)
  - [4.2. 소스 코드 요약](#42-소스-코드-요약)
  - [4.3. 문서 생성](#43-문서-생성)
  - [4.4. RDB 스키마 임베딩](#44-rdb-스키마-임베딩)
  - [4.5. 벡터 유사도 검색](#45-벡터-유사도-검색)
  - [4.6. 콘텐츠 임베딩](#46-콘텐츠-임베딩)
- [5. 프로젝트 구조 상세](#5-프로젝트-구조-상세)
- [6. 예외 및 특이 사항](#6-예외-및-특이-사항)

## 2. 주요 기능

- **Git 저장소 분석**: 코드를 분석하여 AST(추상 구문 트리), 기술 스택, 코드 메트릭 등을 추출합니다.
- **소스 코드 요약**: LLM을 통해 소스 코드를 요약하고 RAG 검색에 활용합니다.
- **자동 문서 생성**: 분석된 데이터를 바탕으로 개발 가이드, API 명세 등 다양한 기술 문서를 생성합니다.
- **다중 소스 임베딩**: RDB 스키마, 파일, URL, 텍스트 등 다양한 형태의 정보를 벡터화하여 RAG 시스템에 통합합니다.
- **유사도 검색**: 벡터화된 데이터베이스에서 `group_name`을 기준으로 관련 정보를 검색합니다.

## 3. 시작하기

### 사전 요구사항

- Docker
- Docker Compose

### 실행 방법

이 서비스는 단독으로 실행되지 않으며, 프로젝트 최상위 디렉토리의 `docker-compose.yml`을 통해 전체 시스템의 일부로 실행되어야 합니다.

1.  **프로젝트 클론**:
    ```bash
    git clone <repository_url>
    cd CoE
    ```

2.  **환경 변수 설정**:
    `CoE-RagPipeline/.env.sample` 파일을 `CoE-RagPipeline/.env`로 복사하고, 필요한 API 키 및 데이터베이스 정보를 입력합니다.

3.  **Docker Compose 실행**:
    프로젝트 최상위 디렉토리에서 아래 명령어를 실행합니다.
    ```bash
    docker-compose up --build -d
    ```

4.  **로그 확인**:
    ```bash
    docker-compose logs -f coe-ragpipeline
    ```

## 4. API 사용 예시

### 4.1. Git 저장소 분석
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d {
    "repositories": [
      {
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }
```

### 4.2. 소스 코드 요약
```bash
curl -X POST "http://localhost:8001/api/v1/source-summary/summarize-repository/YOUR_ANALYSIS_ID" \
  -H "Content-Type: application/json" \
  -d {
    "max_files": 100,
    "batch_size": 5,
    "embed_to_vector_db": true
  }
```

### 4.3. 문서 생성
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate?use_source_summaries=true" \
  -H "Content-Type: application/json" \
  -d {
    "analysis_id": "YOUR_ANALYSIS_ID",
    "document_types": ["development_guide"],
    "language": "korean"
  }
```

### 4.4. RDB 스키마 임베딩
```bash
curl -X POST http://localhost:8001/api/v1/embed_rdb_schema
```

### 4.5. 벡터 유사도 검색
```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d { "query": "사용자 정보 테이블", "k": 5, "group_name": "UserService" }
```

### 4.6. 콘텐츠 임베딩

파일, URL 또는 직접 제공된 텍스트 콘텐츠를 임베딩하여 벡터 데이터베이스에 저장합니다. `group_name`을 지정하여 임베딩된 콘텐츠를 그룹화할 수 있습니다.

**URL 임베딩 예시:**
```bash
curl -X POST "http://localhost:8001/api/v1/embed-content" \
  -H "Content-Type: application/json" \
  -d { "source_type": "url", "source_data": "https://www.example.com/some-article", "group_name": "web_articles", "title": "Interesting Article" }
```

## 5. 프로젝트 구조 상세

이 섹션에서는 `CoE-RagPipeline` 프로젝트의 주요 디렉토리와 파일들의 역할 및 중요성에 대해 상세히 설명합니다.

### 최상위 디렉토리 및 파일

*   `main.py`: FastAPI 애플리케이션의 메인 진입점입니다. 모든 API 라우터와 서비스가 여기서 초기화되고 통합됩니다.
*   `run.sh`: 프로젝트를 실행하기 위한 쉘 스크립트입니다. 가상 환경 설정, 의존성 설치, 서버 실행 등 초기 설정 및 실행 과정을 자동화합니다.
*   `Dockerfile`: Docker 이미지를 빌드하기 위한 설정 파일입니다. 프로젝트를 컨테이너 환경에서 실행할 수 있도록 합니다.
*   `.env.sample`: 환경 변수 설정의 예시 파일입니다. `.env` 파일을 생성할 때 참고하며, API 키, 데이터베이스 URL 등 민감한 정보가 포함됩니다.
*   `requirements.txt`: 프로젝트가 의존하는 Python 패키지 목록을 정의합니다. `pip install -r requirements.txt` 명령으로 모든 의존성을 설치할 수 있습니다.
*   `README.md`: 프로젝트에 대한 개요, 주요 기능, 시작하기 가이드, API 사용 예시 등을 포함하는 주요 문서 파일입니다.
*   `.gitignore`: Git 버전 관리에서 제외할 파일 및 디렉토리 패턴을 정의합니다. (예: `.venv`, `__pycache__`, `output/`)
*   `.dockerignore`: Docker 이미지 빌드 시 컨테이너에 포함하지 않을 파일 및 디렉토리 패턴을 정의합니다.

### 주요 모듈 디렉토리

*   `analyzers/`: Git 리포지토리의 코드를 분석하는 다양한 분석기 모듈을 포함합니다.
*   `cache/`: 분석 결과, 요약 등 임시 데이터를 저장하는 캐시 디렉토리입니다.
*   `chroma_db/`: ChromaDB 벡터 데이터베이스 파일이 저장되는 디렉토리입니다.
*   `config/`: 애플리케이션의 설정 및 프롬프트 관련 파일을 포함합니다.
*   `core/`: 애플리케이션의 핵심 로직 및 기반 기능을 제공합니다.
*   `models/`: Pydantic을 사용하여 데이터 유효성 검사 및 직렬화를 위한 데이터 모델(스키마)을 정의합니다.
*   `output/`: 분석 결과, 생성된 문서, 소스 코드 요약 등 프로젝트의 결과물이 저장되는 디렉토리입니다.
*   `routers/`: FastAPI 애플리케이션의 API 엔드포인트를 정의하는 모듈들을 포함합니다.
*   `services/`: 비즈니스 로직을 구현하는 서비스 모듈들을 포함합니다.
*   `utils/`: 프로젝트 전반에 걸쳐 재사용 가능한 유틸리티 함수들을 포함합니다.

## 6. 예외 및 특이 사항

#### 6.1. 대용량 데이터 처리 및 토큰 제한
*   **설명:** 분석 데이터나 소스 코드 파일의 크기가 LLM의 토큰 제한을 초과할 경우, 시스템은 자동으로 데이터를 잘라내거나(trimming) 여러 청크로 분할(chunking)하여 처리합니다.
*   **영향:** 데이터가 잘려나갈 경우, 문서의 상세도가 일부 저하될 수 있습니다.

#### 6.2. 소스 코드 요약 지원 언어 제한
*   **설명:** 소스 코드 요약 기능은 특정 프로그래밍 언어 및 파일 확장자에 대해서만 지원됩니다. 지원되지 않는 언어의 파일은 요약 과정에서 자동으로 제외됩니다.

#### 6.3. 프롬프트 데이터 누락 (KeyError)
*   **설명:** 과거에는 특정 프롬프트 템플릿이 기대하는 데이터가 제공되지 않을 경우 `KeyError`가 발생할 수 있었습니다. 이제 해당 데이터가 없는 경우 빈 문자열로 대체되어 오류 없이 문서가 생성됩니다.

#### 6.4. LLM API 호출 실패 및 재시도
*   **설명:** LLM API 호출 시 네트워크 문제, API 제한 초과 등으로 인해 실패할 수 있습니다. 시스템은 이러한 실패에 대해 자동으로 여러 번 재시도(retry)를 수행합니다.