from typing import List


def find_documentation_files(files: List) -> List[str]:
    """문서 파일 찾기"""
    doc_patterns = ['readme', 'doc', 'docs', '.md', '.rst', '.txt']
    doc_files = []
    
    for file_info in files:
        path_lower = file_info.path.lower()
        if any(pattern in path_lower for pattern in doc_patterns):
            doc_files.append(file_info.path)
    
    return doc_files


def find_config_files(files: List) -> List[str]:
    """설정 파일 찾기"""
    config_patterns = ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']
    config_files = []
    
    for file_info in files:
        path_lower = file_info.path.lower()
        if any(path_lower.endswith(pattern) for pattern in config_patterns):
            config_files.append(file_info.path)
    
    return config_files