# 🔍 CoE RAG Pipeline

Git 레포지토리들을 분석하여 레포지토리간 연관도, AST 분석, 기술스펙 정적 분석을 수행하는 RAG 파이프라인입니다.

## ✨ 주요 기능

- **Git 레포지토리 분석**: 여러 Git 주소를 받아 소스코드를 자동으로 클론하고 분석
- **스마트 레포지토리 분석**: 같은 레포지토리라도 commit 변경 시 새로운 분석 수행, commit이 동일하면 기존 결과 재사용으로 효율성 향상 ⭐ **NEW**
- **AST 분석**: Python, JavaScript, Java, TypeScript 등 주요 언어의 추상 구문 트리 분석
- **기술스펙 정적 분석**: 의존성, 프레임워크, 라이브러리, 코드 품질 메트릭 분석
- **레포지토리간 연관도 분석**: 공통 의존성, 코드 패턴, 아키텍처 유사성 분석
- **문서 자동 수집**: doc 폴더, README, 참조 URL에서 개발 문서 자동 수집 및 분석
- **LLM 기반 문서 자동 생성**: 분석 결과를 바탕으로 7가지 타입의 개발 문서 자동 생성 ⭐ **NEW**
  - **개발 가이드**: 코딩 컨벤션, 모범 사례, 프로젝트 구조 가이드
  - **API 문서**: 엔드포인트 명세, 사용법, 예제 코드
  - **아키텍처 개요**: 시스템 구조, 컴포넌트 관계, 설계 패턴
  - **코드 리뷰 요약**: 코드 품질 이슈, 개선 사항, 보안 취약점
  - **기술 명세서**: 기술 스택, 의존성, 환경 요구사항
  - **배포 가이드**: 환경 설정, 빌드 과정, 배포 단계
  - **문제 해결 가이드**: 일반적 오류, 해결법, 디버깅 팁
- **마크다운 리포트 자동 생성**: 분석 완료 후 상세한 마크다운 형식의 분석 리포트 자동 생성
- **RAG 시스템 구축**: 분석된 코드와 문서를 벡터화하여 검색 가능한 지식베이스 구축
- **분석별 RAG 검색**: analysis_id 기반으로 특정 분석 결과만 검색하여 정확도 향상 ⭐ **NEW**
- **JSON 결과 저장**: 모든 분석 결과를 구조화된 JSON 형태로 저장
- **임베딩 및 벡터 저장**: ChromaDB를 통한 고성능 벡터 검색 지원

## 🚀 시작하기

### 1. 환경 설정

CoE-RagPipeline은 **통합 .env 파일**로 local과 docker 환경을 모두 지원합니다.

#### 📋 환경 설정 파일

```bash
# 환경 설정 파일 생성
cp .env.example .env
# 또는 로컬 개발용
cp .env.example .env.local
```

#### 🔑 필수 설정 항목

```bash
# SKAX API 설정 (메인 LLM용)
SKAX_API_KEY=your_skax_api_key_here

# OpenAI API 설정 (임베딩용)
OPENAI_API_KEY=your_openai_api_key_here
```

#### 📊 환경별 설정 차이

| 설정 항목 | 로컬 환경 (.env.local) | Docker 환경 (오버라이드) |
|-----------|----------------------|-------------------------|
| **데이터베이스** |
| DB_HOST | localhost | mariadb |
| DB_PORT | 6667 | 3306 |
| **ChromaDB** |
| CHROMA_HOST | localhost | chroma |
| CHROMA_PORT | 6666 | 8000 |
| **Redis** |
| REDIS_HOST | localhost | redis |
| REDIS_PORT | 6669 | 6379 |

#### 🚀 로컬 개발 환경 설정

##### run.sh 스크립트 활용 (권장)

```bash
# 1. 인프라 서비스만 Docker로 실행
docker-compose -f ../docker-compose.local.yml up -d

# 2. run.sh 스크립트로 실행 (.venv 자동 관리)
./run.sh
```

`run.sh` 스크립트는 다음을 자동으로 수행합니다:
- `.venv` 가상환경 자동 생성/활성화
- `requirements.txt` 의존성 자동 설치
- `.env.local` 환경변수 자동 로드
- `python main.py` 서버 실행

##### 수동 실행 방식

```bash
# 가상 환경 설정
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env.local
# .env.local 파일에서 API 키 설정

# 개발 서버 실행
python main.py
```

### 2. 서버 실행

