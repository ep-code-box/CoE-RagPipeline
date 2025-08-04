import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import git
from git import Repo, GitCommandError
import logging

from models.schemas import GitRepository, FileInfo

logger = logging.getLogger(__name__)


class GitAnalyzer:
    """Git 레포지토리 클론 및 기본 분석을 담당하는 클래스"""
    
    def __init__(self, base_clone_dir: Optional[str] = None):
        # cache/repositories 폴더를 기본 클론 디렉토리로 사용
        if base_clone_dir is None:
            cache_dir = Path("cache/repositories")
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.base_clone_dir = str(cache_dir)
        else:
            self.base_clone_dir = base_clone_dir
        self.cloned_repos: Dict[str, str] = {}
        
    def __del__(self):
        """소멸자에서 임시 디렉토리 정리"""
        self.cleanup()
    
    def cleanup(self):
        """클론된 레포지토리들 정리"""
        # cache/repositories 디렉토리 내의 개별 레포지토리만 삭제
        for repo_url, clone_path in self.cloned_repos.items():
            if os.path.exists(clone_path):
                try:
                    shutil.rmtree(clone_path)
                    logger.info(f"Cleaned up cloned repository: {clone_path}")
                except Exception as e:
                    logger.error(f"Failed to cleanup repository {clone_path}: {e}")
        self.cloned_repos.clear()
    
    def cleanup_specific_repo(self, repository_url: str):
        """특정 레포지토리만 정리"""
        if repository_url in self.cloned_repos:
            clone_path = self.cloned_repos[repository_url]
            if os.path.exists(clone_path):
                try:
                    shutil.rmtree(clone_path)
                    logger.info(f"Cleaned up specific repository: {clone_path}")
                    del self.cloned_repos[repository_url]
                except Exception as e:
                    logger.error(f"Failed to cleanup repository {clone_path}: {e}")
    
    def _get_repo_name(self, url: str) -> str:
        """Git URL에서 레포지토리 이름 추출"""
        parsed = urlparse(str(url))
        path = parsed.path.strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path.split('/')[-1] if '/' in path else path
    
    def clone_repository(self, repository: GitRepository) -> str:
        """Git 레포지토리를 클론하고 경로 반환"""
        repo_name = repository.name or self._get_repo_name(str(repository.url))
        # 타임스탬프를 추가하여 동일한 레포지토리의 중복 클론 방지
        import time
        timestamp = str(int(time.time()))
        clone_path = os.path.join(self.base_clone_dir, f"{repo_name}_{timestamp}")
        
        try:
            # 이미 클론된 경우 기존 디렉토리 제거
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path)
            
            logger.info(f"Cloning repository: {repository.url} to {clone_path}")
            
            # Git 레포지토리 클론
            repo = Repo.clone_from(
                str(repository.url),
                clone_path,
                branch=repository.branch or "main",
                depth=1  # shallow clone for faster operation
            )
            
            self.cloned_repos[str(repository.url)] = clone_path
            logger.info(f"Successfully cloned repository: {repository.url} to cache directory")
            
            return clone_path
            
        except GitCommandError as e:
            logger.error(f"Failed to clone repository {repository.url}: {e}")
            raise Exception(f"Git clone failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cloning repository {repository.url}: {e}")
            raise Exception(f"Clone failed: {e}")
    
    def get_latest_commit_info(self, repository_url: str, branch: str = "main") -> Dict[str, Any]:
        """원격 레포지토리의 최신 commit 정보를 가져옵니다 (클론 없이)"""
        try:
            # 임시 디렉토리에 shallow clone으로 최신 commit 정보만 가져오기
            temp_dir = tempfile.mkdtemp(prefix="commit_check_")
            try:
                repo = Repo.clone_from(
                    repository_url,
                    temp_dir,
                    branch=branch,
                    depth=1  # 최신 commit만 가져오기
                )
                
                # 최신 commit 정보 추출
                latest_commit = repo.head.commit
                commit_info = {
                    "commit_hash": latest_commit.hexsha,
                    "commit_date": latest_commit.committed_datetime.isoformat(),
                    "author": latest_commit.author.name,
                    "message": latest_commit.message.strip(),
                    "branch": branch
                }
                
                logger.info(f"Retrieved latest commit info for {repository_url}: {latest_commit.hexsha[:8]}")
                return commit_info
                
            finally:
                # 임시 디렉토리 정리
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    
        except GitCommandError as e:
            logger.error(f"Failed to get commit info for {repository_url}: {e}")
            raise Exception(f"Failed to get commit info: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting commit info for {repository_url}: {e}")
            raise Exception(f"Failed to get commit info: {e}")
    
    def get_commit_info_from_cloned_repo(self, clone_path: str) -> Dict[str, Any]:
        """클론된 레포지토리에서 commit 정보를 가져옵니다"""
        try:
            repo = Repo(clone_path)
            latest_commit = repo.head.commit
            
            commit_info = {
                "commit_hash": latest_commit.hexsha,
                "commit_date": latest_commit.committed_datetime.isoformat(),
                "author": latest_commit.author.name,
                "message": latest_commit.message.strip(),
                "branch": repo.active_branch.name if repo.active_branch else "unknown"
            }
            
            logger.info(f"Retrieved commit info from cloned repo: {latest_commit.hexsha[:8]}")
            return commit_info
            
        except Exception as e:
            logger.error(f"Failed to get commit info from cloned repo {clone_path}: {e}")
            raise Exception(f"Failed to get commit info from cloned repo: {e}")
    
    def analyze_repository_structure(self, clone_path: str) -> List[FileInfo]:
        """레포지토리 구조 분석 및 파일 정보 수집"""
        files = []
        
        try:
            repo_path = Path(clone_path)
            
            # .git 디렉토리와 일반적인 무시 패턴들
            ignore_patterns = {
                '.git', '__pycache__', '.pytest_cache', 'node_modules',
                '.venv', 'venv', '.env', 'dist', 'build', '.DS_Store',
                '.idea', '.vscode', '*.pyc', '*.pyo', '*.pyd'
            }
            
            for file_path in repo_path.rglob('*'):
                if file_path.is_file():
                    # 무시 패턴 체크
                    relative_path = file_path.relative_to(repo_path)
                    if any(part in ignore_patterns or part.startswith('.') 
                          for part in relative_path.parts):
                        continue
                    
                    # 파일 정보 수집
                    try:
                        file_size = file_path.stat().st_size
                        language = self._detect_language(file_path)
                        lines_of_code = self._count_lines(file_path) if language else None
                        
                        file_info = FileInfo(
                            path=str(relative_path),
                            size=file_size,
                            language=language,
                            lines_of_code=lines_of_code
                        )
                        files.append(file_info)
                        
                    except Exception as e:
                        logger.warning(f"Failed to analyze file {file_path}: {e}")
                        continue
            
            # 프레임워크 감지 수행
            detected_framework = self._detect_framework(clone_path, files)
            if detected_framework:
                logger.info(f"Detected framework: {detected_framework}")
                # 프레임워크 정보를 파일들에 추가 (주요 파일들에만)
                for file_info in files:
                    if file_info.language == 'Lua' and detected_framework == 'Love2D':
                        file_info.framework = detected_framework
            
            logger.info(f"Analyzed {len(files)} files in repository")
            return files
            
        except Exception as e:
            logger.error(f"Failed to analyze repository structure: {e}")
            return []
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """파일 확장자를 기반으로 프로그래밍 언어 감지"""
        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'JavaScript',
            '.tsx': 'TypeScript',
            '.java': 'Java',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.cc': 'C++',
            '.cxx': 'C++',
            '.c': 'C',
            '.h': 'C/C++',
            '.hpp': 'C++',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.r': 'R',
            '.R': 'R',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bash': 'Bash',
            '.zsh': 'Zsh',
            '.ps1': 'PowerShell',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.less': 'Less',
            '.xml': 'XML',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.toml': 'TOML',
            '.ini': 'INI',
            '.cfg': 'Config',
            '.conf': 'Config',
            '.md': 'Markdown',
            '.rst': 'reStructuredText',
            '.txt': 'Text',
            '.dockerfile': 'Dockerfile',
            '.makefile': 'Makefile',
            '.lua': 'Lua'  # Love2D/Lua 지원 추가
        }
        
        suffix = file_path.suffix.lower()
        if suffix in extension_map:
            return extension_map[suffix]
        
        # 특별한 파일명 처리
        name = file_path.name.lower()
        if name in ['dockerfile', 'makefile', 'rakefile', 'gemfile']:
            return name.capitalize()
        
        return None
    
    def _detect_framework(self, clone_path: str, files: List[FileInfo]) -> Optional[str]:
        """프로젝트 구조와 파일을 기반으로 프레임워크 감지"""
        repo_path = Path(clone_path)
        
        # Love2D 프로젝트 감지
        if self._is_love2d_project(repo_path, files):
            return "Love2D"
        
        # 다른 프레임워크 감지 로직 추가 가능
        # Django, Flask, React, Vue.js 등
        
        return None
    
    def _is_love2d_project(self, repo_path: Path, files: List[FileInfo]) -> bool:
        """Love2D 프로젝트인지 확인"""
        # Love2D 프로젝트의 특징적인 파일들
        love2d_indicators = [
            'main.lua',      # Love2D의 메인 엔트리 포인트
            'conf.lua'       # Love2D 설정 파일
        ]
        
        # 필수 파일 확인
        file_paths = [file.path for file in files]
        has_main_lua = any('main.lua' in path for path in file_paths)
        
        if not has_main_lua:
            return False
        
        # Lua 파일의 비율 확인 (Love2D는 주로 Lua로 작성됨)
        lua_files = [file for file in files if file.language == 'Lua']
        total_code_files = [file for file in files if file.language and file.language not in ['Text', 'Markdown', 'JSON', 'YAML']]
        
        if total_code_files:
            lua_ratio = len(lua_files) / len(total_code_files)
            # Lua 파일이 50% 이상이고 main.lua가 있으면 Love2D로 판단
            if lua_ratio >= 0.5:
                return True
        
        # conf.lua가 있으면 Love2D일 가능성이 높음
        has_conf_lua = any('conf.lua' in path for path in file_paths)
        if has_conf_lua:
            return True
        
        # Love2D 관련 함수나 모듈 사용 확인 (main.lua 파일 내용 검사)
        try:
            main_lua_path = None
            for file in files:
                if 'main.lua' in file.path:
                    main_lua_path = repo_path / file.path
                    break
            
            if main_lua_path and main_lua_path.exists():
                with open(main_lua_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    # Love2D 특유의 함수들 확인
                    love2d_functions = [
                        'love.load', 'love.update', 'love.draw',
                        'love.graphics', 'love.audio', 'love.keyboard',
                        'love.mouse', 'love.timer'
                    ]
                    if any(func in content for func in love2d_functions):
                        return True
        except Exception as e:
            logger.warning(f"Failed to check main.lua content: {e}")
        
        return False
    
    def _count_lines(self, file_path: Path) -> Optional[int]:
        """파일의 라인 수 계산 (텍스트 파일만)"""
        try:
            # 바이너리 파일 체크
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\0' in chunk:  # null byte가 있으면 바이너리 파일
                    return None
            
            # 텍스트 파일 라인 수 계산
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
                
        except Exception:
            return None
    
    def find_config_files(self, clone_path: str) -> List[str]:
        """설정 파일들 찾기"""
        config_patterns = [
            'package.json', 'requirements.txt', 'Pipfile', 'poetry.lock',
            'pom.xml', 'build.gradle', 'Cargo.toml', 'go.mod',
            'composer.json', 'Gemfile', 'setup.py', 'setup.cfg',
            'pyproject.toml', 'tox.ini', 'Dockerfile', 'docker-compose.yml',
            '.gitignore', '.env*', 'config.*', '*.config.*'
        ]
        
        config_files = []
        repo_path = Path(clone_path)
        
        for pattern in config_patterns:
            if '*' in pattern:
                files = list(repo_path.rglob(pattern))
            else:
                files = list(repo_path.rglob(pattern))
            
            for file_path in files:
                if file_path.is_file():
                    relative_path = file_path.relative_to(repo_path)
                    config_files.append(str(relative_path))
        
        return config_files
    
    def find_documentation_files(self, clone_path: str) -> List[str]:
        """문서 파일들 찾기"""
        doc_patterns = [
            'README*', 'CHANGELOG*', 'LICENSE*', 'CONTRIBUTING*',
            'docs/**/*', 'doc/**/*', '*.md', '*.rst', '*.txt'
        ]
        
        doc_files = []
        repo_path = Path(clone_path)
        
        for pattern in doc_patterns:
            files = list(repo_path.rglob(pattern))
            
            for file_path in files:
                if file_path.is_file():
                    relative_path = file_path.relative_to(repo_path)
                    doc_files.append(str(relative_path))
        
        return doc_files
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 디렉토리 통계 정보 반환"""
        try:
            cache_path = Path(self.base_clone_dir)
            if not cache_path.exists():
                return {
                    "cache_directory": str(cache_path),
                    "exists": False,
                    "total_repositories": 0,
                    "total_size_mb": 0.0,
                    "repositories": []
                }
            
            repositories = []
            total_size = 0
            
            for repo_dir in cache_path.iterdir():
                if repo_dir.is_dir():
                    repo_size = sum(f.stat().st_size for f in repo_dir.rglob('*') if f.is_file())
                    total_size += repo_size
                    repositories.append({
                        "name": repo_dir.name,
                        "size_mb": round(repo_size / (1024 * 1024), 2),
                        "created_at": repo_dir.stat().st_ctime
                    })
            
            return {
                "cache_directory": str(cache_path),
                "exists": True,
                "total_repositories": len(repositories),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "repositories": repositories
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "cache_directory": str(self.base_clone_dir),
                "exists": False,
                "error": str(e)
            }
    
    def cleanup_old_repositories(self, max_age_hours: int = 24):
        """오래된 레포지토리 정리 (기본 24시간)"""
        try:
            cache_path = Path(self.base_clone_dir)
            if not cache_path.exists():
                return
            
            import time
            current_time = time.time()
            cleaned_count = 0
            
            for repo_dir in cache_path.iterdir():
                if repo_dir.is_dir():
                    # 디렉토리 생성 시간 확인
                    dir_age_hours = (current_time - repo_dir.stat().st_ctime) / 3600
                    if dir_age_hours > max_age_hours:
                        try:
                            shutil.rmtree(repo_dir)
                            logger.info(f"Cleaned up old repository: {repo_dir.name} (age: {dir_age_hours:.1f}h)")
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to clean up old repository {repo_dir}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old repositories (older than {max_age_hours}h)")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old repositories: {e}")
            return 0
    
    def calculate_code_metrics(self, files: List[FileInfo]) -> 'CodeMetrics':
        """파일 목록을 기반으로 코드 메트릭 계산"""
        from models.schemas import CodeMetrics
        
        total_lines = 0
        code_files = 0
        
        # 프로그래밍 언어 파일들만 필터링
        programming_languages = {
            'Python', 'JavaScript', 'TypeScript', 'Java', 'Kotlin', 'Scala',
            'Go', 'Rust', 'C++', 'C', 'C#', 'PHP', 'Ruby', 'Swift', 'R'
        }
        
        for file_info in files:
            if file_info.language in programming_languages and file_info.lines_of_code:
                total_lines += file_info.lines_of_code
                code_files += 1
        
        # 기본 메트릭 계산
        metrics = CodeMetrics(
            lines_of_code=total_lines,
            cyclomatic_complexity=None,  # 추후 구현 가능
            maintainability_index=None,  # 추후 구현 가능
            comment_ratio=None  # 추후 구현 가능
        )
        
        logger.info(f"Calculated code metrics: {total_lines} lines across {code_files} code files")
        return metrics