import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from main import app

client = TestClient(app)


class TestSourceSummaryRouter:
    """소스코드 요약 라우터 테스트"""
    
    def test_cache_stats_endpoint(self):
        """캐시 통계 조회 엔드포인트 테스트"""
        with patch('routers.source_summary.source_summary_service') as mock_service:
            mock_service.get_cache_stats.return_value = {
                "memory_cache_size": 5,
                "persistent_cache_files": 10,
                "persistent_cache_size_mb": 2.5,
                "cache_directory": "/test/cache"
            }
            
            response = client.get("/api/v1/source-summary/cache/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["memory_cache_size"] == 5
    
    def test_cache_cleanup_endpoint(self):
        """캐시 정리 엔드포인트 테스트"""
        with patch('routers.source_summary.source_summary_service') as mock_service:
            mock_service.cleanup_cache = MagicMock()
            mock_service.get_cache_stats.return_value = {
                "memory_cache_size": 3,
                "persistent_cache_files": 5,
                "persistent_cache_size_mb": 1.2,
                "cache_directory": "/test/cache"
            }
            
            response = client.post("/api/v1/source-summary/cache/cleanup?max_age_days=7")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "message" in data
            mock_service.cleanup_cache.assert_called_once_with(max_age_days=7)
    
    @pytest.mark.asyncio
    async def test_summarize_file_endpoint(self):
        """단일 파일 요약 엔드포인트 테스트"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def hello_world():
    '''Simple hello world function'''
    print("Hello, World!")
    return "Hello, World!"

if __name__ == "__main__":
    hello_world()
""")
            temp_file_path = f.name
        
        try:
            with patch('routers.source_summary.source_summary_service') as mock_service:
                mock_service.summarize_source_file = AsyncMock(return_value={
                    "file_path": temp_file_path,
                    "file_name": "test.py",
                    "language": "Python",
                    "summary": "Simple Python script with hello world function",
                    "tokens_used": 50
                })
                
                response = client.post(
                    f"/api/v1/source-summary/summarize-file?file_path={temp_file_path}"
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "data" in data
                assert data["data"]["language"] == "Python"
        finally:
            # 임시 파일 정리
            os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_summarize_directory_endpoint(self):
        """디렉토리 요약 엔드포인트 테스트"""
        with patch('routers.source_summary.source_summary_service') as mock_service:
            mock_service.summarize_directory = AsyncMock(return_value={
                "directory_path": "/test/dir",
                "total_files_found": 5,
                "successfully_summarized": 4,
                "failed_files": 1,
                "summaries": {}
            })
            
            response = client.post(
                "/api/v1/source-summary/summarize-directory?directory_path=/test/dir"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["total_files_found"] == 5
    
    @pytest.mark.asyncio
    async def test_summarize_repository_endpoint(self):
        """레포지토리 요약 엔드포인트 테스트"""
        analysis_id = "test-analysis-123"
        
        with patch('routers.source_summary.source_summary_service') as mock_summary_service, \
             patch('routers.source_summary.embedding_service') as mock_embedding_service:
            
            mock_summary_service.summarize_repository_sources = AsyncMock(return_value={
                "analysis_id": analysis_id,
                "summaries": {"test.py": {"summary": "Test file"}},
                "successfully_summarized": 1
            })
            mock_summary_service.get_summary_statistics.return_value = {
                "total_files": 1,
                "total_tokens_used": 100
            }
            mock_embedding_service.embed_source_summaries = AsyncMock(return_value={
                "embedded_count": 1
            })
            
            response = client.post(
                f"/api/v1/source-summary/summarize-repository/{analysis_id}?clone_path=/test/repo"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["summary_result"]["analysis_id"] == analysis_id
    
    def test_get_repository_summaries_endpoint(self):
        """저장된 요약 결과 조회 엔드포인트 테스트"""
        analysis_id = "test-analysis-123"
        
        with patch('routers.source_summary.source_summary_service') as mock_service:
            mock_service.load_repository_summaries.return_value = {
                "analysis_id": analysis_id,
                "summaries": {"test.py": {"summary": "Test file"}}
            }
            mock_service.get_summary_statistics.return_value = {
                "total_files": 1,
                "total_tokens_used": 100
            }
            
            response = client.get(f"/api/v1/source-summary/summaries/{analysis_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["summaries"]["analysis_id"] == analysis_id
    
    def test_get_repository_summaries_not_found(self):
        """존재하지 않는 요약 결과 조회 테스트"""
        analysis_id = "non-existent-analysis"
        
        with patch('routers.source_summary.source_summary_service') as mock_service:
            mock_service.load_repository_summaries.return_value = None
            
            response = client.get(f"/api/v1/source-summary/summaries/{analysis_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "분석 ID" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_search_source_summaries_endpoint(self):
        """소스코드 요약 검색 엔드포인트 테스트"""
        analysis_id = "test-analysis-123"
        query = "authentication function"
        
        with patch('routers.source_summary.embedding_service') as mock_service:
            mock_service.search_source_summaries = AsyncMock(return_value=[
                {
                    "file_path": "auth.py",
                    "summary": "Authentication related functions",
                    "score": 0.95
                }
            ])
            
            response = client.get(
                f"/api/v1/source-summary/search/{analysis_id}?query={query}"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["query"] == query
            assert len(data["data"]["results"]) == 1
            assert data["data"]["results"][0]["file_path"] == "auth.py"