```bash
python main.py
```

## 📂 프로젝트 구조

```
CoE-RagPipeline/
├── main.py                 # FastAPI 메인 애플리케이션
├── Dockerfile              # Docker 이미지 빌드 파일
├── .env.example            # 환경 변수 예시 파일 (미포함)
├── requirements.txt        # 프로젝트 의존성
├── README.md               # 프로젝트 문서
├── README_EMBEDDING.md     # 임베딩 관련 상세 가이드
├── TROUBLESHOOTING.md      # 문제 해결 가이드
├── curl_test_commands.md   # cURL 테스트 명령어 모음
├── test_curl.sh            # 자동화된 cURL 테스트 스크립트
├── server.log              # 서버 로그 파일
├── 설계.md                 # 설계 문서 (한국어)
├── analyzers/              # 분석 모듈들
│   ├── __init__.py
│   ├── git_analyzer.py     # Git 레포지토리 분석
│   └── ast_analyzer.py     # AST 분석 및 코드 파싱
├── chroma_db/              # ChromaDB 벡터 저장소 디렉토리
├── config/                 # 설정 관리
│   ├── __init__.py
│   ├── settings.py         # 애플리케이션 설정
│   └── database.py         # 데이터베이스 설정
├── core/                   # 핵심 비즈니스 로직
│   ├── __init__.py
│   └── database.py         # 데이터베이스 연결 및 모델
├── models/                 # 데이터 모델 정의
│   ├── __init__.py
│   └── schemas.py          # Pydantic 스키마
├── output/                 # 분석 결과 저장 디렉토리
│   ├── results/            # JSON 분석 결과 파일들
│   ├── markdown/           # 마크다운 리포트 파일들
│   └── documents/          # LLM 생성 문서 파일들 ⭐ **NEW**
├── routers/                # API 라우터들
│   ├── __init__.py
│   ├── analysis.py         # 분석 관련 API
│   ├── document_generation.py # 문서 생성 관련 API ⭐ **NEW**
│   ├── embedding.py        # 임베딩 관련 API
│   └── health.py           # 헬스체크 API
├── services/               # 비즈니스 로직 서비스들
│   ├── __init__.py
│   ├── analysis_service.py # Git 분석 및 처리 서비스
│   ├── embedding_service.py # 임베딩 및 벡터 검색 서비스
│   └── llm_service.py      # LLM 기반 문서 생성 서비스 ⭐ **NEW**
└── utils/                  # 유틸리티 함수들
    ├── __init__.py
    ├── app_initializer.py  # 애플리케이션 초기화 유틸리티
    ├── file_utils.py       # 파일 관련 유틸리티
    ├── markdown_generator.py # 마크다운 리포트 생성 유틸리티
    ├── server_utils.py     # 서버 관련 유틸리티
    └── tech_utils.py       # 기술스펙 관련 유틸리티
```

## 🔧 API 엔드포인트

### 🔍 Git 분석 및 코드 처리
- **`POST /api/v1/analyze`**: Git 레포지토리 전체 분석 수행
  - AST 분석, 기술스펙 분석, 연관도 분석 옵션 지원
  - **스마트 중복 감지**: commit hash 기준으로 변경사항 감지, 동일 commit은 기존 결과 재사용 ⭐ **NEW**
  - 자동 문서 수집 및 임베딩 처리
  - **분석 완료 시 마크다운 리포트 자동 생성** (`output/markdown/` 디렉토리에 저장)
  - 백그라운드 작업으로 비동기 처리
- **`GET /api/v1/results`**: 모든 분석 결과 목록 조회
  - 완료/진행중/실패 상태별 필터링 지원
  - 페이지네이션 지원
- **`GET /api/v1/results/{analysis_id}`**: 특정 분석 결과 상세 조회
  - AST 분석 결과, 기술 스택 정보 포함
  - 파일별 상세 분석 데이터 제공

### 📄 문서 생성 (LLM 기반)
- **`POST /api/v1/documents/generate`**: 분석 결과 기반 문서 자동 생성 ⭐ **NEW**
  - 7가지 문서 타입 지원: 개발 가이드, API 문서, 아키텍처 개요, 코드 리뷰 요약, 기술 명세서, 배포 가이드, 문제 해결 가이드
  - 한국어/영어 지원
  - 사용자 정의 프롬프트 지원
  - 백그라운드 작업으로 비동기 처리
