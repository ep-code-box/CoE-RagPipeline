import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


def detect_tech_stack(clone_path: str, files: List) -> List[Dict]:
    """
    프로젝트 파일들을 분석하여 기술 스택을 감지합니다.
    
    Args:
        clone_path: 클론된 레포지토리 경로
        files: 분석할 파일 목록 (FileInfo 객체들)
    
    Returns:
        List[Dict]: 감지된 기술 스택 정보 리스트
    """
    tech_stacks = []
    repo_path = Path(clone_path)
    
    # 언어별 파일 수 계산
    language_counts = Counter()
    for file in files:
        if hasattr(file, 'language') and file.language:
            language_counts[file.language] += 1
    
    # 주요 언어들에 대해 기술 스택 감지
    for language, count in language_counts.most_common():
        if language in ['Text', 'Markdown', 'JSON', 'YAML', 'XML']:
            continue
            
        tech_spec = _detect_language_tech_stack(repo_path, language, files)
        if tech_spec:
            tech_stacks.append(tech_spec)
    
    # 기술 스택이 감지되지 않은 경우 기본값 생성
    if not tech_stacks and language_counts:
        primary_language = language_counts.most_common(1)[0][0]
        if primary_language not in ['Text', 'Markdown', 'JSON', 'YAML', 'XML']:
            tech_stacks.append({
                'language': primary_language,
                'framework': None,
                'dependencies': [],
                'version': None,
                'package_manager': None
            })
    
    return tech_stacks


def _detect_language_tech_stack(repo_path: Path, language: str, files: List) -> Optional[Dict]:
    """특정 언어에 대한 기술 스택 감지"""
    
    if language == 'Python':
        return _detect_python_tech_stack(repo_path, files)
    elif language == 'JavaScript':
        return _detect_javascript_tech_stack(repo_path, files)
    elif language == 'TypeScript':
        return _detect_typescript_tech_stack(repo_path, files)
    elif language == 'Java':
        return _detect_java_tech_stack(repo_path, files)
    elif language == 'Lua':
        return _detect_lua_tech_stack(repo_path, files)
    else:
        # 기본 언어 정보만 반환
        return {
            'language': language,
            'framework': None,
            'dependencies': [],
            'version': None,
            'package_manager': None
        }


def _detect_python_tech_stack(repo_path: Path, files: List) -> Dict:
    """Python 프로젝트의 기술 스택 감지"""
    tech_spec = {
        'language': 'Python',
        'framework': None,
        'dependencies': [],
        'version': None,
        'package_manager': None
    }
    
    # 의존성 파일 찾기 및 분석
    dependency_files = ['requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py', 'setup.cfg']
    
    for dep_file in dependency_files:
        file_path = repo_path / dep_file
        if file_path.exists():
            tech_spec['package_manager'] = get_package_manager(dep_file)
            dependencies = extract_dependencies(str(repo_path), dep_file, 'Python')
            tech_spec['dependencies'].extend(dependencies)
            break
    
    # 프레임워크 감지
    framework = _detect_python_framework(tech_spec['dependencies'], files)
    if framework:
        tech_spec['framework'] = framework
    
    # Python 버전 감지
    version = _detect_python_version(repo_path)
    if version:
        tech_spec['version'] = version
    
    return tech_spec


def _detect_javascript_tech_stack(repo_path: Path, files: List) -> Dict:
    """JavaScript 프로젝트의 기술 스택 감지"""
    tech_spec = {
        'language': 'JavaScript',
        'framework': None,
        'dependencies': [],
        'version': None,
        'package_manager': None
    }
    
    # package.json 분석
    package_json_path = repo_path / 'package.json'
    if package_json_path.exists():
        tech_spec['package_manager'] = 'npm'
        dependencies = extract_dependencies(str(repo_path), 'package.json', 'JavaScript')
        tech_spec['dependencies'] = dependencies
        
        # 프레임워크 감지
        framework = _detect_js_framework(dependencies, files)
        if framework:
            tech_spec['framework'] = framework
        
        # Node.js 버전 감지
        version = _detect_node_version(repo_path)
        if version:
            tech_spec['version'] = version
    
    return tech_spec


