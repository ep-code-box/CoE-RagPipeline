import ast
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

from models.schemas import ASTNode, FileInfo

logger = logging.getLogger(__name__)


class ASTAnalyzer:
    """AST(Abstract Syntax Tree) 분석을 담당하는 클래스"""
    
    def __init__(self):
        self.supported_languages = {
            'Python': self._analyze_python_ast,
            'JavaScript': self._analyze_javascript_ast,
            'TypeScript': self._analyze_typescript_ast,
            'Java': self._analyze_java_ast
        }
    
    def analyze_files(self, clone_path: str, files: List[FileInfo]) -> Dict[str, List[ASTNode]]:
        """파일들의 AST 분석 수행"""
        ast_results = {}
        
        for file_info in files:
            if file_info.language in self.supported_languages:
                try:
                    file_path = os.path.join(clone_path, file_info.path)
                    analyzer = self.supported_languages[file_info.language]
                    ast_nodes = analyzer(file_path)
                    
                    if ast_nodes:
                        ast_results[file_info.path] = ast_nodes
                        logger.info(f"Successfully analyzed AST for {file_info.path}")
                    
                except Exception as e:
                    logger.error(f"Failed to analyze AST for {file_info.path}: {e}")
                    continue
        
        return ast_results
    
    def _analyze_python_ast(self, file_path: str) -> List[ASTNode]:
        """Python 파일의 AST 분석"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            # Python AST 파싱
            tree = ast.parse(source_code)
            return self._convert_python_ast_to_nodes(tree)
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in Python file {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error analyzing Python AST for {file_path}: {e}")
            return []
    
    def _convert_python_ast_to_nodes(self, node: ast.AST, parent_name: str = "") -> List[ASTNode]:
        """Python AST 노드를 ASTNode 객체로 변환"""
        nodes = []
        
        node_type = type(node).__name__
        node_name = self._get_python_node_name(node)
        
        # 라인 번호 정보
        line_start = getattr(node, 'lineno', None)
        line_end = getattr(node, 'end_lineno', None)
        
        # 메타데이터 수집
        metadata = self._get_python_node_metadata(node)
        
        # 현재 노드 생성
        ast_node = ASTNode(
            type=node_type,
            name=node_name,
            line_start=line_start,
            line_end=line_end,
            metadata=metadata
        )
        
        # 자식 노드들 처리
        for child in ast.iter_child_nodes(node):
            child_nodes = self._convert_python_ast_to_nodes(child, node_name or parent_name)
            ast_node.children.extend(child_nodes)
        
        nodes.append(ast_node)
        return nodes
    
    def _get_python_node_name(self, node: ast.AST) -> Optional[str]:
        """Python AST 노드에서 이름 추출"""
        if hasattr(node, 'name'):
            return node.name
        elif isinstance(node, ast.FunctionDef):
            return node.name
        elif isinstance(node, ast.ClassDef):
            return node.name
        elif isinstance(node, ast.Import):
            return ', '.join(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = ', '.join(alias.name for alias in node.names)
            return f"from {module} import {names}"
        elif isinstance(node, ast.Assign):
            targets = []
            for target in node.targets:
                if isinstance(target, ast.Name):
                    targets.append(target.id)
                elif isinstance(target, ast.Attribute):
                    targets.append(f"{target.attr}")
            return ', '.join(targets) if targets else None
        return None
    
    def _get_python_node_metadata(self, node: ast.AST) -> Dict[str, Any]:
        """Python AST 노드에서 메타데이터 추출"""
        metadata = {}
        
        if isinstance(node, ast.FunctionDef):
            metadata.update({
                'args': [arg.arg for arg in node.args.args],
                'decorators': [self._ast_to_string(dec) for dec in node.decorator_list],
                'returns': self._ast_to_string(node.returns) if node.returns else None,
                'is_async': False
            })
        elif isinstance(node, ast.AsyncFunctionDef):
            metadata.update({
                'args': [arg.arg for arg in node.args.args],
                'decorators': [self._ast_to_string(dec) for dec in node.decorator_list],
                'returns': self._ast_to_string(node.returns) if node.returns else None,
                'is_async': True
            })
        elif isinstance(node, ast.ClassDef):
            metadata.update({
                'bases': [self._ast_to_string(base) for base in node.bases],
                'decorators': [self._ast_to_string(dec) for dec in node.decorator_list],
                'methods': []
            })
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            metadata['import_type'] = 'import' if isinstance(node, ast.Import) else 'from_import'
        
        return metadata
    
    def _ast_to_string(self, node: ast.AST) -> str:
        """AST 노드를 문자열로 변환"""
        try:
            return ast.unparse(node)
        except:
            return str(node)
    
    def _analyze_javascript_ast(self, file_path: str) -> List[ASTNode]:
        """JavaScript 파일의 AST 분석 (기본 구현)"""
        # 실제 구현에서는 tree-sitter나 다른 JavaScript 파서를 사용
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 간단한 패턴 매칭으로 기본 구조 추출
            nodes = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # 함수 선언 감지
                if line.startswith('function ') or 'function(' in line:
                    func_name = self._extract_js_function_name(line)
                    if func_name:
                        nodes.append(ASTNode(
                            type='FunctionDeclaration',
                            name=func_name,
                            line_start=i,
                            metadata={'language': 'JavaScript'}
                        ))
                
                # 클래스 선언 감지
                elif line.startswith('class '):
                    class_name = line.split()[1].split('(')[0].split('{')[0]
                    nodes.append(ASTNode(
                        type='ClassDeclaration',
                        name=class_name,
                        line_start=i,
                        metadata={'language': 'JavaScript'}
                    ))
                
                # import/export 감지
                elif line.startswith('import ') or line.startswith('export '):
                    nodes.append(ASTNode(
                        type='ImportDeclaration' if line.startswith('import') else 'ExportDeclaration',
                        name=line,
                        line_start=i,
                        metadata={'language': 'JavaScript'}
                    ))
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error analyzing JavaScript AST for {file_path}: {e}")
            return []
    
    def _extract_js_function_name(self, line: str) -> Optional[str]:
        """JavaScript 함수 이름 추출"""
        try:
            if 'function ' in line:
                parts = line.split('function ')
                if len(parts) > 1:
                    name_part = parts[1].split('(')[0].strip()
                    return name_part if name_part else None
            return None
        except:
            return None
    
    def _analyze_typescript_ast(self, file_path: str) -> List[ASTNode]:
        """TypeScript 파일의 AST 분석 (JavaScript와 유사하게 처리)"""
        return self._analyze_javascript_ast(file_path)
    
    def _analyze_java_ast(self, file_path: str) -> List[ASTNode]:
        """Java 파일의 AST 분석 (기본 구현)"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            nodes = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # 클래스 선언 감지
                if line.startswith('public class ') or line.startswith('class '):
                    class_name = self._extract_java_class_name(line)
                    if class_name:
                        nodes.append(ASTNode(
                            type='ClassDeclaration',
                            name=class_name,
                            line_start=i,
                            metadata={'language': 'Java'}
                        ))
                
                # 메소드 선언 감지
                elif ('public ' in line or 'private ' in line or 'protected ' in line) and '(' in line and ')' in line:
                    method_name = self._extract_java_method_name(line)
                    if method_name:
                        nodes.append(ASTNode(
                            type='MethodDeclaration',
                            name=method_name,
                            line_start=i,
                            metadata={'language': 'Java'}
                        ))
                
                # import 감지
                elif line.startswith('import '):
                    nodes.append(ASTNode(
                        type='ImportDeclaration',
                        name=line,
                        line_start=i,
                        metadata={'language': 'Java'}
                    ))
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error analyzing Java AST for {file_path}: {e}")
            return []
    
    def _extract_java_class_name(self, line: str) -> Optional[str]:
        """Java 클래스 이름 추출"""
        try:
            if 'class ' in line:
                parts = line.split('class ')
                if len(parts) > 1:
                    name_part = parts[1].split()[0].split('{')[0].split('extends')[0].split('implements')[0].strip()
                    return name_part if name_part else None
            return None
        except:
            return None
    
    def _extract_java_method_name(self, line: str) -> Optional[str]:
        """Java 메소드 이름 추출"""
        try:
            # 간단한 패턴 매칭으로 메소드 이름 추출
            if '(' in line and ')' in line:
                before_paren = line.split('(')[0]
                parts = before_paren.split()
                if len(parts) >= 2:
                    return parts[-1]  # 마지막 부분이 메소드 이름
            return None
        except:
            return None
    
    def get_ast_summary(self, ast_results: Dict[str, List[ASTNode]]) -> Dict[str, Any]:
        """AST 분석 결과 요약"""
        summary = {
            'total_files': len(ast_results),
            'languages': {},
            'node_types': {},
            'total_nodes': 0
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