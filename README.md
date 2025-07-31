# 🔍 CoE RAG Pipeline

Git 레포지토리들을 분석하여 레포지토리간 연관도, AST 분석, 기술스펙 정적 분석을 수행하는 RAG 파이프라인입니다.

## ✨ 주요 기능

- **Git 레포지토리 분석**: 여러 Git 주소를 받아 소스코드를 자동으로 클론하고 분석
- **AST 분석**: Python, JavaScript, Java, TypeScript 등 주요 언어의 추상 구문 트리 분석
- **기술스펙 정적 분석**: 의존성, 프레임워크, 라이브러리, 코드 품질 메트릭 분석
- **레포지토리간 연관도 분석**: 공통 의존성, 코드 패턴, 아키텍처 유사성 분석
- **JSON 결과 저장**: 모든 분석 결과를 구조화된 JSON 형태로 저장

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
├── main.py                 # FastAPI 메인 애플리케이션
├── models/                 # 데이터 모델 정의
├── analyzers/              # 분석 모듈들
│   ├── git_analyzer.py     # Git 레포지토리 분석
│   ├── ast_analyzer.py     # AST 분석
│   ├── tech_analyzer.py    # 기술스펙 분석
│   └── correlation_analyzer.py # 연관도 분석
├── utils/                  # 유틸리티 함수들
└── output/                 # 분석 결과 저장 디렉토리
```

## 🔧 API 엔드포인트

- **`POST /analyze`**: Git 주소 목록을 받아 전체 분석 수행
- **`GET /results/{analysis_id}`**: 분석 결과 조회
- **`GET /results`**: 모든 분석 결과 목록 조회
- **`GET /health`**: 서비스 상태 확인

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
curl -X POST "http://127.0.0.1:8001/analyze" \
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
curl -X GET "http://127.0.0.1:8001/results/{analysis_id}"

# 모든 분석 결과 목록
curl -X GET "http://127.0.0.1:8001/results"
```

자세한 테스트 명령어는 [`curl_test_commands.md`](curl_test_commands.md) 파일을 참고하세요.

### Python 스크립트로 테스트

```bash
python test_api.py
```