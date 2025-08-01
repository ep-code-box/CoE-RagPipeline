import json
import logging
from typing import List

logger = logging.getLogger(__name__)


def extract_dependencies(clone_path: str, file_path: str, language: str) -> List[str]:
    """의존성 추출"""
    dependencies = []
    full_path = f"{clone_path}/{file_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if language == 'Python':
            # requirements.txt 파싱
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 버전 정보 제거
                    dep = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
                    dependencies.append(dep.strip())
                    
        elif language == 'JavaScript/Node.js':
            # package.json 파싱 (간단한 버전)
            try:
                data = json.loads(content)
                if 'dependencies' in data:
                    dependencies.extend(data['dependencies'].keys())
                if 'devDependencies' in data:
                    dependencies.extend(data['devDependencies'].keys())
            except json.JSONDecodeError:
                pass
                
    except Exception as e:
        logger.warning(f"Failed to extract dependencies from {file_path}: {e}")
    
    return dependencies


def get_package_manager(filename: str) -> str:
    """패키지 매니저 식별"""
    manager_map = {
        'requirements.txt': 'pip',
        'package.json': 'npm',
        'pom.xml': 'maven',
        'build.gradle': 'gradle',
        'Cargo.toml': 'cargo',
        'go.mod': 'go mod'
    }
    return manager_map.get(filename, 'unknown')