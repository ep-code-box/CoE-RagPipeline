#!/usr/bin/env python3
"""
데이터베이스 연결 및 저장 기능 테스트 스크립트
"""

import sys
import os
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_database, save_analysis_to_db
from models.schemas import (
    AnalysisResult, 
    AnalysisStatus, 
    RepositoryAnalysis, 
    GitRepository, 
    CodeMetrics,
    TechSpec,
    FileInfo
)

def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("🔄 데이터베이스 연결 테스트 시작...")
    
    # 데이터베이스 초기화
    success = init_database()
    if success:
        print("✅ 데이터베이스 연결 및 테이블 생성 성공!")
        return True
    else:
        print("❌ 데이터베이스 연결 실패!")
        return False

def create_test_analysis_result():
    """테스트용 분석 결과 생성"""
    # 테스트 레포지토리 생성
    test_repo = GitRepository(
        url="https://github.com/test/test-repo.git",
        branch="main",
        name="test-repo"
    )
    
    # 테스트 파일 정보
    test_files = [
        FileInfo(path="main.py", size=1024, language="Python", lines_of_code=50),
        FileInfo(path="README.md", size=512, language="Markdown", lines_of_code=20)
    ]
    
    # 테스트 기술스펙
    test_tech_specs = [
        TechSpec(
            language="Python",
            framework="FastAPI",
            dependencies=["fastapi", "uvicorn", "pydantic"],
            version="3.9",
            package_manager="pip"
        )
    ]
    
    # 테스트 코드 메트릭
    test_metrics = CodeMetrics(
        lines_of_code=70,
        comment_ratio=0.2,
        cyclomatic_complexity=5.0,
        maintainability_index=85.0
    )
    
    # 테스트 레포지토리 분석
    test_repo_analysis = RepositoryAnalysis(
        repository=test_repo,
        clone_path="/tmp/test-repo",
        files=test_files,
        tech_specs=test_tech_specs,
        code_metrics=test_metrics,
        documentation_files=["README.md"],
        config_files=[]
    )
    
    # 테스트 분석 결과
    test_analysis = AnalysisResult(
        analysis_id="test-analysis-001",
        status=AnalysisStatus.COMPLETED,
        created_at=datetime.now(),
        completed_at=datetime.now(),
        repositories=[test_repo_analysis],
        correlation_analysis=None
    )
    
    return test_analysis

def test_save_analysis():
    """분석 결과 저장 테스트"""
    print("🔄 분석 결과 저장 테스트 시작...")
    
    # 테스트 데이터 생성
    test_analysis = create_test_analysis_result()
    
    # 데이터베이스에 저장
    success = save_analysis_to_db(test_analysis)
    
    if success:
        print("✅ 분석 결과 저장 성공!")
        print(f"   - Analysis ID: {test_analysis.analysis_id}")
        print(f"   - Git URL: {test_analysis.repositories[0].repository.url}")
        print(f"   - Status: {test_analysis.status}")
        print(f"   - Created: {test_analysis.created_at}")
        return True
    else:
        print("❌ 분석 결과 저장 실패!")
        return False

def main():
    """메인 테스트 함수"""
    print("=" * 50)
    print("🧪 RAG Pipeline 데이터베이스 테스트")
    print("=" * 50)
    
    # 1. 데이터베이스 연결 테스트
    if not test_database_connection():
        print("❌ 데이터베이스 연결 실패로 테스트 중단")
        return False
    
    print()
    
    # 2. 분석 결과 저장 테스트
    if not test_save_analysis():
        print("❌ 분석 결과 저장 실패")
        return False
    
    print()
    print("🎉 모든 테스트 통과!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)