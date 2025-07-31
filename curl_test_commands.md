# 🧪 CoE RAG Pipeline API 테스트 - cURL 명령어

이 문서는 CoE RAG Pipeline API를 테스트하기 위한 cURL 명령어들을 제공합니다.

## 🚀 서버 실행

먼저 서버를 실행하세요:

```bash
# 가상환경 활성화
source .venv/bin/activate

# 서버 실행
python main.py
```

서버는 `http://127.0.0.1:8001`에서 실행됩니다.

## 📋 API 엔드포인트 테스트

### 1. Health Check

서버 상태를 확인합니다.

```bash
curl -X GET "http://127.0.0.1:8001/health" \
  -H "accept: application/json"
```

**예상 응답:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-31T10:30:00.123456"
}
```

### 2. 분석 시작 (POST /analyze)

Git 레포지토리 분석을 시작합니다.

#### 기본 분석 (모든 옵션 포함)

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
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

#### 여러 레포지토리 분석 (연관도 분석 포함)

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/octocat/Hello-World.git",
        "branch": "master"
      },
      {
        "url": "https://github.com/octocat/Spoon-Knife.git",
        "branch": "main"
      }
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }'
```

#### 커스텀 분석 ID 지정

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "analysis_id": "my-custom-analysis-001",
    "repositories": [
      {
        "url": "https://github.com/octocat/Hello-World.git",
        "branch": "master",
        "name": "Hello World Sample"
      }
    ],
    "include_ast": false,
    "include_tech_spec": true,
    "include_correlation": false
  }'
```

**예상 응답:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "message": "분석이 시작되었습니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요."
}
```

### 3. 분석 결과 조회 (GET /results/{analysis_id})

특정 분석의 결과를 조회합니다.

```bash
# analysis_id를 실제 값으로 교체하세요
curl -X GET "http://127.0.0.1:8001/results/550e8400-e29b-41d4-a716-446655440000" \
  -H "accept: application/json"
```

**분석 진행 중 응답:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "created_at": "2025-07-31T10:30:00.123456",
  "repositories": []
}
```

**분석 완료 응답:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-07-31T10:30:00.123456",
  "completed_at": "2025-07-31T10:32:15.789012",
  "repositories": [
    {
      "repository": {
        "url": "https://github.com/octocat/Hello-World.git",
        "branch": "master"
      },
      "clone_path": "/tmp/analysis_550e8400/Hello-World",
      "files": [...],
      "tech_specs": [...],
      "code_metrics": {...}
    }
  ]
}
```

### 4. 모든 분석 결과 목록 조회 (GET /results)

모든 분석 결과의 요약 정보를 조회합니다.

```bash
curl -X GET "http://127.0.0.1:8001/results" \
  -H "accept: application/json"
```

**예상 응답:**
```json
[
  {
    "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "created_at": "2025-07-31T10:30:00.123456",
    "completed_at": "2025-07-31T10:32:15.789012",
    "repository_count": 1
  },
  {
    "analysis_id": "my-custom-analysis-001",
    "status": "running",
    "created_at": "2025-07-31T10:35:00.123456",
    "completed_at": null,
    "repository_count": 0
  }
]
```

## 🔄 완전한 테스트 시나리오

다음은 전체 워크플로우를 테스트하는 스크립트입니다:

```bash
#!/bin/bash

echo "🔍 1. Health Check"
curl -X GET "http://127.0.0.1:8001/health"
echo -e "\n"

echo "🚀 2. Starting Analysis"
RESPONSE=$(curl -s -X POST "http://127.0.0.1:8001/analyze" \
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
  }')

echo $RESPONSE
ANALYSIS_ID=$(echo $RESPONSE | grep -o '"analysis_id":"[^"]*' | cut -d'"' -f4)
echo "Analysis ID: $ANALYSIS_ID"
echo -e "\n"

echo "⏳ 3. Waiting for analysis to complete..."
for i in {1..12}; do
  echo "Checking status (attempt $i/12)..."
  STATUS_RESPONSE=$(curl -s -X GET "http://127.0.0.1:8001/results/$ANALYSIS_ID")
  STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

echo -e "\n📊 4. Final Results"
curl -s -X GET "http://127.0.0.1:8001/results/$ANALYSIS_ID" | jq '.'

echo -e "\n📋 5. All Results List"
curl -s -X GET "http://127.0.0.1:8001/results" | jq '.'
```

## 🛠️ 고급 테스트 옵션

### JSON 응답 포맷팅 (jq 사용)

```bash
# jq가 설치되어 있다면 JSON을 예쁘게 포맷팅할 수 있습니다
curl -s -X GET "http://127.0.0.1:8001/health" | jq '.'
```

### 응답 헤더 포함

```bash
curl -i -X GET "http://127.0.0.1:8001/health"
```

### 상세한 요청/응답 로그

```bash
curl -v -X GET "http://127.0.0.1:8001/health"
```

### 타임아웃 설정

```bash
curl --max-time 30 -X GET "http://127.0.0.1:8001/health"
```

## ❌ 에러 테스트

### 존재하지 않는 분석 ID

```bash
curl -X GET "http://127.0.0.1:8001/results/non-existent-id" \
  -H "accept: application/json"
```

**예상 응답 (404):**
```json
{
  "detail": "분석 결과를 찾을 수 없습니다."
}
```

### 잘못된 요청 데이터

```bash
curl -X POST "http://127.0.0.1:8001/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [],
    "include_ast": "invalid_boolean"
  }'
```

## 📝 참고사항

- 서버가 `127.0.0.1:8001`에서 실행 중인지 확인하세요
- 분석은 백그라운드에서 실행되므로 완료까지 시간이 걸릴 수 있습니다
- 큰 레포지토리의 경우 분석 시간이 더 오래 걸릴 수 있습니다
- 네트워크 연결이 필요한 Git 클론 작업이 포함됩니다