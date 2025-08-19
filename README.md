# 🔍 CoE RAG 파이프라인

Git 리포지토리를 분석하고, AST 분석 및 기술 스택 정적 분석을 수행합니다. 분석된 코드와 문서를 기반으로 RAG 시스템을 구축합니다.

## ✨ 주요 기능

### 1. Git 저장소 분석 (Repository Analysis)
Git 리포지토리의 코드를 분석하여 AST(추상 구문 트리), 기술 스택, 코드 메트릭 등 다양한 정보를 추출합니다.

### 2. 소스 코드 요약 (Source Code Summarization)
분석된 저장소 내의 소스 코드 파일을 LLM을 통해 요약합니다. 요약된 내용은 문서 생성 시 활용될 수 있습니다.
**지원 언어:** Python, JavaScript, TypeScript, React JSX/TSX, Java, Kotlin, Swift, Go, Rust, C++, C, C#, PHP, Ruby, Scala, Shell Script, SQL, YAML, JSON, XML, HTML, CSS, SCSS, LESS. (지원되지 않는 언어의 파일은 요약에서 제외됩니다.)

### 3. 문서 생성 (Document Generation)
분석된 데이터와 소스 코드 요약을 바탕으로 다양한 형식의 기술 문서를 생성합니다.
**문서 타입:** 개발 가이드, API 문서, 아키텍처 개요, 기술 명세서 등.

### 4. RDB 스키마 임베딩 (RDB Schema Embedding)
MariaDB 데이터베이스의 스키마(테이블, 컬럼) 정보를 추출하여 RAG에 포함시킵니다.

### 5. 벡터 유사도 검색 (Vector Similarity Search)
저장된 벡터 데이터베이스에서 유사한 문서를 검색합니다. `group_name`을 사용하여 특정 그룹의 문서와 RDB 스키마 정보를 함께 검색할 수 있습니다.

## 🚀 시작하기

### 📋 사전 요구사항
- Python, Docker
- LLM API 키 (예: SKAX, OpenAI)

### 🔧 환경 설정
1.  `.env.sample` 파일을 복사하여 `.env` 파일을 생성합니다.
    ```bash
    cp .env.sample .env
    ```
2.  `.env` 파일을 열어 `SKAX_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL` 등 필요한 환경 변수를 설정합니다.

### 🏃‍♂️ 서버 실행
`run.sh` 스크립트를 사용하면 가상 환경 설정, 의존성 설치, 서버 실행을 한 번에 처리할 수 있습니다.
```bash
# 실행 권한 부여
chmod +x run.sh

# 서버 실행
./run.sh
```

## 📂 프로젝트 구조

## 📝 API 사용 예시

### 1. Git 저장소 분석 (Repository Analysis)
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }'
```

### 2. 소스 코드 요약 (Source Code Summarization)
```bash
curl -X POST "http://localhost:8001/api/v1/source-summary/summarize-repository/YOUR_ANALYSIS_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "max_files": 100,
    "batch_size": 5,
    "embed_to_vector_db": true
  }'
```

### 3. 문서 생성 (Document Generation)
*   **소스 요약을 포함하여 생성 (기본값):**
    ```bash
    curl -X POST "http://localhost:8001/api/v1/documents/generate" \
      -H "Content-Type: application/json" \
      -d '{
        "analysis_id": "YOUR_ANALYSIS_ID",
        "document_types": ["development_guide"],
        "language": "korean"
      }'
    ```
    또는 명시적으로:
    ```bash
    curl -X POST "http://localhost:8001/api/v1/documents/generate?use_source_summaries=true" \
      -H "Content-Type: application/json" \
      -d '{
        "analysis_id": "YOUR_ANALYSIS_ID",
        "document_types": ["development_guide"],
        "language": "korean"
      }'
    ```

*   **소스 요약 없이 생성:**
    ```bash
    curl -X POST "http://localhost:8001/api/v1/documents/generate?use_source_summaries=false" \
      -H "Content-Type: application/json" \
      -d '{
        "analysis_id": "YOUR_ANALYSIS_ID",
        "document_types": ["development_guide"],
        "language": "korean"
      }'
    ```

### 4. RDB 스키마 임베딩 (RDB Schema Embedding)
데이터베이스의 스키마 정보를 RAG에 추가하려면 다음 엔드포인트를 호출합니다.
```bash
curl -X POST http://localhost:8001/api/v1/embed_rdb_schema
```

### 5. 벡터 유사도 검색 (Vector Similarity Search)
저장된 벡터 데이터베이스에서 유사한 문서를 검색합니다. `group_name`을 사용하여 특정 그룹의 문서와 RDB 스키마 정보를 함께 검색할 수 있습니다.
```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{ "query": "사용자 정보 테이블", "k": 5, "group_name": "UserService" }'
```

### 6. 콘텐츠 임베딩 (Content Embedding)
파일, URL 또는 직접 제공된 텍스트 콘텐츠를 임베딩하여 벡터 데이터베이스에 저장합니다. `group_name`을 지정하여 임베딩된 콘텐츠를 그룹화할 수 있습니다.

**1. 파일 임베딩:**
```bash
curl -X POST "http://localhost:8001/api/v1/embed-content" \
  -H "Content-Type: application/json" \
  -d '{ "source_type": "file", "source_data": "/path/to/your/document.txt", "group_name": "my_project_docs", "title": "My Project Document", "metadata": {"author": "Gemini", "version": "1.0"} }'