- **`GET /api/v1/documents/status/{task_id}`**: 문서 생성 작업 상태 조회 ⭐ **NEW**
  - 진행 상황 및 완료 여부 확인
  - 생성된 문서 정보 제공
- **`GET /api/v1/documents/types`**: 지원되는 문서 타입 목록 조회 ⭐ **NEW**
- **`GET /api/v1/documents/list/{analysis_id}`**: 특정 분석의 생성된 문서 목록 조회 ⭐ **NEW**
- **`DELETE /api/v1/documents/{analysis_id}/{document_type}`**: 생성된 문서 삭제 ⭐ **NEW**

### 🔍 벡터 검색 및 RAG
- **`POST /api/v1/search`**: 벡터 유사도 검색
  - ChromaDB 기반 고성능 검색
  - 메타데이터 필터링 지원
  - **analysis_id 기반 검색**: 특정 분석 결과만 검색 ⭐ **NEW**
  - 유사도 점수 및 컨텍스트 제공
- **`GET /api/v1/stats`**: 임베딩 및 벡터 통계 정보
  - 총 문서 수, 벡터 차원, 컬렉션 정보
  - 검색 성능 메트릭

### 🏥 시스템 관리
- **`GET /health`**: 서비스 상태 및 의존성 확인
  - 데이터베이스 연결 상태
  - ChromaDB 연결 상태
  - 임베딩 서비스 연결 상태

## 🧪 API 테스트

### 🏥 헬스체크 및 시스템 상태

```bash
# 서비스 상태 확인
curl -X GET "http://localhost:8001/health"

# 벡터 데이터베이스 통계 확인
curl -X GET "http://localhost:8001/api/v1/stats"
```

### 🔍 Git 레포지토리 분석

```bash
# 분석 시작 (공개 레포지토리)
curl -X POST "http://localhost:8001/api/v1/analyze" \
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
    "include_correlation": true
  }'

# 새로운 분석 응답 예시 (commit 변경 감지):
# {
#   "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c",
#   "status": "started",
#   "message": "분석이 시작되었습니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요."
# }

# 동일 commit 재사용 응답 예시 (NEW!):
# {
#   "analysis_id": "existing-analysis-id",
#   "status": "existing",
#   "message": "모든 레포지토리의 commit이 동일합니다. 기존 분석 결과를 사용합니다: existing-analysis-id"
# }

# commit 변경 감지 응답 예시 (NEW!):
# {
#   "analysis_id": "new-analysis-uuid",
#   "status": "started", 
#   "message": "레포지토리 commit이 변경되어 새로운 분석을 시작합니다. 기존: abc123, 최신: def456"
# }
```

### 📊 분석 결과 조회

```bash
# 모든 분석 결과 목록 조회
curl -X GET "http://localhost:8001/api/v1/results"

# 특정 분석 결과 상세 조회 (analysis_id는 위에서 받은 값 사용)
curl -X GET "http://localhost:8001/api/v1/results/3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c"
```

### 📄 문서 생성 테스트

```bash
# 지원되는 문서 타입 목록 조회
curl -X GET "http://localhost:8001/api/v1/documents/types"

# 문서 생성 시작 (분석 완료 후 사용 가능)
curl -X POST "http://localhost:8001/api/v1/documents/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c",
    "document_types": ["development_guide", "api_documentation"],
    "language": "korean",
    "custom_prompt": "FastAPI 관련 내용을 중심으로 작성해주세요."
  }'

# 문서 생성 응답 예시:
# {
#   "task_id": "doc-task-12345",
#   "status": "pending",
#   "message": "문서 생성이 시작되었습니다. /status/{task_id} 엔드포인트로 진행 상황을 확인하세요."
# }

# 문서 생성 상태 확인
curl -X GET "http://localhost:8001/api/v1/documents/status/doc-task-12345"

# 생성된 문서 목록 조회
curl -X GET "http://localhost:8001/api/v1/documents/list/3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c"

# 특정 문서 삭제
curl -X DELETE "http://localhost:8001/api/v1/documents/3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c/development_guide"
```

### 🔍 벡터 검색 테스트

```bash
# 일반 벡터 검색 (분석 완료 후 사용 가능)
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 함수 정의",
    "k": 5,
    "filter_metadata": {
      "file_type": "python"
    }
  }'

# 특정 분석 결과에서만 검색 (NEW!)
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 함수 정의",
    "k": 5,
    "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c"
  }'
```

