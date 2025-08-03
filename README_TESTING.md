# 🧪 CoE RAG Pipeline - 테스트 가이드

이 문서는 CoE RAG Pipeline 프로젝트의 테스트 구조와 실행 방법을 설명합니다.

## 📋 목차

- [테스트 구조](#테스트-구조)
- [테스트 실행](#테스트-실행)
- [테스트 타입](#테스트-타입)
- [CI/CD](#cicd)
- [개발 환경 설정](#개발-환경-설정)

## 🏗️ 테스트 구조

```
tests/
├── __init__.py
├── conftest.py              # 공통 픽스처 및 설정
├── unit/                    # 단위 테스트
│   ├── __init__.py
│   ├── test_analysis_service.py
│   ├── test_embedding_service.py
│   ├── test_llm_service.py
│   ├── test_database.py
│   ├── test_analyzers.py
│   └── test_utils.py
├── api/                     # API 테스트
│   ├── __init__.py
│   ├── test_health_router.py
│   ├── test_analysis_router.py
│   ├── test_embedding_router.py
│   └── test_document_generation_router.py
└── integration/             # 통합 테스트
    ├── __init__.py
    └── test_full_analysis_flow.py
```

## 🚀 테스트 실행

### 기본 실행 방법

```bash
# 모든 테스트 실행
python test_runner.py

# 또는 Make 사용
make test
```

### 테스트 타입별 실행

```bash
# 단위 테스트만 실행
python test_runner.py --type unit
make test-unit

# API 테스트만 실행
python test_runner.py --type api
make test-api

# 통합 테스트만 실행
python test_runner.py --type integration
make test-integration

# 모든 테스트 + 커버리지
python test_runner.py --type all
make test-all
```

### 추가 옵션

```bash
# 커버리지 없이 실행
python test_runner.py --no-coverage

# 조용한 모드로 실행
python test_runner.py --quiet

# 린팅만 실행
python test_runner.py --lint
make lint

# 타입 체킹만 실행
python test_runner.py --type-check
make type-check

# 모든 체크 실행 (테스트 + 린팅 + 타입체킹)
python test_runner.py --all-checks
make check-all
```

## 🔍 테스트 타입

### 1. 단위 테스트 (Unit Tests)

**위치**: `tests/unit/`  
**마커**: `@pytest.mark.unit`

핵심 비즈니스 로직과 개별 함수/클래스를 테스트합니다.

- **test_analysis_service.py**: 분석 서비스 로직
- **test_embedding_service.py**: 임베딩 및 벡터 검색
- **test_llm_service.py**: LLM 문서 생성
- **test_database.py**: 데이터베이스 모델 및 연결
- **test_analyzers.py**: Git 및 AST 분석기
- **test_utils.py**: 유틸리티 함수들

### 2. API 테스트 (API Tests)

**위치**: `tests/api/`  
**마커**: `@pytest.mark.api`

FastAPI 엔드포인트의 HTTP 요청/응답을 테스트합니다.

- **test_health_router.py**: 헬스체크 API
- **test_analysis_router.py**: 분석 관련 API
- **test_embedding_router.py**: 검색 관련 API
- **test_document_generation_router.py**: 문서 생성 API

### 3. 통합 테스트 (Integration Tests)

**위치**: `tests/integration/`  
**마커**: `@pytest.mark.integration`

여러 컴포넌트가 함께 동작하는 전체 플로우를 테스트합니다.

- **test_full_analysis_flow.py**: 전체 분석 워크플로우

### 4. 특수 마커

- `@pytest.mark.slow`: 느린 테스트 (실제 외부 API 호출 등)
- `@pytest.mark.database`: 데이터베이스 관련 테스트

## 🔧 개발 환경 설정

### 1. 테스트 의존성 설치

```bash
# 기본 의존성 설치
pip install -r requirements.txt

# 개발 환경 설정 (린팅, 타입체킹 도구 포함)
make setup-dev
```

### 2. 환경 변수 설정

테스트 실행 시 필요한 환경 변수:

```bash
export TESTING=true
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=test_user
export DB_PASSWORD=test_password
export DB_NAME=test_coe_db
export OPENAI_API_KEY=test-api-key
```


## 📊 커버리지 리포트

테스트 커버리지는 자동으로 생성됩니다:

```bash
# 커버리지 리포트 생성
make coverage

# HTML 리포트 확인
open htmlcov/index.html
```

## 🔒 보안 테스트

```bash
# 보안 취약점 검사
make security

# 결과 파일 확인
cat bandit-report.json
cat safety-report.json
```

## 🚀 CI/CD

GitHub Actions를 통한 자동화된 테스트:

- **트리거**: `main`, `develop` 브랜치 push 및 PR
- **Python 버전**: 3.9, 3.10, 3.11
- **데이터베이스**: MySQL 8.0
- **실행 단계**:
  1. 린팅 (flake8)
  2. 타입 체킹 (mypy)
  3. 단위 테스트
  4. 통합 테스트
  5. API 테스트
  6. 커버리지 리포트 업로드

## 🛠️ 테스트 작성 가이드

### 1. 테스트 파일 명명 규칙

- 파일명: `test_<모듈명>.py`
- 클래스명: `Test<클래스명>`
- 함수명: `test_<기능>_<상황>`

### 2. 픽스처 사용

```python
def test_example(client, sample_data, mock_service):
    # Given
    # 테스트 데이터 준비
    
    # When
    # 테스트 실행
    
    # Then
    # 결과 검증
```

### 3. 모킹 가이드

```python
@patch('module.external_service')
def test_with_mock(mock_service):
    mock_service.return_value = expected_result
    # 테스트 로직
```

### 4. 비동기 테스트

```python
@pytest.mark.asyncio
async def test_async_function(async_client):
    response = await async_client.get(/api/endpoint)
    assert response.status_code == 200
```

## 🐛 디버깅

### 테스트 실패 시 디버깅

```bash
# 상세한 출력으로 실행
pytest -v -s tests/unit/test_specific.py::test_function

# 특정 테스트만 실행
pytest tests/unit/test_analysis_service.py::TestRagAnalysisService::test_create_analysis_request_success

# 디버거와 함께 실행
pytest --pdb tests/unit/test_specific.py
```

### 로그 확인

```bash
# 로그와 함께 테스트 실행
pytest -s --log-cli-level=INFO
```

## 📈 성능 테스트

```bash
# 느린 테스트만 실행
pytest -m slow

# 성능 테스트 실행
make perf-test
```

## 🔄 지속적 개선

1. **커버리지 목표**: 80% 이상 유지
2. **테스트 속도**: 단위 테스트는 빠르게, 통합 테스트는 필요시에만
3. **모킹 전략**: 외부 의존성은 모킹, 내부 로직은 실제 테스트
4. **문서화**: 복잡한 테스트는 주석으로 설명

## 🆘 문제 해결

### 자주 발생하는 문제

1. **데이터베이스 연결 오류**
   ```bash
   # 테스트 DB 연결 확인
   make db-test
   ```

2. **의존성 충돌**
   ```bash
   # 가상환경 재생성
   pip install -r requirements.txt --force-reinstall
   ```

3. **포트 충돌**
   ```bash
   # 사용 중인 포트 확인
   lsof -i :8001
   ```

## 📞 지원

테스트 관련 문제가 있으면:

1. 이 문서를 먼저 확인
2. GitHub Issues에 문제 보고
3. 팀 슬랙 채널에서 질문

---

**Happy Testing! 🎉**
