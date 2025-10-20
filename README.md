# CoE RAG Pipeline

문서 맵
- 배포/기동: `../docs/DEPLOY.md`
- 마이그레이션 운영: `../docs/OPERATIONS.md`
- Swagger/UI 경로/사용: `../docs/SWAGGER_GUIDE.md`
- cURL 예시 모음: `../docs/curl-checks.md`

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

운영/배포/기동 절차는 최상위 문서에서 관리합니다. 아래 문서를 참고하세요.
- 전체 배포 및 완전 격리 스택: `../docs/DEPLOY.md`

### 3.1. 오프라인 환경 의존성 설치
내부망에서 `pip install`이 제한될 경우, 외부망 머신에서 아래 명령으로 휠을 준비하세요.
```bash
cd CoE-RagPipeline
python -m pip download -r requirements.txt -d vendor/wheels
python -m pip download uv -d vendor/wheels
```
준비한 `vendor/wheels/*.whl` 파일을 내부망 서버로 복사하면 `run.sh`가 자동으로 감지하여 `--no-index --find-links=vendor/wheels` 옵션으로 설치합니다.
환경에 따라 다른 디렉터리를 쓰고 싶다면 `WHEEL_DIR=/path/to/wheels ./run.sh`처럼 환경 변수를 지정할 수 있습니다.

> Docker가 사용 가능한 환경이라면 루트 디렉터리에서 `./scripts/download_wheels.sh rag` 를 실행해 Linux/Python3.11용 휠을 자동으로 모을 수 있습니다.

## 5. 운영 시 DB 마이그레이션

정책과 실행 방법은 `../docs/OPERATIONS.md`를 참고하세요.

## 4. API 사용 예시

Swagger 경로와 주요 예시는 다음 문서에서 확인하세요.
- Swagger/UI: `../docs/SWAGGER_GUIDE.md`
- cURL 예시 모음: `../docs/curl-checks.md`

중요: RAG Pipeline 직접 호출은 단계적으로 중단 예정이며, Backend 경유 호출을 권장합니다.
기존 스크립트/자동화는 Backend 엔드포인트로 이전해 주세요(유예 기간 후 적용).

### 분석 고급 옵션(Enhanced 플래그)

기존 `/api/v1/enhanced/*` 엔드포인트는 제거되었습니다. 대신 `/api/v1/analyze` 요청 본문에 아래 플래그를 포함하세요.

- `include_tree_sitter` (bool, 기본 true)
- `include_static_analysis` (bool, 기본 true)
- `include_dependency_analysis` (bool, 기본 true)
- `generate_report` (bool, 기본 true)

예시
```
POST /api/v1/analyze
{
  "repositories": [{"url": "https://github.com/octocat/Hello-World.git", "branch": "main"}],
  "include_ast": true,
  "include_tech_spec": true,
  "include_correlation": true,
  "include_tree_sitter": true,
  "include_static_analysis": true,
  "include_dependency_analysis": true,
  "generate_report": true,
  "group_name": "MyTeamA"
}
```

### 요약/임베딩 커버리지 설정(대형 리포 제어)

아래 환경변수로 요약/임베딩 커버리지를 조절할 수 있습니다.

- 요약 파이프라인
  - `SUMMARY_MAX_FILES_DEFAULT` (기본 100)
  - `SUMMARY_BATCH_SIZE_DEFAULT` (기본 5)
  - `SUMMARY_MAX_FILE_TOKENS` (기본 6000)
  - `SUMMARY_MAX_CONCURRENT_REQUESTS` (기본 3)
  - `SUMMARY_RETRY_ATTEMPTS` (기본 3), `SUMMARY_RETRY_DELAY` (기본 1.0)
- 임베딩 청크
  - `EMBEDDING_CHUNK_SIZE` (기본 1000)
  - `EMBEDDING_CHUNK_OVERLAP` (기본 200)
  - `CONTENT_EMBEDDING_CHUNK_SIZE` (기본 `EMBEDDING_CHUNK_SIZE`)
  - `CONTENT_EMBEDDING_CHUNK_OVERLAP` (기본 `EMBEDDING_CHUNK_OVERLAP`)

품질 우선이면 청크 크기를 작게/오버랩을 높게, 비용/속도 우선이면 반대로 조정하세요.

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

### 성능/비용 최적화 (Reranking)

벡터 검색 결과를 LLM으로 재정렬(reranking)하는 기능이 있으며, 기본 비활성화입니다.
환경변수로 제어해 성능/비용 균형을 맞출 수 있습니다.

- `ENABLE_RERANKING` (default: `false`): `true`일 때 LLM 리랭킹 활성화
- `RERANK_MULTIPLIER` (default: `5`): 초기 후보 수 배수 (`k * multiplier`)
- `RERANK_MAX_CANDIDATES` (default: `30`): 리랭크 최대 후보 수 상한
- `RERANK_CONTENT_CHARS` (default: `1000`): 각 문서 내용의 리랭크 입력 길이 제한(문자)
- `RERANK_MODEL` (default: `gpt-4o-mini`): 리랭킹에 사용할 모델명

리랭킹은 품질 향상에 도움이 되지만 비용/지연이 증가합니다. 트래픽이 많거나 응답 지연에 민감하면 `ENABLE_RERANKING=false` 유지 또는 후보 수를 줄이는 것을 권장합니다.
