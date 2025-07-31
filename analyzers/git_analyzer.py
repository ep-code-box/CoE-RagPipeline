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
        self.base_clone_dir = base_clone_dir or tempfile.mkdtemp(prefix="rag_pipeline_")
        self.cloned_repos: Dict[str, str] = {}
        
    def __del__(self):
        """소멸자에서 임시 디렉토리 정리"""
        self.cleanup()
    
    def cleanup(self):
        """클론된 레포지토리들 정리"""
        if os.path.exists(self.base_clone_dir):
            try:
                shutil.rmtree(self.base_clone_dir)
                logger.info(f"Cleaned up clone directory: {self.base_clone_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup clone directory: {e}")
    
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
        clone_path = os.path.join(self.base_clone_dir, repo_name)
        
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
            logger.info(f"Successfully cloned repository: {repository.url}")
            
            return clone_path
            
        except GitCommandError as e:
            logger.error(f"Failed to clone repository {repository.url}: {e}")
            raise Exception(f"Git clone failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cloning repository {repository.url}: {e}")
            raise Exception(f"Clone failed: {e}")
    
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
            '.makefile': 'Makefile'
        }
        
        suffix = file_path.suffix.lower()
        if suffix in extension_map:
            return extension_map[suffix]
        
        # 특별한 파일명 처리
        name = file_path.name.lower()
        if name in ['dockerfile', 'makefile', 'rakefile', 'gemfile']:
            return name.capitalize()
        
        return None
    
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