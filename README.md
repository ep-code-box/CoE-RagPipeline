# 🔍 CoE RAG 파이프라인

Git 리포지토리를 분석하고, AST 분석 및 기술 스택 정적 분석을 수행합니다. 분석된 코드와 문서를 기반으로 RAG 시스템을 구축합니다.

## ✨ 주요 기능

- **Git 리포지토리 분석**: 여러 Git 리포지토리를 자동으로 클론하고 분석합니다.
- **스마트 변경 감지**: 커밋 해시를 기반으로 리포지토리 변경 사항을 감지하여 불필요한 분석을 방지합니다.
- **AST 분석**: Python, JavaScript, Java, TypeScript 등 주요 언어에 대해 고정밀 추상 구문 트리 분석을 수행합니다.
- **기술 스택 분석**: 의존성 파일에서 프레임워크, 라이브러리 및 버전을 추출합니다.
- **리포지토리 간 분석**: 리포지토리 간의 의존성 및 유사성을 분석합니다.
- **소스 코드 요약**: LLM을 사용하여 소스 코드 파일을 요약하고 벡터 데이터베이스에 저장합니다.
- **자동 문서 생성**: 분석 결과를 기반으로 7가지 유형의 개발 문서를 생성합니다.
- **RDB 스키마 임베딩**: MariaDB 데이터베이스의 스키마(테이블, 컬럼) 정보를 추출하여 RAG에 포함시킵니다.

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

### RDB 스키마 임베딩

데이터베이스의 스키마 정보를 RAG에 추가하려면 다음 엔드포인트를 호출합니다.

```bash
curl -X POST http://localhost:8001/api/v1/embed_rdb_schema
```

### 벡터 유사도 검색

저장된 벡터 데이터베이스에서 유사한 문서를 검색합니다. `group_name`을 사용하여 특정 그룹의 문서와 RDB 스키마 정보를 함께 검색할 수 있습니다.

```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "사용자 정보 테이블",
    "k": 5,
    "group_name": "UserService"
  }'
```

```
CoE-RagPipeline/
```
├── main.py                 # FastAPI 메인 애플리케이션
├── run.sh                  # 실행 스크립트
├── Dockerfile              # Docker 이미지 빌드 파일
├── .env.sample             # 환경 변수 예시 파일
├── requirements.txt        # 프로젝트 의존성
├── README.md               # 프로젝트 문서
├── analyzers/              # 분석 모듈 (Git, AST 등)
├── config/                 # 애플리케이션 설정
├── core/                   # 핵심 로직 (데이터베이스 등)
├── models/                 # Pydantic 데이터 모델
├── output/                 # 분석 결과, 문서, 요약 저장
├── routers/                # API 라우터
└── services/               # 비즈니스 로직 서비스
```
