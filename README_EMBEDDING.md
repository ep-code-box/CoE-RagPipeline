# 🔍 CoE RAG Pipeline - Embedding 기능

CoE-RagPipeline에 분석 결과를 embedding하여 Chroma 벡터 데이터베이스에 저장하는 기능이 추가되었습니다.

## ✨ 새로운 기능

### 1. 자동 Embedding 처리
- 분석 완료 시 자동으로 분석 결과를 embedding하여 Chroma DB에 저장
- 레포지토리 요약, 기술스펙, AST 분석, 코드 메트릭, 연관도 분석 등 모든 분석 결과를 벡터화

### 2. 벡터 검색 API
- 자연어 쿼리로 유사한 분석 결과 검색
- 메타데이터 필터링 지원
- 유사도 점수와 함께 결과 반환

### 3. 통계 및 모니터링
- Chroma 데이터베이스 통계 정보 조회
- 저장된 문서 수 및 저장 경로 확인

## 🚀 사용 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

새로 추가된 패키지:
- `openai`: OpenAI API 클라이언트
- `langchain`: LangChain 프레임워크
- `langchain-openai`: OpenAI 통합
- `langchain-chroma`: Chroma 벡터스토어
- `chromadb`: Chroma 데이터베이스

### 2. 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# OpenAI 설정 (embedding용)
OPENAI_API_KEY="your-api-key-here"
OPENAI_API_BASE="https://guest-api.sktax.chat/v1"

# Chroma 설정
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

### 3. 서버 실행

```bash
python3 main.py
```

### 4. 분석 실행 (자동 Embedding 포함)

기존 분석 API를 사용하면 자동으로 embedding이 수행됩니다:

```bash
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
```

## 🔧 새로운 API 엔드포인트

### 1. 벡터 검색

```bash
curl -X POST "http://127.0.0.1:8001/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python FastAPI dependencies",
    "k": 5
  }'
```

**응답 예시:**
```json
[
  {
    "content": "Language: Python\\nPackage Manager: pip\\nDependencies:\\n  - fastapi\\n  - uvicorn\\n  - pydantic",
    "metadata": {
      "analysis_id": "abc123",
      "repository_url": "https://github.com/example/repo.git",
      "document_type": "tech_spec",
      "language": "Python"
    },
    "score": 0.8542
  }
]
```

### 2. 통계 정보 조회

```bash
curl -X GET "http://127.0.0.1:8001/embeddings/stats"
```

**응답 예시:**
```json
{
  "total_documents": 25,
  "persist_directory": "./chroma_db"
}
```

## 📊 Document 타입

Embedding되는 문서들은 다음과 같은 타입으로 분류됩니다:

1. **repository_summary**: 레포지토리 기본 정보 및 통계
2. **tech_spec**: 기술스펙 및 의존성 정보
3. **ast_analysis**: AST 분석 결과 (파일별)
4. **code_metrics**: 코드 메트릭 정보
5. **correlation_analysis**: 레포지토리간 연관도 분석

## 🔍 검색 예시

### 기술스펙 검색
```bash
curl -X POST "http://127.0.0.1:8001/search?query=Python%20dependencies&k=3"
```

### 특정 분석 결과 검색
```bash
curl -X POST "http://127.0.0.1:8001/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "FastAPI web framework",
    "k": 5,
    "filter_metadata": {"document_type": "tech_spec"}
  }'
```

### 레포지토리별 검색
```bash
curl -X POST "http://127.0.0.1:8001/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication code",
    "k": 3,
    "filter_metadata": {"repository_name": "my-project"}
  }'
```

## 🧪 테스트

### 단위 테스트 실행

```bash
python3 test_embedding_simple.py
```

이 테스트는 서버 없이 EmbeddingService의 기본 기능을 검증합니다.

### 통합 테스트 실행

1. 서버 시작: `python3 main.py`
2. 별도 터미널에서: `python3 test_embedding.py`

## 📁 파일 구조

```
CoE-RagPipeline/
├── services/
│   ├── __init__.py
│   └── embedding_service.py      # 새로 추가된 Embedding 서비스
├── main.py                       # Embedding 통합 및 새 API 엔드포인트
├── requirements.txt              # 새 의존성 추가
├── .env                          # Embedding 관련 환경 변수
├── test_embedding_simple.py      # 단위 테스트
├── test_embedding.py             # 통합 테스트
└── README_EMBEDDING.md           # 이 문서
```

## 🔧 주요 구현 사항

### EmbeddingService 클래스

- **초기화**: OpenAI Embeddings, Chroma 벡터스토어, 텍스트 분할기 설정
- **문서 생성**: 분석 결과를 구조화된 텍스트 문서로 변환
- **Embedding 처리**: OpenAI API를 사용하여 텍스트를 벡터로 변환
- **벡터 저장**: Chroma 데이터베이스에 벡터와 메타데이터 저장
- **검색 기능**: 자연어 쿼리로 유사한 문서 검색

### 통합 지점

- `perform_analysis()` 함수에서 분석 완료 후 자동 embedding 수행
- 실패 시에도 로그 기록하고 분석 프로세스는 계속 진행
- 환경 변수를 통한 설정 관리

## ⚠️ 주의사항

1. **API 키 설정**: OpenAI API 키가 올바르게 설정되어야 합니다
2. **디스크 공간**: Chroma 데이터베이스는 로컬 디스크에 저장됩니다
3. **네트워크**: OpenAI API 호출을 위한 인터넷 연결이 필요합니다
4. **비용**: OpenAI Embedding API 사용에 따른 비용이 발생할 수 있습니다

## 🚀 향후 개선 사항

1. **배치 처리**: 대량 문서 처리를 위한 배치 embedding
2. **캐싱**: 중복 문서 embedding 방지를 위한 캐싱 메커니즘
3. **다양한 Embedding 모델**: OpenAI 외 다른 embedding 모델 지원
4. **고급 검색**: 하이브리드 검색, 재랭킹 등 고급 검색 기능
5. **UI**: 검색 결과를 시각화하는 웹 인터페이스

## 📞 문제 해결

### 일반적인 문제들

1. **"No embedding data received" 오류**
   - OpenAI API 키 확인
   - 네트워크 연결 확인
   - API 베이스 URL 확인

2. **Chroma 데이터베이스 오류**
   - 디스크 공간 확인
   - 권한 설정 확인
   - 디렉토리 경로 확인

3. **검색 결과 없음**
   - 분석 데이터가 embedding되었는지 확인
   - 검색 쿼리 조정
   - 통계 API로 저장된 문서 수 확인