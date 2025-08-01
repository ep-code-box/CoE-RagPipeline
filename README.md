# 🔍 CoE RAG Pipeline

Git 레포지토리들을 분석하여 레포지토리간 연관도, AST 분석, 기술스펙 정적 분석을 수행하는 RAG 파이프라인입니다.

## ✨ 주요 기능

- **Git 레포지토리 분석**: 여러 Git 주소를 받아 소스코드를 자동으로 클론하고 분석
- **AST 분석**: Python, JavaScript, Java, TypeScript 등 주요 언어의 추상 구문 트리 분석
- **기술스펙 정적 분석**: 의존성, 프레임워크, 라이브러리, 코드 품질 메트릭 분석
- **레포지토리간 연관도 분석**: 공통 의존성, 코드 패턴, 아키텍처 유사성 분석
- **문서 자동 수집**: doc 폴더, README, 참조 URL에서 개발 문서 자동 수집 및 분석
- **개발 표준 문서 생성**: 분석 결과를 바탕으로 코딩 스타일, 아키텍처 패턴, 공통 함수 가이드 자동 생성
- **RAG 시스템 구축**: 분석된 코드와 문서를 벡터화하여 검색 가능한 지식베이스 구축
- **JSON 결과 저장**: 모든 분석 결과를 구조화된 JSON 형태로 저장
- **임베딩 및 벡터 저장**: ChromaDB를 통한 고성능 벡터 검색 지원

## 🚀 시작하기

### 1. 환경 설정

```bash
# 가상 환경 활성화
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
python main.py
```

## 📂 프로젝트 구조

```
CoE-RagPipeline/
├── main.py                 # FastAPI 메인 애플리케이션 (경량화됨)
├── config/                 # 설정 관리
│   └── settings.py         # 애플리케이션 설정
├── routers/                # API 라우터들
│   ├── analysis.py         # 분석 관련 API
│   ├── embedding.py        # 임베딩 관련 API
│   └── health.py           # 헬스체크 API
├── services/               # 비즈니스 로직 서비스들
│   ├── analysis_service.py # 분석 서비스
│   └── embedding_service.py # 임베딩 서비스
├── analyzers/              # 분석 모듈들
│   ├── git_analyzer.py     # Git 레포지토리 분석
│   └── ast_analyzer.py     # AST 분석
├── utils/                  # 유틸리티 함수들
│   ├── file_utils.py       # 파일 관련 유틸리티
│   ├── tech_utils.py       # 기술스펙 관련 유틸리티
│   └── server_utils.py     # 서버 관련 유틸리티
├── models/                 # 데이터 모델 정의
│   └── schemas.py          # Pydantic 스키마
├── output/                 # 분석 결과 저장 디렉토리
│   └── results/            # JSON 분석 결과 파일들
└── chroma_db/              # ChromaDB 벡터 저장소
```

## 🔧 API 엔드포인트

### 코드 분석
- **`POST /api/v1/analyze`**: Git 주소 목록을 받아 전체 분석 수행
  - AST 분석, 기술스펙 분석, 연관도 분석 옵션 지원
  - 문서 수집 및 분석 포함
- **`GET /api/v1/results/{analysis_id}`**: 분석 결과 조회
- **`GET /api/v1/results`**: 모든 분석 결과 목록 조회

### 문서 처리
- **`POST /documents/extract`**: 레포지토리에서 문서 자동 추출
  - doc 폴더, README, 위키 페이지 수집
  - 참조 URL에서 외부 문서 수집
- **`POST /documents/analyze`**: 수집된 문서 분석 및 구조화
- **`GET /documents/{analysis_id}`**: 문서 분석 결과 조회

### RAG 시스템
- **`POST /api/v1/search`**: 벡터 유사도 검색
- **`GET /api/v1/stats`**: 임베딩 통계 정보 조회

### 표준 문서 생성
- **`POST /standards/generate`**: 개발 표준 문서 자동 생성
  - 코딩 스타일 가이드
  - 아키텍처 패턴 문서
  - 공통 함수 및 유틸리티 가이드
- **`GET /standards/{analysis_id}`**: 생성된 표준 문서 조회

### 시스템
- **`GET /health`**: 서비스 상태 확인
- **`GET /metrics`**: 분석 성능 메트릭 조회

## 🧪 API 테스트

### cURL 명령어로 테스트