### 🔧 자동화된 테스트 스크립트

```bash
# 실행 권한 부여
chmod +x test_curl.sh

# 전체 테스트 실행
./test_curl.sh

# Python 테스트 스크립트 실행
python test_api.py
```

자세한 테스트 명령어는 [`curl_test_commands.md`](curl_test_commands.md) 파일을 참고하세요.

## 📄 LLM 기반 문서 자동 생성

### 🚀 개요

CoE RAG Pipeline에 LLM을 활용한 문서 자동 생성 기능이 추가되었습니다. 이 기능은 Git 레포지토리 분석 결과를 바탕으로 다양한 타입의 개발 문서를 자동으로 생성합니다.

### ✨ 주요 기능

#### 🔄 자동 문서 생성
- **분석 완료 시 자동 실행**: Git 분석이 완료되면 자동으로 기본 문서들을 생성
- **백그라운드 처리**: 문서 생성은 비동기로 처리되어 API 응답 속도에 영향 없음
- **다중 문서 생성**: 한 번의 요청으로 여러 타입의 문서를 동시 생성

#### 📋 지원 문서 타입

1. **development_guide**: 개발 가이드 - 코딩 컨벤션, 아키텍처 패턴, 모범 사례
2. **api_documentation**: API 문서 - 엔드포인트 설명, 요청/응답 예시, 사용법 가이드
3. **architecture_overview**: 아키텍처 개요 - 시스템 구조, 컴포넌트 관계, 데이터 흐름
4. **code_review_summary**: 코드 리뷰 요약 - 발견된 이슈, 개선 사항, 권장사항
5. **technical_specification**: 기술 명세서 - 기술 스택, 의존성 정보, 버전 정보
6. **deployment_guide**: 배포 가이드 - 환경 설정, 빌드 과정, 배포 단계
7. **troubleshooting_guide**: 문제 해결 가이드 - 일반적 오류, 해결 방법, 디버깅 팁

### 📁 파일 구조

```
CoE-RagPipeline/
├── services/
│   └── llm_service.py              # LLM 문서 생성 서비스
├── routers/
│   └── document_generation.py     # 문서 생성 API 엔드포인트
├── models/
│   └── schemas.py                 # 문서 생성 관련 스키마 추가
├── output/
│   └── documents/                 # 생성된 문서 저장 디렉토리
│       └── {analysis_id}/         # 분석별 문서 폴더
│           ├── development_guide_korean.md
│           ├── api_documentation_korean.md
│           └── ...
└── main.py                        # 문서 생성 라우터 추가
```

### 🔧 설정

#### 환경 변수
```bash
# OpenAI API 키 (필수)
export OPENAI_API_KEY="your-openai-api-key"
```

#### 설정 파일 (`config/settings.py`)
```python
class Settings:
    # OpenAI 설정
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # 디렉토리 설정
    DOCUMENTS_DIR: str = "output/documents"
```

## 🔄 스마트 레포지토리 분석 (Commit 기반)

### 기능 설명

시스템은 분석 요청 시 다음과 같이 commit 기준으로 변경사항을 감지하고 처리합니다:

1. **Commit 기반 변경 감지**: 레포지토리 URL, 브랜치, **commit hash**를 기준으로 변경사항 확인
2. **스마트 분석 결정**: commit이 변경된 경우에만 새로운 분석 수행, 동일 commit은 기존 결과 재사용
3. **효율성 향상**: 불필요한 중복 분석을 방지하면서도 코드 변경사항은 정확히 반영

### API 응답 예시

#### 새로운 분석이 필요한 경우 (Commit 변경 감지)
```json
{
  "analysis_id": "new-analysis-uuid",
  "status": "started",
  "message": "분석이 시작되었습니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요.",
  "existing_analyses": null,
  "commit_info": {
    "repository_url": "https://github.com/example/repo.git",
    "previous_commit": "abc123ef",
    "latest_commit": "def456gh",
    "reason": "commit_changed"
  }
}
```

#### 모든 레포지토리의 Commit이 동일한 경우
```json
{
  "analysis_id": "existing-analysis-uuid",
  "status": "existing",
  "message": "모든 레포지토리의 commit이 동일합니다. 기존 분석 결과를 사용합니다: existing-analysis-uuid",
  "commit_info": {
    "repository_url": "https://github.com/example/repo.git",
    "commit_hash": "abc123ef",
    "reason": "same_commit"
  }
}
```

