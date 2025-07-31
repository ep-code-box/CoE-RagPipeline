#!/usr/bin/env python3
"""
간단한 API 테스트 스크립트
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def test_health():
    """Health check 테스트"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_analyze():
    """Analyze endpoint 테스트"""
    print("\n🔍 Testing analyze endpoint...")
    
    # 테스트용 요청 데이터
    test_data = {
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
            f"{BASE_URL}/analyze",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            return response.json().get("analysis_id")
        return None
    except Exception as e:
        print(f"❌ Analyze test failed: {e}")
        return None

def test_results(analysis_id):
    """Results endpoint 테스트"""
    print(f"\n🔍 Testing results endpoint for analysis_id: {analysis_id}")
    
    # 분석 완료까지 대기 (최대 30초)
    for i in range(6):
        try:
            response = requests.get(f"{BASE_URL}/results/{analysis_id}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Analysis Status: {result.get('status')}")
                
                if result.get('status') == 'completed':
                    print("✅ Analysis completed!")
                    print(f"Repositories analyzed: {len(result.get('repositories', []))}")
                    return True
                elif result.get('status') == 'failed':
                    print(f"❌ Analysis failed: {result.get('error_message')}")
                    return False
                else:
                    print(f"⏳ Analysis in progress... (attempt {i+1}/6)")
                    time.sleep(5)
            else:
                print(f"❌ Results check failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Results test failed: {e}")
            return False
    
    print("⏰ Analysis timeout")
    return False

def test_list_results():
    """Results list endpoint 테스트"""
    print("\n🔍 Testing results list endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/results")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Results list test failed: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Starting API tests...")
    
    # 1. Health check
    if not test_health():
        print("❌ Health check failed. Make sure the server is running.")
        return
    
    # 2. List results (초기 상태)
    test_list_results()
    
    # 3. Start analysis
    analysis_id = test_analyze()
    if not analysis_id:
        print("❌ Analysis start failed.")
        return
    
    # 4. Check results
    if test_results(analysis_id):
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed.")
    
    # 5. List results (최종 상태)
    test_list_results()

if __name__ == "__main__":
    main()