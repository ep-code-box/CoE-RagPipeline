#!/usr/bin/env python3
import requests
import json

# 서버 URL
BASE_URL = "http://localhost:8001"

def test_health():
    """헬스체크 테스트"""
    print("=== 헬스체크 테스트 ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_analyze():
    """분석 API 테스트"""
    print("=== 분석 API 테스트 ===")
    data = {
        "repositories": [
            {
                "url": "https://github.com/octocat/Hello-World.git",
                "branch": "master"
            }
        ],
        "include_ast": True,
        "include_tech_spec": True,
        "include_correlation": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/analyze",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    if response.status_code == 200:
        return response.json().get("analysis_id")
    return None

def test_document_generation(analysis_id):
    """문서 생성 API 테스트"""
    print("=== 문서 생성 API 테스트 ===")
    data = {
        "analysis_id": analysis_id,
        "document_types": ["development_guide"],
        "language": "korean"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/documents/generate",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

if __name__ == "__main__":
    # 헬스체크
    test_health()
    
    # 분석 테스트
    analysis_id = test_analyze()
    
    # 문서 생성 테스트 (분석 ID가 있는 경우)
    if analysis_id:
        test_document_generation(analysis_id)
    else:
        # 테스트용 더미 ID로 문서 생성 테스트
        test_document_generation("test-analysis-id")