def _detect_typescript_tech_stack(repo_path: Path, files: List) -> Dict:
    """TypeScript 프로젝트의 기술 스택 감지"""
    tech_spec = {
        'language': 'TypeScript',
        'framework': None,
        'dependencies': [],
        'version': None,
        'package_manager': None
    }
    
    # package.json 분석
    package_json_path = repo_path / 'package.json'
    if package_json_path.exists():
        tech_spec['package_manager'] = 'npm'
        dependencies = extract_dependencies(str(repo_path), 'package.json', 'JavaScript')
        tech_spec['dependencies'] = dependencies
        
        # 프레임워크 감지
        framework = _detect_js_framework(dependencies, files)
        if framework:
            tech_spec['framework'] = framework
    
    # TypeScript 버전 감지
    version = _detect_typescript_version(repo_path)
    if version:
        tech_spec['version'] = version
    
    return tech_spec


def _detect_java_tech_stack(repo_path: Path, files: List) -> Dict:
    """Java 프로젝트의 기술 스택 감지"""
    tech_spec = {
        'language': 'Java',
        'framework': None,
        'dependencies': [],
        'version': None,
        'package_manager': None
    }
    
    # Maven 프로젝트 감지
    pom_xml_path = repo_path / 'pom.xml'
    if pom_xml_path.exists():
        tech_spec['package_manager'] = 'maven'
        dependencies = extract_dependencies(str(repo_path), 'pom.xml', 'Java')
        tech_spec['dependencies'] = dependencies
        
        # Spring 프레임워크 감지
        if any('spring' in dep.lower() for dep in dependencies):
            tech_spec['framework'] = 'Spring'
    
    # Gradle 프로젝트 감지
    gradle_files = ['build.gradle', 'build.gradle.kts']
    for gradle_file in gradle_files:
        gradle_path = repo_path / gradle_file
        if gradle_path.exists():
            tech_spec['package_manager'] = 'gradle'
            dependencies = extract_dependencies(str(repo_path), gradle_file, 'Java')
            tech_spec['dependencies'] = dependencies
            break
    
    return tech_spec


def _detect_lua_tech_stack(repo_path: Path, files: List) -> Dict:
    """Lua 프로젝트의 기술 스택 감지"""
    tech_spec = {
        'language': 'Lua',
        'framework': None,
        'dependencies': [],
        'version': None,
        'package_manager': None
    }
    
    # Love2D 프레임워크 감지
    if _is_love2d_project(repo_path, files):
        tech_spec['framework'] = 'Love2D'
    
    return tech_spec


def _detect_python_framework(dependencies: List[str], files: List) -> Optional[str]:
    """Python 프레임워크 감지"""
    dep_lower = [dep.lower() for dep in dependencies]
    
    if 'django' in dep_lower:
        return 'Django'
    elif 'flask' in dep_lower:
        return 'Flask'
    elif 'fastapi' in dep_lower:
        return 'FastAPI'
    elif 'tornado' in dep_lower:
        return 'Tornado'
    elif 'pyramid' in dep_lower:
        return 'Pyramid'
    elif 'bottle' in dep_lower:
        return 'Bottle'
    
    return None


def _detect_js_framework(dependencies: List[str], files: List) -> Optional[str]:
    """JavaScript/TypeScript 프레임워크 감지"""
    dep_lower = [dep.lower() for dep in dependencies]
    
    if 'react' in dep_lower:
        return 'React'
    elif 'vue' in dep_lower:
        return 'Vue.js'
    elif 'angular' in dep_lower or '@angular/core' in dep_lower:
        return 'Angular'
    elif 'express' in dep_lower:
        return 'Express.js'
    elif 'next' in dep_lower or 'nextjs' in dep_lower:
        return 'Next.js'
    elif 'nuxt' in dep_lower:
        return 'Nuxt.js'
    elif 'svelte' in dep_lower:
        return 'Svelte'
    
    return None


def _detect_python_version(repo_path: Path) -> Optional[str]:
    """Python 버전 감지"""
    # .python-version 파일 확인
    python_version_file = repo_path / '.python-version'
    if python_version_file.exists():
        try:
            with open(python_version_file, 'r') as f:
                return f.read().strip()
        except Exception:
            pass
    
    # pyproject.toml에서 버전 확인
    pyproject_file = repo_path / 'pyproject.toml'
    if pyproject_file.exists():
        try:
            with open(pyproject_file, 'r') as f:
                content = f.read()
                # python_requires 패턴 찾기
                match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except Exception:
            pass
    
    return None


