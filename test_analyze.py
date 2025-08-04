#!/usr/bin/env python3
import requests
import json
import time

# 서버 URL
BASE_URL = "http://localhost:8001"

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
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            analysis_id = result.get("analysis_id")
            print(f"Analysis ID: {analysis_id}")
            return analysis_id
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def check_analysis_status(analysis_id):
    """분석 상태 확인"""
    print(f"=== 분석 상태 확인: {analysis_id} ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/results/{analysis_id}",
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_document_generation(analysis_id):
    """문서 생성 API 테스트"""
    print(f"=== 문서 생성 API 테스트: {analysis_id} ===")
    data = {
        "analysis_id": analysis_id,
        "document_types": ["development_guide"],
        "language": "korean"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/documents/generate",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # 분석 실행
    analysis_id = test_analyze()
    
    if analysis_id:
        # 잠시 대기 후 상태 확인
        print("Waiting for analysis to complete...")
        time.sleep(5)
        
        # 분석 상태 확인
        if check_analysis_status(analysis_id):
            # 문서 생성 테스트
            test_document_generation(analysis_id)
        else:
            print("Analysis not completed yet or failed")
    else:
        print("Failed to start analysis")