자동화된 테스트 스크립트를 실행하세요:

```bash
# 실행 권한 부여
chmod +x test_curl.sh

# 테스트 실행
./test_curl.sh
```

또는 개별 cURL 명령어를 사용하세요:

```bash
# Health Check
curl -X GET "http://127.0.0.1:8001/health"

# 분석 시작
curl -X POST "http://127.0.0.1:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/octocat/Hello-World.git",
        "branch": "master"
      }
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": false
  }'

# 분석 결과 조회 (analysis_id는 위 응답에서 받은 값 사용)
curl -X GET "http://127.0.0.1:8001/api/v1/results/{analysis_id}"

# 모든 분석 결과 목록
curl -X GET "http://127.0.0.1:8001/api/v1/results"
```

자세한 테스트 명령어는 [`curl_test_commands.md`](curl_test_commands.md) 파일을 참고하세요.

### Python 스크립트로 테스트

```bash
python test_api.py
```

## 🔧 문제 해결

### 404 에러 "분석 결과를 찾을 수 없습니다"

이 에러가 발생하는 경우 다음을 확인하세요:

1. **올바른 analysis_id 사용**: 분석 시작 시 반환된 정확한 analysis_id를 사용하고 있는지 확인
2. **분석 상태 확인**: `/results` 엔드포인트로 사용 가능한 분석 결과 목록 확인
3. **분석 완료 대기**: 분석이 완료될 때까지 충분히 기다린 후 결과 조회
4. **서버 재시작**: 이제 분석 결과가 `output/results/` 디렉토리에 JSON 파일로 저장되어 서버 재시작 후에도 유지됩니다

### 개선된 에러 메시지

404 에러 발생 시 다음과 같은 상세한 정보를 제공합니다:

```json
{
  "detail": {
    "message": "분석 결과를 찾을 수 없습니다.",
    "analysis_id": "요청한-분석-ID",
    "available_analysis_ids": ["사용가능한-ID-목록"],
    "total_available": 1,
    "suggestions": [
      "1. 올바른 analysis_id를 사용하고 있는지 확인하세요.",
      "2. /results 엔드포인트로 사용 가능한 분석 결과 목록을 확인하세요.",
      "3. 분석이 아직 진행 중이거나 실패했을 수 있습니다.",
      "4. 분석 ID 형식이 올바른지 확인하세요 (UUID 형식)."
    ]
  }
}
```

### 영구 저장소

- 모든 분석 결과는 `output/results/` 디렉토리에 JSON 파일로 저장됩니다
- 서버 재시작 시 자동으로 기존 분석 결과를 로드합니다
- 분석 완료 및 실패 시 모두 결과가 저장됩니다

## 🔧 고급 기능

### 정적 분석 상세

#### AST 분석
- **함수 및 클래스 추출**: 모든 함수, 클래스, 메서드의 시그니처와 독스트링 추출
- **의존성 그래프**: import/require 관계를 통한 모듈 의존성 그래프 생성
- **복잡도 분석**: 순환 복잡도(Cyclomatic Complexity) 및 코드 메트릭 계산
- **패턴 인식**: 디자인 패턴, 안티패턴 자동 감지

#### 기술스펙 분석
- **프레임워크 감지**: 사용 중인 프레임워크 및 라이브러리 자동 식별
- **버전 관리**: package.json, requirements.txt, pom.xml 등에서 의존성 버전 추출
- **보안 취약점**: 알려진 취약점이 있는 라이브러리 버전 감지
- **라이선스 분석**: 사용된 라이브러리의 라이선스 호환성 검사

### 문서 수집 및 분석

#### 자동 문서 수집
```python
# 수집 대상 문서 유형
DOCUMENT_PATTERNS = [
    "README*",
    "CHANGELOG*", 
    "docs/**/*.md",
    "doc/**/*.md",
    "*.wiki",
    "API.md",
    "CONTRIBUTING.md"
]

# 외부 문서 수집
EXTERNAL_DOC_SOURCES = [
    "confluence_urls",
    "notion_pages", 
    "github_wiki",
    "reference_urls"
]
```

#### 문서 구조화
- **마크다운 파싱**: 헤더, 코드 블록, 링크 구조 분석
- **API 문서 추출**: OpenAPI/Swagger 스펙 자동 추출
- **코드 예제 수집**: 문서 내 코드 예제와 실제 코드 매칭

### RAG 시스템 구축

