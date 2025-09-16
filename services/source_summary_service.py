import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from config.settings import settings
from utils.token_utils import TokenUtils, TokenChunk

logger = logging.getLogger(__name__)


class SourceSummaryService:
    """소스코드 파일을 LLM을 통해 요약하는 서비스"""
    
    def __init__(self):
        """소스코드 요약 서비스 초기화"""
        if not settings.SKAX_API_KEY:
            raise ValueError("SKAX_API_KEY가 설정되지 않았습니다.")
       
        # SKAX API 클라이언트 초기화
        self.client = OpenAI(
            api_key=settings.SKAX_API_KEY,
            base_url=settings.SKAX_API_BASE
        )
        self.model = settings.SKAX_MODEL_NAME
        # OPEN AI API 클라이언트 초기화
        # self.client = OpenAI(
        #     api_key=settings.OPENAI_API_KEY
        # )
        # self.model = "gpt-4o-mini"
        
        # 지원하는 파일 확장자
        self.supported_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.jsx': 'React JSX',
            '.tsx': 'React TSX',
            '.java': 'Java',
            '.kt': 'Kotlin',
            '.swift': 'Swift',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.scala': 'Scala',
            '.sh': 'Shell Script',
            '.sql': 'SQL',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.json': 'JSON',
            '.xml': 'XML',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.less': 'LESS'
        }
        
        # 요약 결과 캐시 (메모리 기반)
        self.summary_cache = {}
        
        # 영구 캐시 디렉토리
        self.cache_dir = Path("cache/source_summaries")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 성능 최적화 설정 (설정 기반)
        self.max_concurrent_requests = settings.SUMMARY_MAX_CONCURRENT_REQUESTS
        self.retry_attempts = settings.SUMMARY_RETRY_ATTEMPTS
        self.retry_delay = settings.SUMMARY_RETRY_DELAY
        
        # 스레드 풀 실행자
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_requests)
        
    def should_summarize_file(self, file_path: str, file_size: int = None) -> bool:
        """파일이 요약 대상인지 확인"""
        path = Path(file_path)
        
        # 확장자 확인
        if path.suffix.lower() not in self.supported_extensions:
            return False
            
        # 파일 크기 확인 (너무 작은 파일은 제외)
        if file_size and file_size < 100:  # 100바이트 미만
            return False
            
        # 특정 디렉토리 제외
        excluded_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'build', 'dist', 'target', '.gradle', '.idea', '.vscode',
            'coverage', '.nyc_output', 'logs', 'tmp', 'temp'
        }
        
        for part in path.parts:
            if part in excluded_dirs:
                return False
                
        return True
    
    def get_file_hash(self, file_path: str) -> str:
        """파일의 해시값을 계산하여 캐시 키로 사용"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return str(hash(file_path))
    
    def get_persistent_cache_path(self, file_hash: str) -> Path:
        """영구 캐시 파일 경로를 반환"""
        return self.cache_dir / f"{file_hash}.json"
    
    def load_from_persistent_cache(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """영구 캐시에서 요약 결과를 로드"""
        try:
            cache_path = self.get_persistent_cache_path(file_hash)
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    # 캐시 유효성 검사 (7일 이내)
                    cache_time = datetime.fromisoformat(cached_data.get('cached_at', ''))
                    if (datetime.now() - cache_time).days < 7:
                        logger.debug(f"Loaded from persistent cache: {file_hash}")
                        return cached_data['summary']
        except Exception as e:
            logger.debug(f"Failed to load from persistent cache {file_hash}: {e}")
        return None
    
    def save_to_persistent_cache(self, file_hash: str, summary: Dict[str, Any]) -> None:
        """영구 캐시에 요약 결과를 저장"""
        try:
            cache_path = self.get_persistent_cache_path(file_hash)
            cache_data = {
                'summary': summary,
                'cached_at': datetime.now().isoformat()
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved to persistent cache: {file_hash}")
        except Exception as e:
            logger.error(f"Failed to save to persistent cache {file_hash}: {e}")
    
    async def call_llm_with_retry(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """재시도 로직이 포함된 LLM 호출"""
        for attempt in range(self.retry_attempts):
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=0.1
                    )
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # 지수 백오프
                else:
                    logger.error(f"All LLM call attempts failed: {e}")
                    return None
    
    async def summarize_source_file(
        self, 
        file_path: str, 
        max_tokens: int = 1000,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        단일 소스코드 파일을 요약합니다.
        
        Args:
            file_path: 요약할 파일 경로
            max_tokens: 최대 토큰 수
            use_cache: 캐시 사용 여부
            
        Returns:
            요약 결과 딕셔너리 또는 None
        """
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return None
                
            # 파일 정보 수집
            path = Path(file_path)
            file_size = os.path.getsize(file_path)
            
            # 요약 대상 확인
            if not self.should_summarize_file(file_path, file_size):
                logger.debug(f"Skipping file (not suitable for summary): {file_path}")
                return None
            
            # 캐시 확인 (메모리 캐시 -> 영구 캐시 순서)
            file_hash = self.get_file_hash(file_path) if use_cache else None
            cache_key = f"{file_path}:{file_hash}" if file_hash else None
            
            if use_cache and cache_key in self.summary_cache:
                logger.debug(f"Using memory cache for {file_path}")
                return self.summary_cache[cache_key]
            
            # 영구 캐시 확인
            if use_cache and file_hash:
                cached_summary = self.load_from_persistent_cache(file_hash)
                if cached_summary:
                    # 메모리 캐시에도 저장
                    self.summary_cache[cache_key] = cached_summary
                    return cached_summary
            
            # 파일 내용 읽기
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return None
            
            # 파일이 너무 크면 토큰 기준으로 잘라내기
            estimated_tokens = TokenUtils.estimate_tokens(source_code)
            max_file_tokens = settings.SUMMARY_MAX_FILE_TOKENS  # 설정 기반
            
            if estimated_tokens > max_file_tokens:
                # 토큰 기준으로 잘라내기
                target_chars = int(len(source_code) * (max_file_tokens / estimated_tokens))
                source_code = source_code[:target_chars] + "\n... (파일이 토큰 제한으로 잘렸습니다)"
                logger.info(f"File truncated due to token limit: {file_path} ({estimated_tokens} -> ~{max_file_tokens} tokens)")
            
            # 언어 감지
            language = self.supported_extensions.get(path.suffix.lower(), 'Unknown')
            
            # LLM 프롬프트 생성
            system_prompt = self._get_summary_system_prompt(language)
            user_prompt = self._get_summary_user_prompt(file_path, source_code, language)
            
            logger.info(f"Summarizing file: {file_path} ({language})")
            
            # LLM 호출 전 토큰 수 확인
            full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
            prompt_tokens = TokenUtils.estimate_tokens(full_prompt)
            model_limit = TokenUtils.get_model_limit(self.model, reserve_for_completion=max_tokens)
            
            if prompt_tokens > model_limit:
                logger.warning(f"Prompt too large for {file_path}: {prompt_tokens} > {model_limit} tokens")
                # 더 작은 파일 내용으로 재시도
                smaller_target = int(len(source_code) * 0.5)  # 50%로 줄이기
                source_code = source_code[:smaller_target] + "\n... (토큰 제한으로 추가 잘림)"
                user_prompt = self._get_summary_user_prompt(file_path, source_code, language)
                full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
                prompt_tokens = TokenUtils.estimate_tokens(full_prompt)
                logger.info(f"Reduced prompt size: {prompt_tokens} tokens")
            
            # LLM 호출 (재시도 로직 포함)
            summary_content = await self.call_llm_with_retry(full_prompt, max_tokens)
            if not summary_content:
                logger.error(f"Failed to get LLM response for {file_path} after retries")
                return None
            
            # 결과 구성
            result = {
                "file_path": file_path,
                "file_name": path.name,
                "language": language,
                "file_size": file_size,
                "summary": summary_content,
                "summarized_at": datetime.now().isoformat(),
                "model_used": self.model,
                "tokens_used": len(full_prompt.split()) + len(summary_content.split()),  # 토큰 사용량 추정
                "file_hash": file_hash
            }
            
            # 캐시에 저장 (메모리 + 영구)
            if use_cache and cache_key:
                self.summary_cache[cache_key] = result
                # 영구 캐시에도 저장
                if file_hash:
                    self.save_to_persistent_cache(file_hash, result)
            
            logger.info(f"Successfully summarized {file_path}, tokens: {result['tokens_used']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to summarize file {file_path}: {str(e)}")
            return None
    
    async def summarize_directory(
        self, 
        directory_path: str,
        max_files: int = None,
        batch_size: int = None
    ) -> Dict[str, Any]:
        """
        디렉토리 내의 모든 소스코드 파일을 요약합니다.
        
        Args:
            directory_path: 요약할 디렉토리 경로
            max_files: 최대 처리할 파일 수
            batch_size: 배치 처리 크기
            
        Returns:
            요약 결과 딕셔너리
        """
        try:
            if not os.path.exists(directory_path):
                raise ValueError(f"Directory not found: {directory_path}")
            
            # 파라미터 기본값 보정
            if max_files is None:
                max_files = settings.SUMMARY_MAX_FILES_DEFAULT
            if batch_size is None:
                batch_size = settings.SUMMARY_BATCH_SIZE_DEFAULT

            # 요약 대상 파일 수집
            target_files = []
            for root, dirs, files in os.walk(directory_path):
                # 제외할 디렉토리 필터링
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                    'node_modules', '__pycache__', 'venv', '.venv', 'build', 'dist'
                }]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.should_summarize_file(file_path):
                        target_files.append(file_path)
                        
                        if len(target_files) >= max_files:
                            break
                            
                if len(target_files) >= max_files:
                    break
            
            logger.info(f"Found {len(target_files)} files to summarize in {directory_path}")
            
            # 배치 처리로 요약 수행 (동시 처리 최적화)
            summaries = {}
            failed_files = []
            total_tokens = 0
            
            # 세마포어를 사용하여 동시 요청 수 제한
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            async def process_file_with_semaphore(file_path: str):
                async with semaphore:
                    return await self.summarize_source_file(file_path)
            
            for i in range(0, len(target_files), batch_size):
                batch_files = target_files[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(target_files) + batch_size - 1)//batch_size}")
                
                # 배치 내 파일들을 동시에 처리
                batch_tasks = [process_file_with_semaphore(file_path) for file_path in batch_files]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for file_path, result in zip(batch_files, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to summarize {file_path}: {result}")
                        failed_files.append(file_path)
                    elif result:
                        relative_path = os.path.relpath(file_path, directory_path)
                        summaries[relative_path] = result
                        total_tokens += result.get('tokens_used', 0)
                    else:
                        failed_files.append(file_path)
                
                # 배치 간 짧은 대기 (API 레이트 리밋 방지)
                if i + batch_size < len(target_files):
                    await asyncio.sleep(0.5)
            
            # 결과 구성
            result = {
                "directory_path": directory_path,
                "total_files_found": len(target_files),
                "successfully_summarized": len(summaries),
                "failed_files": len(failed_files),
                "total_tokens_used": total_tokens,
                "summaries": summaries,
                "failed_file_paths": failed_files,
                "summarized_at": datetime.now().isoformat()
            }
            
            logger.info(f"Directory summary completed: {len(summaries)}/{len(target_files)} files, "
                       f"total tokens: {total_tokens}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to summarize directory {directory_path}: {str(e)}")
            raise
    
    def _get_summary_system_prompt(self, language: str) -> str:
        """요약을 위한 시스템 프롬프트 생성"""
        return f"""당신은 {language} 코드 분석 전문가입니다. 
소스코드 파일을 분석하여 다음 정보를 포함한 구조화된 요약을 제공해주세요:

1. **파일 목적**: 이 파일이 무엇을 하는지 간단히 설명
2. **주요 구성요소**: 클래스, 함수, 상수 등의 핵심 요소들
3. **핵심 기능**: 주요 비즈니스 로직이나 기능들
4. **의존성**: import/require 되는 주요 라이브러리나 모듈
5. **설계 패턴**: 사용된 디자인 패턴이나 아키텍처 패턴
6. **주목할 점**: 특별한 구현 방식이나 주의사항

JSON 형식으로 응답하지 말고, 마크다운 형식으로 구조화하여 응답해주세요.
개발자가 빠르게 이해할 수 있도록 핵심 내용을 간결하게 정리해주세요."""

    def _get_summary_user_prompt(self, file_path: str, source_code: str, language: str) -> str:
        """요약을 위한 사용자 프롬프트 생성"""
        return f"""다음 {language} 소스코드 파일을 분석하여 요약해주세요:

**파일 경로**: `{file_path}`

**소스코드**:
```{language.lower()}
{source_code}
```

위의 가이드라인에 따라 이 파일의 핵심 내용을 요약해주세요."""

    def save_summaries_to_file(self, summaries: Dict[str, Any], output_path: str) -> bool:
        """요약 결과를 파일로 저장"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Summaries saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save summaries to {output_path}: {e}")
            return False
    
    def load_summaries_from_file(self, input_path: str) -> Optional[Dict[str, Any]]:
        """파일에서 요약 결과를 로드"""
        try:
            if not os.path.exists(input_path):
                return None
                
            with open(input_path, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            
            logger.info(f"Summaries loaded from {input_path}")
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to load summaries from {input_path}: {e}")
            return None
    
    def clear_cache(self):
        """메모리 캐시 클리어"""
        self.summary_cache.clear()
        logger.info("Summary cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        return {
            "cached_files": len(self.summary_cache),
            "cache_size_mb": sum(len(str(v)) for v in self.summary_cache.values()) / (1024 * 1024)
        }
    
    async def summarize_repository_sources(
        self,
        clone_path: str,
        analysis_id: str,
        max_files: int = 100,
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """
        레포지토리의 모든 소스코드를 요약하고 결과를 저장합니다.
        
        Args:
            clone_path: 클론된 레포지토리 경로
            analysis_id: 분석 ID
            max_files: 최대 처리할 파일 수
            batch_size: 배치 처리 크기
            
        Returns:
            요약 결과 딕셔너리
        """
        try:
            logger.info(f"Starting repository source summarization for analysis {analysis_id}")
            
            # 디렉토리 요약 수행
            summary_result = await self.summarize_directory(
                directory_path=clone_path,
                max_files=max_files,
                batch_size=batch_size
            )
            
            # 분석 ID 추가
            summary_result["analysis_id"] = analysis_id
            summary_result["repository_path"] = clone_path
            
            # 요약 결과를 파일로 저장
            output_dir = f"output/summaries/{analysis_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            summary_file_path = os.path.join(output_dir, "source_summaries.json")
            self.save_summaries_to_file(summary_result, summary_file_path)
            
            logger.info(f"Repository source summarization completed for analysis {analysis_id}: "
                       f"{summary_result['successfully_summarized']} files summarized")
            
            return summary_result
            
        except Exception as e:
            logger.error(f"Failed to summarize repository sources for analysis {analysis_id}: {str(e)}")
            raise
    
    def load_repository_summaries(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        저장된 레포지토리 요약 결과를 로드합니다.
        
        Args:
            analysis_id: 분석 ID
            
        Returns:
            요약 결과 딕셔너리 또는 None
        """
        try:
            summary_file_path = f"output/summaries/{analysis_id}/source_summaries.json"
            return self.load_summaries_from_file(summary_file_path)
        except Exception as e:
            logger.error(f"Failed to load repository summaries for analysis {analysis_id}: {str(e)}")
            return None
    
    def get_summary_statistics(self, summaries: Dict[str, Any]) -> Dict[str, Any]:
        """
        요약 결과의 통계 정보를 생성합니다.
        
        Args:
            summaries: 요약 결과 딕셔너리
            
        Returns:
            통계 정보 딕셔너리
        """
        try:
            if not summaries or "summaries" not in summaries:
                return {}
            
            file_summaries = summaries["summaries"]
            
            # 언어별 통계
            language_stats = {}
            total_tokens = 0
            total_files = len(file_summaries)
            
            for file_path, summary in file_summaries.items():
                language = summary.get("language", "Unknown")
                tokens = summary.get("tokens_used", 0)
                
                if language not in language_stats:
                    language_stats[language] = {"count": 0, "tokens": 0}
                
                language_stats[language]["count"] += 1
                language_stats[language]["tokens"] += tokens
                total_tokens += tokens
            
            return {
                "total_files": total_files,
                "total_tokens_used": total_tokens,
                "average_tokens_per_file": total_tokens / total_files if total_files > 0 else 0,
                "language_distribution": language_stats,
                "successfully_summarized": summaries.get("successfully_summarized", 0),
                "failed_files": summaries.get("failed_files", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summary statistics: {str(e)}")
            return {}
    
    def cleanup_cache(self, max_age_days: int = 7) -> None:
        """
        오래된 캐시 파일들을 정리합니다.
        
        Args:
            max_age_days: 캐시 파일 최대 보관 일수
        """
        try:
            current_time = datetime.now()
            cleaned_count = 0
            
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    # 파일 수정 시간 확인
                    file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if (current_time - file_time).days > max_age_days:
                        cache_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean cache file {cache_file}: {e}")
            
            logger.info(f"Cleaned {cleaned_count} old cache files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보를 반환합니다.
        
        Returns:
            캐시 통계 딕셔너리
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "memory_cache_size": len(self.summary_cache),
                "persistent_cache_files": len(cache_files),
                "persistent_cache_size_mb": total_size / (1024 * 1024),
                "cache_directory": str(self.cache_dir)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