## 🔍 분석별 RAG 검색

### 기능 설명

특정 분석 결과(analysis_id)를 기준으로 RAG 검색을 수행하여 더 정확하고 관련성 높은 결과를 제공합니다.

### 메타데이터 구조

임베딩된 문서들은 다음과 같은 메타데이터를 포함합니다:

```json
{
  "analysis_id": "분석 ID",
  "repository_url": "레포지토리 URL",
  "repository_name": "레포지토리 이름",
  "document_type": "문서 타입 (repository_summary, tech_spec, ast_analysis, code_metrics, correlation_analysis)",
  "language": "프로그래밍 언어",
  "file_path": "파일 경로",
  "created_at": "생성 시간"
}
```

## 🔧 문제 해결

### 404 에러 "분석 결과를 찾을 수 없습니다"

이 에러가 발생하는 경우 다음을 확인하세요:

1. **올바른 analysis_id 사용**: 분석 시작 시 반환된 정확한 analysis_id를 사용하고 있는지 확인
2. **분석 상태 확인**: `/results` 엔드포인트로 사용 가능한 분석 결과 목록 확인
3. **분석 완료 대기**: 분석이 완료될 때까지 충분히 기다린 후 결과 조회
4. **Commit 변경 확인**: 같은 레포지토리라도 commit이 변경되면 새로운 analysis_id가 생성됩니다
5. **서버 재시작**: 이제 분석 결과가 `output/results/` 디렉토리에 JSON 파일로 저장되어 서버 재시작 후에도 유지됩니다

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
      "4. 같은 레포지토리라도 commit이 변경되면 새로운 analysis_id가 생성됩니다.",
      "5. 분석 ID 형식이 올바른지 확인하세요 (UUID 형식)."
    ]
  }
}
```

### 영구 저장소

- 모든 분석 결과는 `output/results/` 디렉토리에 JSON 파일로 저장됩니다
- 서버 재시작 시 자동으로 기존 분석 결과를 로드합니다
- 분석 완료 및 실패 시 모두 결과가 저장됩니다

### LLM 문서 생성 관련 문제

#### OpenAI API 키 오류
**문제**: `ValueError: OPENAI_API_KEY가 설정되지 않았습니다.`

**해결**: 환경 변수 `OPENAI_API_KEY` 설정

#### 분석 결과 없음
**문제**: `404: 분석 결과를 찾을 수 없습니다.`

**해결**: 먼저 `/api/v1/analyze`로 분석 수행

#### 문서 생성 실패
- 로그에서 상세 오류 확인
- OpenAI API 할당량 확인
- 네트워크 연결 확인

## 🔧 고급 기능

### 📊 정적 분석 상세

#### AST (추상 구문 트리) 분석
- **함수 및 클래스 추출**: 모든 함수, 클래스, 메서드의 시그니처와 독스트링 추출
- **의존성 그래프**: import/require 관계를 통한 모듈 의존성 그래프 생성
- **복잡도 분석**: 순환 복잡도(Cyclomatic Complexity) 및 코드 메트릭 계산
- **패턴 인식**: 디자인 패턴, 안티패턴 자동 감지

#### 기술스펙 분석
- **프레임워크 감지**: 사용 중인 프레임워크 및 라이브러리 자동 식별
- **버전 관리**: package.json, requirements.txt, pom.xml 등에서 의존성 버전 추출
- **보안 취약점**: 알려진 취약점이 있는 라이브러리 버전 감지
- **라이선스 분석**: 사용된 라이브러리의 라이선스 호환성 검사

### 📚 문서 수집 및 분석

#### 자동 문서 수집
```python
# 수집 대상 문서 유형
DOCUMENT_PATTERNS = [
    "README*",           # README 파일들
    "CHANGELOG*",        # 변경 이력
    "docs/**/*.md",      # 문서 폴더
    "doc/**/*.md",       # 문서 폴더 (단수형)
    "*.wiki",            # 위키 파일
    "API.md",            # API 문서
    "CONTRIBUTING.md"    # 기여 가이드
]
```

#### 문서 구조화 및 임베딩
- **마크다운 파싱**: 헤더, 코드 블록, 링크 구조 분석
- **API 문서 추출**: OpenAPI/Swagger 스펙 자동 추출
- **코드 예제 수집**: 문서 내 코드 예제와 실제 코드 매칭
- **자동 벡터화**: 수집된 문서를 ChromaDB에 자동 임베딩

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