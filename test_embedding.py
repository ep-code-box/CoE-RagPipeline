#!/usr/bin/env python3
"""
Embedding 기능 테스트 스크립트
"""
import os
import sys
import time
import requests
from datetime import datetime

# 테스트용 환경 변수 설정
os.environ["OPENAI_API_BASE"] = "https://guest-api.sktax.chat/v1"
os.environ["OPENAI_API_KEY"] = "sktax-XyeKFrq67ZjS4EpsDlrHHXV8it"
os.environ["CHROMA_PERSIST_DIRECTORY"] = "./test_chroma_db"

BASE_URL = "http://127.0.0.1:8001"


def test_health():
    """서버 상태 확인"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_analysis_with_embedding():
    """분석 및 embedding 테스트"""
    print("\n🔍 Testing analysis with embedding...")
    
    # 분석 요청 데이터
    analysis_data = {
        "repositories": [
            {
                "url": "https://github.com/octocat/Hello-World.git",
                "branch": "master",
                "name": "Hello-World"
            }
        ],
        "include_ast": True,
        "include_tech_spec": True,
        "include_correlation": False
    }
    
    try:
        # 분석 시작
        print("📤 Starting analysis...")
        response = requests.post(f"{BASE_URL}/analyze", json=analysis_data)
        
        if response.status_code != 200:
            print(f"❌ Analysis start failed: {response.status_code}")
            print(response.text)
            return None
        
        result = response.json()
        analysis_id = result["analysis_id"]
        print(f"✅ Analysis started with ID: {analysis_id}")
        
        # 분석 완료 대기
        print("⏳ Waiting for analysis to complete...")
        max_attempts = 30
        for attempt in range(max_attempts):
            response = requests.get(f"{BASE_URL}/results/{analysis_id}")
            if response.status_code == 200:
                result = response.json()
                if result["status"] == "completed":
                    print("✅ Analysis completed successfully")
                    return analysis_id
                elif result["status"] == "failed":
                    print(f"❌ Analysis failed: {result.get('error_message', 'Unknown error')}")
                    return None
                else:
                    print(f"⏳ Analysis status: {result['status']} (attempt {attempt + 1}/{max_attempts})")
            
            time.sleep(2)
        
        print("❌ Analysis timeout")
        return None
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return None


def test_embedding_search():
    """Embedding 검색 테스트"""
    print("\n🔍 Testing embedding search...")
    
    try:
        # 검색 쿼리
        search_queries = [
            "Python code",
            "repository information",
            "dependencies",
            "Hello World"
        ]
        
        for query in search_queries:
            print(f"🔎 Searching for: '{query}'")
            response = requests.post(f"{BASE_URL}/search", params={"query": query, "k": 3})
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Found {len(results)} results")
                
                # 특정 쿼리에 대한 결과 타입 검증
                if query == "dependencies" and results:
                    assert any(r['metadata'].get('document_type') == 'tech_spec' for r in results), \
                        "Query 'dependencies' should return 'tech_spec' documents"
                    print("  ➡️  Verified 'tech_spec' document type for 'dependencies' query.")
                
                for i, result in enumerate(results):
                    print(f"  {i+1}. Score: {result.get('score', 'N/A'):.4f}")
                    print(f"     Type: {result['metadata'].get('document_type', 'Unknown')}")
                    print(f"     Content preview: {result['content'][:100]}...")
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(response.text)
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False


def test_embedding_stats():
    """Embedding 통계 테스트"""
    print("\n🔍 Testing embedding stats...")
    
    try:
        response = requests.get(f"{BASE_URL}/embeddings/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Embedding stats retrieved:")
            print(f"  Total documents: {stats.get('total_documents', 'N/A')}")
            print(f"  Persist directory: {stats.get('persist_directory', 'N/A')}")
            return True
        else:
            print(f"❌ Stats retrieval failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return False


def test_direct_embedding_service():
    """EmbeddingService 직접 테스트"""
    print("\n🔍 Testing EmbeddingService directly...")
    
    try:
        from services.embedding_service import EmbeddingService
        from models.schemas import (
            AnalysisResult, RepositoryAnalysis, GitRepository, 
            CodeMetrics, TechSpec, ASTNode, FileInfo
        )
        
        # 테스트용 분석 결과 생성
        test_repo = GitRepository(
            url="https://github.com/test/direct-test.git",
            name="test-repo",
            branch="main"
        )
        
        test_files = [
            FileInfo(path="main.py", size=1024, language="Python", lines_of_code=50),
            FileInfo(path="README.md", size=512, language="Markdown", lines_of_code=20)
        ]
        
        test_tech_specs = [
            TechSpec(
                language="Python",
                dependencies=["requests", "fastapi"],
                package_manager="pip"
            )
        ]
        
        test_ast_nodes = [
            ASTNode(type="FunctionDef", name="main", line_start=1, line_end=10)
        ]
        
        test_repo_analysis = RepositoryAnalysis(
            repository=test_repo,
            clone_path="/tmp/test",
            files=test_files,
            ast_analysis={"main.py": test_ast_nodes},
            tech_specs=test_tech_specs,
            code_metrics=CodeMetrics(
                lines_of_code=70,
                cyclomatic_complexity=5.0,
                maintainability_index=85.0,
                comment_ratio=0.15
            ),
            documentation_files=["README.md"],
            config_files=["requirements.txt"]
        )
        
        test_analysis = AnalysisResult(
            analysis_id="test-direct-embedding-123",
            status="completed",
            created_at=datetime.now(),
            repositories=[test_repo_analysis],
            correlation_analysis=None
        )
        
        print("✅ Created test analysis data for direct test")
        
        # EmbeddingService 테스트
        embedding_service = EmbeddingService(chroma_persist_directory="./test_chroma_db")
        print("✅ Initialized EmbeddingService for direct test")
        result = embedding_service.process_analysis_result(test_analysis)
        
        print(f"✅ Direct embedding test result: {result}")
        
        # 검색 테스트
        search_results = embedding_service.search_similar_documents("test repository", k=2)
        print(f"✅ Direct search found {len(search_results)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct embedding test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 Starting Embedding Feature Tests")
    print("=" * 50)
    
    # 1. 서버 상태 확인
    if not test_health():
        print("❌ Server is not running. Please start the server first:")
        print("   python main.py")
        return False
    
    # 2. 직접 EmbeddingService 테스트
    if not test_direct_embedding_service():
        print("❌ Direct embedding service test failed")
        return False
    
    # 3. 분석 및 embedding 테스트
    analysis_id = test_analysis_with_embedding()
    if not analysis_id:
        print("❌ Analysis with embedding test failed")
        return False
    
    # 4. Embedding 검색 테스트
    if not test_embedding_search():
        print("❌ Embedding search test failed")
        return False
    
    # 5. Embedding 통계 테스트
    if not test_embedding_stats():
        print("❌ Embedding stats test failed")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All embedding tests passed successfully!")
    print("\n📋 Test Summary:")
    print("  ✅ Server health check")
    print("  ✅ Direct EmbeddingService test")
    print("  ✅ Analysis with embedding")
    print("  ✅ Embedding search")
    print("  ✅ Embedding statistics")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)