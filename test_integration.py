#!/usr/bin/env python3
"""
RAG Pipeline 통합 테스트 - 데이터베이스 저장 기능 포함
"""

import requests
import json
import time
import sys

def test_server_health():
    """서버 상태 확인"""
    try:
        response = requests.get('http://127.0.0.1:8001/health', timeout=5)
        if response.status_code == 200:
            print('✅ 서버가 정상적으로 실행 중입니다')
            return True
        else:
            print(f'❌ 서버 상태 확인 실패: {response.status_code}')
            return False
    except requests.exceptions.ConnectionError:
        print('❌ 서버에 연결할 수 없습니다. 서버를 먼저 시작해주세요.')
        return False
    except Exception as e:
        print(f'❌ 서버 상태 확인 중 오류: {e}')
        return False

def test_analysis_with_db_save():
    """분석 요청 및 데이터베이스 저장 테스트"""
    print("🔄 분석 요청 및 데이터베이스 저장 테스트 시작...")
    
    # 테스트 분석 요청
    test_request = {
        'repositories': [
            {
                'url': 'https://github.com/octocat/Hello-World.git',
                'branch': 'master'
            }
        ],
        'include_ast': False,
        'include_tech_spec': True,
        'include_correlation': False
    }
    
    try:
        # 분석 요청
        response = requests.post('http://127.0.0.1:8001/analyze', 
                               json=test_request, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            analysis_id = result['analysis_id']
            print(f'✅ 분석 요청 성공: {analysis_id}')
            print('📊 데이터베이스 저장 기능이 포함된 분석이 시작되었습니다.')
            
            # 분석 완료 대기 (최대 30초)
            print("⏳ 분석 완료 대기 중...")
            for i in range(30):
                time.sleep(1)
                try:
                    result_response = requests.get(f'http://127.0.0.1:8001/results/{analysis_id}', timeout=5)
                    if result_response.status_code == 200:
                        analysis_result = result_response.json()
                        if analysis_result['status'] == 'completed':
                            print('✅ 분석 완료!')
                            print(f'   - 레포지토리 수: {len(analysis_result["repositories"])}')
                            print(f'   - 상태: {analysis_result["status"]}')
                            print('💾 분석 결과가 데이터베이스에 저장되었습니다.')
                            return True
                        elif analysis_result['status'] == 'failed':
                            print(f'❌ 분석 실패: {analysis_result.get("error_message", "알 수 없는 오류")}')
                            return False
                        else:
                            print(f'   진행 중... ({i+1}/30초)')
                except:
                    print(f'   대기 중... ({i+1}/30초)')
            
            print('⏰ 분석 완료 대기 시간 초과')
            return False
            
        else:
            print(f'❌ 분석 요청 실패: {response.status_code}')
            print(f'   응답: {response.text}')
            return False
            
    except Exception as e:
        print(f'❌ 분석 테스트 실패: {e}')
        return False

def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🧪 RAG Pipeline 통합 테스트 (데이터베이스 저장 포함)")
    print("=" * 60)
    
    # 1. 서버 상태 확인
    if not test_server_health():
        print("❌ 서버 상태 확인 실패로 테스트 중단")
        print("💡 서버를 시작하려면: python main.py")
        return False
    
    print()
    
    # 2. 분석 및 데이터베이스 저장 테스트
    if not test_analysis_with_db_save():
        print("❌ 분석 및 데이터베이스 저장 테스트 실패")
        return False
    
    print()
    print("🎉 모든 통합 테스트 통과!")
    print("📊 RAG Pipeline이 분석 결과를 데이터베이스에 성공적으로 저장하고 있습니다.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)