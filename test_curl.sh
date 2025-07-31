#!/bin/bash

# CoE RAG Pipeline API 테스트 스크립트 (cURL 버전)
# 사용법: ./test_curl.sh

BASE_URL="http://127.0.0.1:8001"

echo "🚀 CoE RAG Pipeline API 테스트 시작"
echo "서버 URL: $BASE_URL"
echo "=================================="

# 1. Health Check
echo -e "\n🔍 1. Health Check 테스트"
echo "curl -X GET \"$BASE_URL/health\""
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/health" -H "accept: application/json")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check 성공"
    echo "응답: $RESPONSE_BODY"
else
    echo "❌ Health check 실패 (HTTP $HTTP_CODE)"
    echo "서버가 실행 중인지 확인하세요: python main.py"
    exit 1
fi

# 2. 분석 시작
echo -e "\n🚀 2. 분석 시작 테스트"
ANALYZE_DATA='{
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

echo "curl -X POST \"$BASE_URL/analyze\" -H \"Content-Type: application/json\" -d '$ANALYZE_DATA'"
ANALYZE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/analyze" \
    -H "Content-Type: application/json" \
    -H "accept: application/json" \
    -d "$ANALYZE_DATA")

HTTP_CODE=$(echo "$ANALYZE_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$ANALYZE_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 분석 시작 성공"
    echo "응답: $RESPONSE_BODY"
    
    # analysis_id 추출 (jq가 없는 경우를 위한 간단한 파싱)
    ANALYSIS_ID=$(echo "$RESPONSE_BODY" | grep -o '"analysis_id":"[^"]*' | cut -d'"' -f4)
    echo "분석 ID: $ANALYSIS_ID"
else
    echo "❌ 분석 시작 실패 (HTTP $HTTP_CODE)"
    echo "응답: $RESPONSE_BODY"
    exit 1
fi

# 3. 분석 결과 조회 (진행 상황 확인)
echo -e "\n⏳ 3. 분석 진행 상황 확인"
MAX_ATTEMPTS=12
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "시도 $ATTEMPT/$MAX_ATTEMPTS: 분석 상태 확인 중..."
    
    RESULT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/results/$ANALYSIS_ID" \
        -H "accept: application/json")
    
    HTTP_CODE=$(echo "$RESULT_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$RESULT_RESPONSE" | sed '/HTTP_CODE:/d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        # 상태 추출
        STATUS=$(echo "$RESPONSE_BODY" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        echo "현재 상태: $STATUS"
        
        if [ "$STATUS" = "completed" ]; then
            echo "✅ 분석 완료!"
            echo "최종 결과:"
            echo "$RESPONSE_BODY" | head -c 500
            echo "..."
            break
        elif [ "$STATUS" = "failed" ]; then
            echo "❌ 분석 실패"
            echo "응답: $RESPONSE_BODY"
            break
        else
            echo "분석 진행 중... 5초 후 재시도"
            sleep 5
        fi
    else
        echo "❌ 결과 조회 실패 (HTTP $HTTP_CODE)"
        echo "응답: $RESPONSE_BODY"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "⏰ 분석 시간 초과 (60초)"
fi

# 4. 모든 분석 결과 목록 조회
echo -e "\n📋 4. 모든 분석 결과 목록 조회"
echo "curl -X GET \"$BASE_URL/results\""
LIST_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/results" \
    -H "accept: application/json")

HTTP_CODE=$(echo "$LIST_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 결과 목록 조회 성공"
    echo "응답: $RESPONSE_BODY"
else
    echo "❌ 결과 목록 조회 실패 (HTTP $HTTP_CODE)"
    echo "응답: $RESPONSE_BODY"
fi

# 5. 에러 케이스 테스트
echo -e "\n❌ 5. 에러 케이스 테스트"
echo "존재하지 않는 분석 ID 조회:"
echo "curl -X GET \"$BASE_URL/results/non-existent-id\""
ERROR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/results/non-existent-id" \
    -H "accept: application/json")

HTTP_CODE=$(echo "$ERROR_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$ERROR_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "404" ]; then
    echo "✅ 404 에러 정상 처리"
    echo "응답: $RESPONSE_BODY"
else
    echo "⚠️ 예상과 다른 응답 (HTTP $HTTP_CODE)"
    echo "응답: $RESPONSE_BODY"
fi

echo -e "\n🎉 테스트 완료!"
echo "=================================="
echo "💡 추가 테스트를 원한다면 curl_test_commands.md 파일을 참고하세요."