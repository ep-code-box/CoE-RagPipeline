#!/usr/bin/env python3
import requests
import json

# 서버 URL
BASE_URL = "http://localhost:8001"

def test_document_generation_with_real_id():
    """실제 분석 ID로 문서 생성 API 테스트"""
    print("=== 실제 분석 ID로 문서 생성 API 테스트 ===")
    
    # 실제 존재하는 분석 ID 사용
    analysis_id = "2e63e109-7df4-4bc7-9a15-ecf41c05161d"
    
    data = {
        "analysis_id": analysis_id,
        "document_types": ["development_guide"],
        "language": "korean"
    }
    
    try:
        print(f"Sending request to: {BASE_URL}/api/v1/documents/generate")
        print(f"Request data: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/documents/generate",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print(f"Task ID: {task_id}")
            
            # 작업 상태 확인
            if task_id:
                import time
                time.sleep(2)
                check_task_status(task_id)
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def check_task_status(task_id):
    """작업 상태 확인"""
    print(f"=== 작업 상태 확인: {task_id} ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/documents/status/{task_id}",
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_document_generation_with_real_id()