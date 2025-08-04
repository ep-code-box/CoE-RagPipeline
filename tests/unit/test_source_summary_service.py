import pytest
import tempfile
import os
import json
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from services.source_summary_service import SourceSummaryService


class TestSourceSummaryService:
    """소스코드 요약 서비스 테스트"""
    
    @pytest.fixture
    def service(self):
        """테스트용 서비스 인스턴스"""
        with patch('services.source_summary_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-api-key"
            return SourceSummaryService()
    
    def test_should_summarize_file_python(self, service):
        """Python 파일 요약 대상 확인 테스트"""
        assert service.should_summarize_file("test.py", 1000) == True
        assert service.should_summarize_file("test.js", 1000) == True
        assert service.should_summarize_file("test.txt", 1000) == False
        assert service.should_summarize_file("test.py", 50) == False  # 너무 작은 파일
    
    def test_should_summarize_file_excluded_dirs(self, service):
        """제외 디렉토리 확인 테스트"""
        assert service.should_summarize_file("node_modules/test.js", 1000) == False
        assert service.should_summarize_file(".git/test.py", 1000) == False
        assert service.should_summarize_file("__pycache__/test.py", 1000) == False
        assert service.should_summarize_file("src/test.py", 1000) == True
    
    def test_get_file_hash(self, service):
        """파일 해시 계산 테스트"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            hash1 = service.get_file_hash(temp_file)
            hash2 = service.get_file_hash(temp_file)
            assert hash1 == hash2  # 같은 파일은 같은 해시
            assert len(hash1) == 32  # MD5 해시 길이
        finally:
            os.unlink(temp_file)
    
    def test_get_persistent_cache_path(self, service):
        """영구 캐시 경로 생성 테스트"""
        file_hash = "abcd1234"
        cache_path = service.get_persistent_cache_path(file_hash)
        assert cache_path.name == f"{file_hash}.json"
        assert cache_path.parent == service.cache_dir
    
    def test_save_and_load_persistent_cache(self, service):
        """영구 캐시 저장/로드 테스트"""
        file_hash = "test_hash_123"
        test_summary = {
            "file_path": "/test/file.py",
            "summary": "Test summary",
            "tokens_used": 100
        }
        
        # 저장
        service.save_to_persistent_cache(file_hash, test_summary)
        
        # 로드
        loaded_summary = service.load_from_persistent_cache(file_hash)
        assert loaded_summary == test_summary
        
        # 캐시 파일 정리
        cache_path = service.get_persistent_cache_path(file_hash)
        if cache_path.exists():
            cache_path.unlink()
    
    @pytest.mark.asyncio
    async def test_call_llm_with_retry_success(self, service):
        """LLM 호출 재시도 로직 성공 테스트"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test summary"
        
        with patch.object(service.client.chat.completions, 'create', return_value=mock_response):
            result = await service.call_llm_with_retry("test prompt")
            assert result == "Test summary"
    
    @pytest.mark.asyncio
    async def test_call_llm_with_retry_failure(self, service):
        """LLM 호출 재시도 로직 실패 테스트"""
        with patch.object(service.client.chat.completions, 'create', side_effect=Exception("API Error")):
            result = await service.call_llm_with_retry("test prompt")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_summarize_source_file_success(self, service):
        """소스파일 요약 성공 테스트"""
        # 임시 Python 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def hello_world():
    '''Simple hello world function'''
    print("Hello, World!")
    return "Hello, World!"
""")
            temp_file = f.name
        
        try:
            with patch.object(service, 'call_llm_with_retry', return_value="Test summary"):
                result = await service.summarize_source_file(temp_file)
                
                assert result is not None
                assert result["file_path"] == temp_file
                assert result["language"] == "Python"
                assert result["summary"] == "Test summary"
                assert "tokens_used" in result
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_summarize_source_file_with_cache(self, service):
        """캐시를 사용한 소스파일 요약 테스트"""
        # 임시 Python 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            temp_file = f.name
        
        try:
            with patch.object(service, 'call_llm_with_retry', return_value="Test summary") as mock_llm:
                # 첫 번째 호출
                result1 = await service.summarize_source_file(temp_file)
                assert mock_llm.call_count == 1
                
                # 두 번째 호출 (캐시 사용)
                result2 = await service.summarize_source_file(temp_file)
                assert mock_llm.call_count == 1  # LLM 호출 횟수 증가하지 않음
                assert result1 == result2
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_summarize_directory(self, service):
        """디렉토리 요약 테스트"""
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # 테스트 파일들 생성
            test_files = [
                ("test1.py", "print('test1')"),
                ("test2.js", "console.log('test2')"),
                ("test3.txt", "not a source file")  # 요약 대상이 아님
            ]
            
            for filename, content in test_files:
                with open(os.path.join(temp_dir, filename), 'w') as f:
                    f.write(content)
            
            with patch.object(service, 'call_llm_with_retry', return_value="Test summary"):
                result = await service.summarize_directory(temp_dir, max_files=10, batch_size=2)
                
                assert result["directory_path"] == temp_dir
                assert result["total_files_found"] == 2  # .py와 .js 파일만
                assert result["successfully_summarized"] == 2
                assert len(result["summaries"]) == 2
    
    def test_get_summary_statistics(self, service):
        """요약 통계 생성 테스트"""
        test_summaries = {
            "summaries": {
                "test1.py": {
                    "language": "Python",
                    "tokens_used": 100
                },
                "test2.js": {
                    "language": "JavaScript", 
                    "tokens_used": 150
                },
                "test3.py": {
                    "language": "Python",
                    "tokens_used": 80
                }
            },
            "successfully_summarized": 3,
            "failed_files": 1
        }
        
        stats = service.get_summary_statistics(test_summaries)
        
        assert stats["total_files"] == 3
        assert stats["total_tokens_used"] == 330
        assert stats["average_tokens_per_file"] == 110
        assert stats["language_distribution"]["Python"]["count"] == 2
        assert stats["language_distribution"]["JavaScript"]["count"] == 1
        assert stats["successfully_summarized"] == 3
        assert stats["failed_files"] == 1
    
    def test_get_cache_stats(self, service):
        """캐시 통계 조회 테스트"""
        # 메모리 캐시에 데이터 추가
        service.summary_cache["test_key"] = {"summary": "test"}
        
        stats = service.get_cache_stats()
        
        assert "memory_cache_size" in stats
        assert "persistent_cache_files" in stats
        assert "persistent_cache_size_mb" in stats
        assert "cache_directory" in stats
        assert stats["memory_cache_size"] == 1
    
    def test_cleanup_cache(self, service):
        """캐시 정리 테스트"""
        # 테스트용 캐시 파일 생성
        test_cache_file = service.cache_dir / "test_cache.json"
        test_cache_file.write_text('{"test": "data"}')
        
        # 캐시 정리 실행
        service.cleanup_cache(max_age_days=0)  # 모든 파일 삭제
        
        # 파일이 삭제되었는지 확인
        assert not test_cache_file.exists()
    
    @pytest.mark.asyncio
    async def test_summarize_repository_sources(self, service):
        """레포지토리 소스코드 요약 테스트"""
        analysis_id = "test-analysis-123"
        
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # 테스트 파일 생성
            with open(os.path.join(temp_dir, "test.py"), 'w') as f:
                f.write("print('hello')")
            
            with patch.object(service, 'call_llm_with_retry', return_value="Test summary"):
                result = await service.summarize_repository_sources(
                    clone_path=temp_dir,
                    analysis_id=analysis_id,
                    max_files=10,
                    batch_size=5
                )
                
                assert result["analysis_id"] == analysis_id
                assert result["repository_path"] == temp_dir
                assert result["successfully_summarized"] == 1
                assert "summaries" in result
    
    def test_load_repository_summaries(self, service):
        """저장된 레포지토리 요약 로드 테스트"""
        analysis_id = "test-analysis-123"
        test_data = {
            "analysis_id": analysis_id,
            "summaries": {"test.py": {"summary": "test"}}
        }
        
        # 테스트 데이터 저장
        output_dir = f"output/summaries/{analysis_id}"
        os.makedirs(output_dir, exist_ok=True)
        summary_file = os.path.join(output_dir, "source_summaries.json")
        
        with open(summary_file, 'w') as f:
            json.dump(test_data, f)
        
        try:
            # 데이터 로드
            loaded_data = service.load_repository_summaries(analysis_id)
            assert loaded_data == test_data
        finally:
            # 테스트 파일 정리
            if os.path.exists(summary_file):
                os.unlink(summary_file)
            if os.path.exists(output_dir):
                os.rmdir(output_dir)