#### 청킹 전략
```python
# 코드 청킹
CODE_CHUNK_STRATEGIES = {
    "function_based": "함수/메서드 단위로 청킹",
    "class_based": "클래스 단위로 청킹", 
    "file_based": "파일 단위로 청킹",
    "semantic_based": "의미적 블록 단위로 청킹"
}

# 문서 청킹
DOC_CHUNK_STRATEGIES = {
    "section_based": "마크다운 섹션 단위",
    "paragraph_based": "문단 단위",
    "sliding_window": "슬라이딩 윈도우 방식"
}
```

#### 메타데이터 관리
```json
{
  "chunk_metadata": {
    "source_type": "code|document",
    "file_path": "path/to/file",
    "language": "python|javascript|markdown",
    "function_name": "function_name",
    "class_name": "class_name", 
    "complexity_score": 5.2,
    "last_modified": "2025-07-31T10:00:00Z",
    "author": "developer_name",
    "tags": ["api", "database", "utility"]
  }
}
```

### 개발 표준 문서 생성

#### 코딩 스타일 가이드 생성
- **네이밍 컨벤션**: 변수, 함수, 클래스 네이밍 패턴 분석
- **코드 포맷팅**: 들여쓰기, 줄바꿈, 공백 사용 패턴 분석
- **주석 스타일**: 독스트링, 인라인 주석 스타일 분석

#### 아키텍처 패턴 문서
- **레이어 구조**: MVC, MVP, MVVM 등 아키텍처 패턴 식별
- **모듈 구조**: 패키지/모듈 구성 방식 분석
- **의존성 주입**: DI 패턴 사용 현황 분석

#### 공통 함수 가이드
- **유틸리티 함수**: 중복 사용되는 헬퍼 함수 식별
- **공통 로직**: 여러 곳에서 반복되는 비즈니스 로직 추출
- **리팩토링 제안**: 공통화 가능한 코드 블록 제안

## 🔧 문제 해결

### 분석 관련 문제

#### Git 클론 실패
**문제**: `Git clone failed: Authentication required`

**해결방법**:
```bash
# SSH 키 설정 확인
ssh -T git@github.com

# 환경 변수에 Git 토큰 설정
export GIT_TOKEN=your_github_token

# Docker 컨테이너에 SSH 키 마운트
docker-compose exec coe-rag-pipeline ssh-add /root/.ssh/id_rsa
```

#### 대용량 레포지토리 처리
**문제**: `Repository too large, analysis timeout`

**해결방법**:
```bash
# 환경 변수 조정
MAX_REPO_SIZE_MB=1000
ANALYSIS_TIMEOUT_MINUTES=60
PARALLEL_ANALYSIS_WORKERS=4

# 선택적 분석 활성화
SKIP_LARGE_FILES=true
MAX_FILE_SIZE_KB=500
```

#### 메모리 부족
**문제**: AST 분석 중 메모리 부족

**해결방법**:
```bash
# Docker 메모리 제한 증가
services:
  coe-rag-pipeline:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

# 배치 처리 크기 조정
AST_BATCH_SIZE=10
EMBEDDING_BATCH_SIZE=50
```

### RAG 시스템 문제

#### ChromaDB 연결 실패
**문제**: `Failed to connect to ChromaDB`

**해결방법**:
```bash
# ChromaDB 상태 확인
docker-compose logs chroma

# 네트워크 연결 테스트
docker-compose exec coe-rag-pipeline ping chroma

# 포트 및 호스트 설정 확인
CHROMA_HOST=chroma
CHROMA_PORT=6666
```

#### 임베딩 생성 실패
**문제**: `Embedding generation failed`

**해결방법**:
```bash
# 임베딩 서비스 상태 확인
curl http://koEmbeddings:6668/health

# 텍스트 길이 제한 확인
MAX_EMBEDDING_TEXT_LENGTH=512

# 배치 크기 조정
EMBEDDING_BATCH_SIZE=16
```

## 🧪 테스트

### 통합 테스트
```bash
# 전체 파이프라인 테스트
python test_integration.py

# 특정 분석 모듈 테스트
python test_ast_analyzer.py
python test_doc_extractor.py
python test_rag_system.py
```

### 성능 테스트
```bash
# 대용량 레포지토리 테스트
python test_performance.py --repo-size large

# 메모리 사용량 모니터링
python test_memory_usage.py
```