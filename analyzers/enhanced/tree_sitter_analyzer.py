"""Tree-sitter based AST analyzer for enhanced code parsing"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import tree_sitter
from tree_sitter import Language, Parser

from models.schemas import ASTNode, FileInfo

logger = logging.getLogger(__name__)


class TreeSitterAnalyzer:
    """Tree-sitter를 사용한 고급 AST 분석기"""
    
    def __init__(self):
        self.languages = {}
        self.parsers = {}
        self._initialize_languages()
    
    def _initialize_languages(self):
        """지원하는 언어들을 초기화"""
        try:
            # Tree-sitter 언어 라이브러리들 로드
            import tree_sitter_python
            import tree_sitter_javascript
            import tree_sitter_java
            import tree_sitter_typescript
            
            # 언어별 파서 설정 (PyCapsule을 Language 객체로 변환)
            language_capsules = {
                'Python': tree_sitter_python.language(),
                'JavaScript': tree_sitter_javascript.language(),
                'Java': tree_sitter_java.language(),
                'TypeScript': tree_sitter_typescript.language_typescript(),
                'TSX': tree_sitter_typescript.language_tsx()
            }
            
            self.languages = {}
            # 각 언어별 파서 생성
            for lang_name, language_capsule in language_capsules.items():
                try:
                    # PyCapsule을 Language 객체로 변환
                    language = tree_sitter.Language(language_capsule)
                    self.languages[lang_name] = language
                    
                    # 파서 생성 및 언어 설정
                    parser = Parser()
                    parser.language = language  # set_language 대신 property 사용
                    self.parsers[lang_name] = parser
                except Exception as e:
                    logger.warning(f"Failed to initialize {lang_name} parser: {e}")
                    continue
                
            logger.info(f"Initialized tree-sitter for languages: {list(self.languages.keys())}")
            
        except ImportError as e:
            logger.error(f"Failed to import tree-sitter languages: {e}")
            self.languages = {}
            self.parsers = {}
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter: {e}")
            self.languages = {}
            self.parsers = {}
    
    def is_available(self) -> bool:
        """Tree-sitter가 사용 가능한지 확인"""
        return len(self.languages) > 0
    
    def analyze_files(self, clone_path: str, files: List[FileInfo]) -> Dict[str, List[ASTNode]]:
        """파일들의 Tree-sitter AST 분석 수행"""
        if not self.is_available():
            logger.warning("Tree-sitter is not available, skipping analysis")
            return {}
        
        ast_results = {}
        
        for file_info in files:
            if file_info.language in self.parsers:
                try:
                    file_path = os.path.join(clone_path, file_info.path)
                    ast_nodes = self._analyze_file(file_path, file_info.language)
                    
                    if ast_nodes:
                        ast_results[file_info.path] = ast_nodes
                        logger.info(f"Successfully analyzed {file_info.path} with tree-sitter")
                    
                except Exception as e:
                    logger.error(f"Failed to analyze {file_info.path} with tree-sitter: {e}")
                    continue
        
        return ast_results
    
    def _analyze_file(self, file_path: str, language: str) -> List[ASTNode]:
        """단일 파일의 Tree-sitter AST 분석"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, 'utf8'))
            
            return self._convert_tree_to_nodes(tree.root_node, source_code, language)
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path} with tree-sitter: {e}")
            return []
    
    def _convert_tree_to_nodes(self, node, source_code: str, language: str, parent_name: str = "") -> List[ASTNode]:
        """Tree-sitter 노드를 ASTNode 객체로 변환"""
        nodes = []
        
        # 노드 정보 추출
        node_type = node.type
        node_name = self._get_node_name(node, source_code, language)
        
        # 위치 정보
        start_point = node.start_point
        end_point = node.end_point
        line_start = start_point[0] + 1  # 1-based indexing
        line_end = end_point[0] + 1
        
        # 메타데이터 수집
        metadata = self._get_node_metadata(node, source_code, language)
        metadata['language'] = language
        metadata['tree_sitter'] = True
        
        # 현재 노드 생성
        ast_node = ASTNode(
            type=node_type,
            name=node_name,
            line_start=line_start,
            line_end=line_end,
            metadata=metadata
        )
        
        # 자식 노드들 처리
        for child in node.children:
            child_nodes = self._convert_tree_to_nodes(child, source_code, language, node_name or parent_name)
            ast_node.children.extend(child_nodes)
        
        nodes.append(ast_node)
        return nodes
    
    def _get_node_name(self, node, source_code: str, language: str) -> Optional[str]:
        """노드에서 이름 추출"""
        try:
            # 언어별 이름 추출 로직
            if language == 'Python':
                return self._get_python_node_name(node, source_code)
            elif language in ['JavaScript', 'TypeScript']:
                return self._get_js_node_name(node, source_code)
            elif language == 'Java':
                return self._get_java_node_name(node, source_code)
            
            # 기본적으로 텍스트 내용 반환 (짧은 경우만)
            text = source_code[node.start_byte:node.end_byte]
            if len(text) <= 100 and '\n' not in text:
                return text.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting node name: {e}")
            return None
    
    def _get_python_node_name(self, node, source_code: str) -> Optional[str]:
        """Python 노드 이름 추출"""
        if node.type in ['function_definition', 'class_definition']:
            # 이름 노드 찾기
            for child in node.children:
                if child.type == 'identifier':
                    return source_code[child.start_byte:child.end_byte]
        elif node.type == 'import_statement':
            return source_code[node.start_byte:node.end_byte].strip()
        elif node.type == 'import_from_statement':
            return source_code[node.start_byte:node.end_byte].strip()
        
        return None
    
    def _get_js_node_name(self, node, source_code: str) -> Optional[str]:
        """JavaScript/TypeScript 노드 이름 추출"""
        if node.type in ['function_declaration', 'method_definition', 'class_declaration']:
            # 이름 노드 찾기
            for child in node.children:
                if child.type == 'identifier':
                    return source_code[child.start_byte:child.end_byte]
        elif node.type in ['import_statement', 'export_statement']:
            return source_code[node.start_byte:node.end_byte].strip()
        
        return None
    
    def _get_java_node_name(self, node, source_code: str) -> Optional[str]:
        """Java 노드 이름 추출"""
        if node.type in ['class_declaration', 'method_declaration', 'constructor_declaration']:
            # 이름 노드 찾기
            for child in node.children:
                if child.type == 'identifier':
                    return source_code[child.start_byte:child.end_byte]
        elif node.type == 'import_declaration':
            return source_code[node.start_byte:node.end_byte].strip()
        
        return None
    
    def _get_node_metadata(self, node, source_code: str, language: str) -> Dict[str, Any]:
        """노드 메타데이터 추출"""
        metadata = {
            'node_type': node.type,
            'start_byte': node.start_byte,
            'end_byte': node.end_byte,
            'child_count': len(node.children)
        }
        
        # 언어별 특화 메타데이터
        if language == 'Python':
            metadata.update(self._get_python_metadata(node, source_code))
        elif language in ['JavaScript', 'TypeScript']:
            metadata.update(self._get_js_metadata(node, source_code))
        elif language == 'Java':
            metadata.update(self._get_java_metadata(node, source_code))
        
        return metadata
    
    def _get_python_metadata(self, node, source_code: str) -> Dict[str, Any]:
        """Python 특화 메타데이터"""
        metadata = {}
        
        if node.type == 'function_definition':
            metadata['is_function'] = True
            # 파라미터 정보 추출 시도
            for child in node.children:
                if child.type == 'parameters':
                    metadata['has_parameters'] = True
                    break
        elif node.type == 'class_definition':
            metadata['is_class'] = True
        elif node.type in ['import_statement', 'import_from_statement']:
            metadata['is_import'] = True
        
        return metadata
    
    def _get_js_metadata(self, node, source_code: str) -> Dict[str, Any]:
        """JavaScript/TypeScript 특화 메타데이터"""
        metadata = {}
        
        if node.type == 'function_declaration':
            metadata['is_function'] = True
        elif node.type == 'class_declaration':
            metadata['is_class'] = True
        elif node.type == 'method_definition':
            metadata['is_method'] = True
        elif node.type in ['import_statement', 'export_statement']:
            metadata['is_import_export'] = True
        
        return metadata
    
    def _get_java_metadata(self, node, source_code: str) -> Dict[str, Any]:
        """Java 특화 메타데이터"""
        metadata = {}
        
        if node.type == 'class_declaration':
            metadata['is_class'] = True
        elif node.type == 'method_declaration':
            metadata['is_method'] = True
        elif node.type == 'constructor_declaration':
            metadata['is_constructor'] = True
        elif node.type == 'import_declaration':
            metadata['is_import'] = True
        
        return metadata
    
    def get_ast_summary(self, ast_results: Dict[str, List[ASTNode]]) -> Dict[str, Any]:
        """Tree-sitter AST 분석 결과 요약"""
        summary = {
            'total_files': len(ast_results),
            'languages': {},
            'node_types': {},
            'total_nodes': 0,
            'analyzer': 'tree-sitter'
        }
        
        for file_path, nodes in ast_results.items():
            for node in nodes:
                summary['total_nodes'] += 1
                
                # 언어별 통계
                language = node.metadata.get('language', 'Unknown')
                if language not in summary['languages']:
                    summary['languages'][language] = 0
                summary['languages'][language] += 1
                
                # 노드 타입별 통계
                if node.type not in summary['node_types']:
                    summary['node_types'][node.type] = 0
                summary['node_types'][node.type] += 1
        
        return summary