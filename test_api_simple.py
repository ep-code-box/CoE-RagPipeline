#!/usr/bin/env python3
import requests
import json

# 서버 URL
BASE_URL = "http://localhost:8001"

def test_document_generation():
    """문서 생성 API 테스트"""
    print("=== 문서 생성 API 테스트 ===")
    data = {
        "analysis_id": "test-analysis-id",
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
    except requests.exceptions.Timeout:
        print("Request timed out")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_document_generation()