```

**2. URL 임베딩:**
```bash
curl -X POST "http://localhost:8001/api/v1/embed-content" \
  -H "Content-Type: application/json" \
  -d '{ "source_type": "url", "source_data": "https://www.example.com/some-article", "group_name": "web_articles", "title": "Interesting Article", "metadata": {"category": "AI", "published_date": "2023-01-01"} }'
```

**3. 텍스트 임베딩:**
```bash
curl -X POST "http://localhost:8001/api/v1/embed-content" \
  -H "Content-Type: application/json" \
  -d '{ "source_type": "text", "source_data": "This is a sample text content that I want to embed into the vector database.", "group_name": "misc_notes", "title": "Sample Text Note" }'
```

## 📂 프로젝트 구조 상세 설명

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
*   `__pycache__/`: Python이 바이트코드 컴파일된 파일을 저장하는 디렉토리입니다.
*   `.git/`: Git 버전 관리 시스템의 메타데이터를 저장하는 디렉토리입니다.
*   `.venv/`: Python 가상 환경 디렉토리입니다. 프로젝트 의존성을 격리하여 관리합니다.

### 주요 모듈 디렉토리

*   `analyzers/`: Git 리포지토리의 코드를 분석하는 다양한 분석기 모듈을 포함합니다.
    *   `ast_analyzer.py`: 추상 구문 트리(AST) 분석을 담당합니다.
    *   `git_analyzer.py`: Git 리포지토리 클론, 변경 감지 등 Git 관련 분석을 수행합니다.
    *   `tech_spec_analyzer.py`: 기술 스택 및 의존성 분석을 담당합니다.
    *   `enhanced/`: 더 고급 분석 기능을 제공하는 모듈들을 포함합니다.
        *   `dependency_analyzer.py`: 코드베이스 내의 의존성 관계를 분석합니다.
        *   `static_analyzer.py`: 정적 코드 분석을 수행합니다.
        *   `tree_sitter_analyzer.py`: Tree-sitter를 활용한 구문 분석을 담당합니다.

*   `cache/`: 분석 결과, 요약 등 임시 데이터를 저장하는 캐시 디렉토리입니다.
*   `chroma_db/`: ChromaDB 벡터 데이터베이스 파일이 저장되는 디렉토리입니다. RAG 시스템의 핵심 저장소로 사용됩니다.

*   `config/`: 애플리케이션의 설정 및 프롬프트 관련 파일을 포함합니다.
    *   `prompts.py`: LLM(Large Language Model)이 문서를 생성하거나 요약할 때 사용하는 다양한 시스템 및 사용자 프롬프트 템플릿을 정의합니다.
    *   `settings.py`: 애플리케이션 전반에 걸친 설정(API 키, 데이터베이스 URL 등)을 관리합니다.

*   `core/`: 애플리케이션의 핵심 로직 및 기반 기능을 제공합니다.
    *   `database.py`: 데이터베이스 연결 및 세션 관리를 담당합니다.

*   `models/`: Pydantic을 사용하여 데이터 유효성 검사 및 직렬화를 위한 데이터 모델(스키마)을 정의합니다.
    *   `schemas.py`: API 요청/응답, 데이터베이스 모델 등 다양한 데이터 구조를 정의합니다.

*   `output/`: 분석 결과, 생성된 문서, 소스 코드 요약 등 프로젝트의 결과물이 저장되는 디렉토리입니다.
    *   `documents/`: LLM이 생성한 최종 문서들이 저장됩니다.
    *   `results/`: Git 분석 등의 중간 결과물들이 저장됩니다.
    *   `summaries/`: 소스 코드 요약 결과가 저장됩니다.

*   `routers/`: FastAPI 애플리케이션의 API 엔드포인트를 정의하는 모듈들을 포함합니다. 각 파일은 특정 기능 영역에 대한 라우터를 담당합니다.
    *   `analysis.py`: Git 리포지토리 분석 관련 API 엔드포인트를 정의합니다.
    *   `document_generation.py`: 문서 생성 관련 API 엔드포인트를 정의합니다.
    *   `embedding.py`: 벡터 임베딩 관련 API 엔드포인트를 정의합니다.
    *   `health.py`: 애플리케이션 상태 확인(Health Check) 엔드포인트를 정의합니다.
    *   `source_summary.py`: 소스 코드 요약 관련 API 엔드포인트를 정의합니다.
    *   `enhanced/`: 향상된 분석 및 관련 API 엔드포인트를 정의합니다.

*   `services/`: 비즈니스 로직을 구현하는 서비스 모듈들을 포함합니다. 라우터에서 호출되어 실제 작업을 수행합니다.
    *   `analysis_service.py`: Git 리포지토리 분석의 전체 흐름을 관리합니다.
    *   `llm_service.py`: LLM과의 통신 및 문서 생성 로직을 담당합니다.
    *   `source_summary_service.py`: 소스 코드 파일 요약 로직을 담당합니다.
    *   `embedding_service.py`: 텍스트 임베딩 및 벡터 데이터베이스 저장을 담당합니다.
    *   `rag_analysis_service.py`, `rag_code_file_service.py`, `rag_document_analysis_service.py`, `rag_repository_analysis_service.py`, `rag_tech_dependency_service.py`: RAG(Retrieval Augmented Generation) 시스템의 다양한 분석 및 데이터 처리 로직을 담당합니다.
    *   `rdb_embedding_service.py`: RDB 스키마 임베딩 로직을 담당합니다.
    *   `sql_agent_service.py`: SQL 에이전트 관련 로직을 담당합니다.

*   `utils/`: 프로젝트 전반에 걸쳐 재사용 가능한 유틸리티 함수들을 포함합니다.
    *   `app_initializer.py`: 애플리케이션 초기화 관련 유틸리티.
    *   `file_utils.py`: 파일 시스템 관련 유틸리티.
    *   `markdown_generator.py`: 마크다운 문서 생성 유틸리티.
    *   `server_utils.py`: 서버 관련 유틸리티.
    *   `tech_utils.py`: 기술 관련 유틸리티.
    *   `token_utils.py`: 토큰 계산 및 청킹 관련 유틸리티.

## 4. 예외 및 특이 사항 (Exceptions and Special Considerations)

#### 4.1. 대용량 데이터 처리 및 토큰 제한
*   **설명:** 분석 데이터나 소스 코드 파일의 크기가 LLM의 토큰 제한을 초과할 경우, 시스템은 자동으로 데이터를 잘라내거나(trimming) 여러 청크로 분할(chunking)하여 처리합니다.
*   **영향:** 데이터가 잘려나갈 경우, 문서의 상세도가 일부 저하될 수 있습니다.
*   **관련 로그:** `분석 데이터가 너무 큼`, `분석 데이터 잘라내기 완료`, `토큰 제한 초과` 등의 로그 메시지를 확인할 수 있습니다.

#### 4.2. 소스 코드 요약 지원 언어 제한
*   **설명:** 소스 코드 요약 기능은 특정 프로그래밍 언어 및 파일 확장자에 대해서만 지원됩니다. 지원되지 않는 언어의 파일은 요약 과정에서 자동으로 제외됩니다.
*   **지원 언어:** Python, JavaScript, TypeScript, React JSX/TSX, Java, Kotlin, Swift, Go, Rust, C++, C, C#, PHP, Ruby, Scala, Shell Script, SQL, YAML, JSON, XML, HTML, CSS, SCSS, LESS.
*   **영향:** 지원되지 않는 언어로 작성된 파일은 문서 생성 시 소스 코드 요약 정보에 포함되지 않습니다.

#### 4.3. 프롬프트 데이터 누락 (KeyError)
*   **설명:** 과거에는 특정 프롬프트 템플릿이 기대하는 데이터(예: `source_summary_info`)가 제공되지 않을 경우 `KeyError`가 발생할 수 있었습니다. 이는 주로 소스 요약 정보가 없는 상태에서 소스 요약을 기대하는 프롬프트가 사용될 때 발생했습니다.
*   **현재 처리:** 이 문제는 수정되었으며, 이제 해당 데이터가 없는 경우 빈 문자열로 대체되어 오류 없이 문서가 생성됩니다.
*   **참고:** 실제 소스 요약 정보를 문서에 포함하려면 `use_source_summaries=true` (기본값)로 설정하여 문서 생성 API를 호출해야 합니다.

#### 4.4. LLM API 호출 실패 및 재시도
*   **설명:** LLM(Large Language Model) API 호출 시 네트워크 문제, API 제한 초과 등으로 인해 실패할 수 있습니다.
*   **처리:** 시스템은 이러한 실패에 대해 자동으로 여러 번 재시도(retry)를 수행합니다. 재시도 간에는 지수 백오프(exponential backoff) 전략을 사용하여 API 부하를 줄입니다.
*   **영향:** 일시적인 네트워크 문제나 API 제한은 자동으로 복구될 수 있습니다. 지속적인 실패는 로그를 통해 확인할 수 있습니다.