def _detect_node_version(repo_path: Path) -> Optional[str]:
    """Node.js 버전 감지"""
    # .nvmrc 파일 확인
    nvmrc_file = repo_path / '.nvmrc'
    if nvmrc_file.exists():
        try:
            with open(nvmrc_file, 'r') as f:
                return f.read().strip()
        except Exception:
            pass
    
    # package.json에서 engines 확인
    package_json_file = repo_path / 'package.json'
    if package_json_file.exists():
        try:
            with open(package_json_file, 'r') as f:
                data = json.load(f)
                if 'engines' in data and 'node' in data['engines']:
                    return data['engines']['node']
        except Exception:
            pass
    
    return None


def _detect_typescript_version(repo_path: Path) -> Optional[str]:
    """TypeScript 버전 감지"""
    package_json_file = repo_path / 'package.json'
    if package_json_file.exists():
        try:
            with open(package_json_file, 'r') as f:
                data = json.load(f)
                # devDependencies에서 typescript 버전 확인
                if 'devDependencies' in data and 'typescript' in data['devDependencies']:
                    return data['devDependencies']['typescript']
                # dependencies에서 typescript 버전 확인
                if 'dependencies' in data and 'typescript' in data['dependencies']:
                    return data['dependencies']['typescript']
        except Exception:
            pass
    
    return None


def _is_love2d_project(repo_path: Path, files: List) -> bool:
    """Love2D 프로젝트인지 확인"""
    # main.lua 파일 존재 확인
    main_lua_exists = any('main.lua' in getattr(file, 'path', '') for file in files)
    if not main_lua_exists:
        return False
    
    # Love2D 관련 함수 확인
    main_lua_path = repo_path / 'main.lua'
    if main_lua_path.exists():
        try:
            with open(main_lua_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                love2d_functions = [
                    'love.load', 'love.update', 'love.draw',
                    'love.graphics', 'love.audio', 'love.keyboard'
                ]
                if any(func in content for func in love2d_functions):
                    return True
        except Exception:
            pass
    
    return False


def extract_dependencies(clone_path: str, file_path: str, language: str) -> List[str]:
    """의존성 추출"""
    dependencies = []
    full_path = f"{clone_path}/{file_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if language == 'Python':
            if file_path.endswith('requirements.txt'):
                # requirements.txt 파싱
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 버전 정보 제거
                        dep = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].split('[')[0]
                        dependencies.append(dep.strip())
            elif file_path.endswith('pyproject.toml'):
                # pyproject.toml 파싱 (간단한 버전)
                lines = content.split('\n')
                in_dependencies = False
                for line in lines:
                    line = line.strip()
                    if line.startswith('[tool.poetry.dependencies]') or line.startswith('dependencies = ['):
                        in_dependencies = True
                        continue
                    if in_dependencies and line.startswith('['):
                        break
                    if in_dependencies and '=' in line:
                        dep = line.split('=')[0].strip().strip('"').strip("'")
                        if dep and dep != 'python':
                            dependencies.append(dep)
                            
        elif language == 'JavaScript':
            # package.json 파싱
            try:
                data = json.loads(content)
                if 'dependencies' in data:
                    dependencies.extend(data['dependencies'].keys())
                if 'devDependencies' in data:
                    dependencies.extend(data['devDependencies'].keys())
            except json.JSONDecodeError:
                pass
                
        elif language == 'Java':
            if file_path.endswith('pom.xml'):
                # Maven pom.xml 파싱 (간단한 버전)
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(content)
                    for dependency in root.findall('.//{http://maven.apache.org/POM/4.0.0}dependency'):
                        group_id = dependency.find('{http://maven.apache.org/POM/4.0.0}groupId')
                        artifact_id = dependency.find('{http://maven.apache.org/POM/4.0.0}artifactId')
                        if group_id is not None and artifact_id is not None:
                            dependencies.append(f"{group_id.text}:{artifact_id.text}")
                except ET.ParseError:
                    pass
                    
    except Exception as e:
        logger.warning(f"Failed to extract dependencies from {file_path}: {e}")
    
    return dependencies


def get_package_manager(filename: str) -> str:
    """패키지 매니저 식별"""
    manager_map = {
        'requirements.txt': 'pip',
        'Pipfile': 'pipenv',
        'pyproject.toml': 'poetry',
        'setup.py': 'pip',
        'package.json': 'npm',
        'yarn.lock': 'yarn',
        'pnpm-lock.yaml': 'pnpm',
        'pom.xml': 'maven',
        'build.gradle': 'gradle',
        'build.gradle.kts': 'gradle',
        'Cargo.toml': 'cargo',
        'go.mod': 'go mod',
        'composer.json': 'composer',
        'Gemfile': 'bundler'
    }
    return manager_map.get(filename, 'unknown')