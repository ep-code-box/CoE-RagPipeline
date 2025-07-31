#!/usr/bin/env python3
"""
간단한 Embedding 기능 테스트 스크립트 (서버 독립적)
"""

import os
import sys
from datetime import datetime

# 테스트용 환경 변수 설정
os.environ["OPENAI_API_BASE"] = "https://guest-api.sktax.chat/v1"
os.environ["OPENAI_API_KEY"] = "sktax-XyeKFrq67ZjS4EpsDlrHHXV8it"
os.environ["CHROMA_PERSIST_DIRECTORY"] = "./test_chroma_db"


def test_embedding_service():
    """EmbeddingService 직접 테스트"""
    print("🔍 Testing EmbeddingService...")
    
    try:
        from services.embedding_service import EmbeddingService
        from models.schemas import (
            AnalysisResult, RepositoryAnalysis, GitRepository, 
            CodeMetrics, TechSpec, ASTNode, FileInfo
        )
        
        print("✅ Successfully imported required modules")
        
        # 테스트용 분석 결과 생성
        test_repo = GitRepository(
            url="https://github.com/test/test-repo.git",
            name="test-repo",
            branch="main"
        )
        
        # 테스트용 파일 정보
        test_files = [
            FileInfo(path="main.py", size=1024, language="Python"),
            FileInfo(path="utils.js", size=512, language="JavaScript"),
            FileInfo(path="README.md", size=256, language="Markdown")
        ]
        
        # 테스트용 AST 노드
        test_ast_nodes = [
            ASTNode(
                type="FunctionDef",
                name="main",
                line_start=1,
                line_end=5,
                metadata={"args": ["argc", "argv"], "returns": "int"}
            ),
            ASTNode(
                type="ClassDef", 
                name="TestClass",
                line_start=10,
                line_end=20,
                metadata={"methods": ["__init__", "test_method"]}
            )
        ]
        
        # 테스트용 기술스펙
        test_tech_specs = [
            TechSpec(
                language="Python",
                dependencies=["fastapi", "uvicorn", "pydantic"],
                package_manager="pip"
            ),
            TechSpec(
                language="JavaScript",
                dependencies=["express", "lodash", "axios"],
                package_manager="npm"
            )
        ]
        
        test_repo_analysis = RepositoryAnalysis(
            repository=test_repo,
            clone_path="/tmp/test-repo",
            files=test_files,
            ast_analysis={"main.py": test_ast_nodes},
            tech_specs=test_tech_specs,
            code_metrics=CodeMetrics(
                lines_of_code=1500,
                cyclomatic_complexity=5.2,
                maintainability_index=75.8,
                comment_ratio=0.15
            ),
            documentation_files=["README.md"],
            config_files=["package.json", "requirements.txt"]
        )
        
        test_analysis = AnalysisResult(
            analysis_id="test-embedding-simple-123",
            status="completed",
            created_at=datetime.now(),
            repositories=[test_repo_analysis],
            correlation_analysis=None
        )
        
        print("✅ Created test analysis data")
        
        # EmbeddingService 초기화
        embedding_service = EmbeddingService(chroma_persist_directory="./test_chroma_db")
        print("✅ EmbeddingService initialized successfully")
        
        # 분석 결과 처리 (embedding 및 저장)
        result = embedding_service.process_analysis_result(test_analysis)
        print(f"✅ Embedding processing result: {result}")
        
        if result["status"] == "success":
            print(f"   📊 Documents created: {result['document_count']}")
            print(f"   🆔 Analysis ID: {result['analysis_id']}")
        
        # 검색 테스트
        search_queries = [
            "Python FastAPI",
            "test repository",
            "JavaScript dependencies",
            "main function",
            "README documentation"
        ]
        
        print("\n🔎 Testing search functionality...")
        for query in search_queries:
            search_results = embedding_service.search_similar_documents(query, k=2)
            print(f"   Query: '{query}' -> {len(search_results)} results")
            
            for i, result in enumerate(search_results):
                score = result.get('score', 0)
                doc_type = result['metadata'].get('document_type', 'Unknown')
                content_preview = result['content'][:80].replace('\n', ' ')
                print(f"     {i+1}. [{doc_type}] Score: {score:.4f} - {content_preview}...")
        
        # 통계 정보
        stats = embedding_service.get_collection_stats()
        print(f"\n📈 Collection stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """필요한 모듈들이 제대로 import되는지 테스트"""
    print("🔍 Testing imports...")
    
    try:
        # 기본 라이브러리들
        import langchain
        import langchain_openai
        import langchain_community
        import chromadb
        print("✅ LangChain and ChromaDB imports successful")
        
        # 프로젝트 모듈들
        from services.embedding_service import EmbeddingService
        from models.schemas import AnalysisResult, RepositoryAnalysis
        print("✅ Project module imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 Starting Simple Embedding Tests")
    print("=" * 50)
    
    # 1. Import 테스트
    if not test_imports():
        print("❌ Import tests failed")
        return False
    
    # 2. EmbeddingService 테스트
    if not test_embedding_service():
        print("❌ EmbeddingService tests failed")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All simple embedding tests passed!")
    print("\n📋 Test Summary:")
    print("  ✅ Module imports")
    print("  ✅ EmbeddingService initialization")
    print("  ✅ Document creation and embedding")
    print("  ✅ Vector search functionality")
    print("  ✅ Collection statistics")
    
    print("\n💡 Next steps:")
    print("  1. Start the server: python3 main.py")
    print("  2. Test the API endpoints:")
    print("     - POST /analyze (with embedding)")
    print("     - POST /search")
    print("     - GET /embeddings/stats")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)