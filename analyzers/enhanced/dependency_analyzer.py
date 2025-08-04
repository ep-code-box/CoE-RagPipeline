"""Dependency analysis tools integration for package and security analysis"""

import os
import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from models.schemas import FileInfo

logger = logging.getLogger(__name__)


@dataclass
class DependencyAnalysisResult:
    """의존성 분석 결과를 담는 데이터 클래스"""
    tool: str
    project_path: str
    dependencies: List[Dict[str, Any]]
    vulnerabilities: List[Dict[str, Any]]
    summary: Dict[str, Any]


class DependencyAnalyzer:
    """의존성 분석 도구들을 통합한 분석기"""
    
    def __init__(self):
        self.available_tools = {}
        self._check_available_tools()
    
    def _check_available_tools(self):
        """사용 가능한 의존성 분석 도구들을 확인"""
        tools_to_check = {
            'pipdeptree': self._check_pipdeptree,
            'pip-audit': self._check_pip_audit
        }
        
        for tool_name, check_func in tools_to_check.items():
            try:
                if check_func():
                    self.available_tools[tool_name] = True
                    logger.info(f"Dependency analysis tool '{tool_name}' is available")
                else:
                    self.available_tools[tool_name] = False
                    logger.warning(f"Dependency analysis tool '{tool_name}' is not available")
            except Exception as e:
                self.available_tools[tool_name] = False
                logger.error(f"Error checking tool '{tool_name}': {e}")
    
    def _check_pipdeptree(self) -> bool:
        """pipdeptree 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['pipdeptree', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_pip_audit(self) -> bool:
        """pip-audit 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['pip-audit', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def analyze_project(self, clone_path: str, files: List[FileInfo]) -> List[DependencyAnalysisResult]:
        """프로젝트의 의존성 분석 수행"""
        results = []
        
        # requirements.txt, setup.py, pyproject.toml 등 의존성 파일 찾기
        dependency_files = self._find_dependency_files(clone_path, files)
        
        if not dependency_files:
            logger.info("No dependency files found for analysis")
            return results
        
        # pipdeptree 분석
        if self.available_tools.get('pipdeptree'):
            pipdeptree_result = self._run_pipdeptree(clone_path, dependency_files)
            if pipdeptree_result:
                results.append(pipdeptree_result)
        
        # pip-audit 분석
        if self.available_tools.get('pip-audit'):
            pip_audit_result = self._run_pip_audit(clone_path, dependency_files)
            if pip_audit_result:
                results.append(pip_audit_result)
        
        return results
    
    def _find_dependency_files(self, clone_path: str, files: List[FileInfo]) -> List[str]:
        """의존성 파일들을 찾기"""
        dependency_files = []
        dependency_patterns = [
            'requirements.txt',
            'requirements-dev.txt',
            'requirements-test.txt',
            'setup.py',
            'setup.cfg',
            'pyproject.toml',
            'Pipfile',
            'poetry.lock',
            'package.json',
            'package-lock.json',
            'yarn.lock',
            'pom.xml',
            'build.gradle',
            'Cargo.toml'
        ]
        
        for file_info in files:
            file_name = os.path.basename(file_info.path)
            if file_name in dependency_patterns:
                full_path = os.path.join(clone_path, file_info.path)
                if os.path.exists(full_path):
                    dependency_files.append(full_path)
        
        return dependency_files
    
    def _run_pipdeptree(self, project_path: str, dependency_files: List[str]) -> Optional[DependencyAnalysisResult]:
        """pipdeptree를 사용한 의존성 트리 분석"""
        try:
            # JSON 형식으로 의존성 트리 출력
            cmd = ['pipdeptree', '--json-tree']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=project_path)
            
            dependencies = []
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    dependencies = data
                except json.JSONDecodeError:
                    logger.error("Failed to parse pipdeptree JSON output")
                    return None
            
            # 플랫 형식으로도 분석
            flat_cmd = ['pipdeptree', '--json']
            flat_result = subprocess.run(flat_cmd, capture_output=True, text=True, timeout=60, cwd=project_path)
            
            flat_dependencies = []
            if flat_result.stdout:
                try:
                    flat_data = json.loads(flat_result.stdout)
                    flat_dependencies = flat_data
                except json.JSONDecodeError:
                    pass
            
            # 요약 정보 생성
            total_packages = len(flat_dependencies)
            top_level_packages = len([dep for dep in dependencies if dep.get('package', {}).get('package_name')])
            
            return DependencyAnalysisResult(
                tool='pipdeptree',
                project_path=project_path,
                dependencies=dependencies,
                vulnerabilities=[],  # pipdeptree는 취약점 분석 안함
                summary={
                    'total_packages': total_packages,
                    'top_level_packages': top_level_packages,
                    'dependency_files': dependency_files,
                    'flat_dependencies': flat_dependencies
                }
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"pipdeptree analysis timed out for {project_path}")
            return None
        except Exception as e:
            logger.error(f"Error running pipdeptree on {project_path}: {e}")
            return None
    
    def _run_pip_audit(self, project_path: str, dependency_files: List[str]) -> Optional[DependencyAnalysisResult]:
        """pip-audit를 사용한 보안 취약점 분석"""
        try:
            # requirements.txt 파일이 있는 경우 해당 파일 기준으로 분석
            requirements_files = [f for f in dependency_files if 'requirements' in os.path.basename(f)]
            
            if requirements_files:
                # requirements.txt 기준 분석
                cmd = ['pip-audit', '--format=json', '--requirement', requirements_files[0]]
            else:
                # 현재 환경 기준 분석
                cmd = ['pip-audit', '--format=json']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=project_path)
            
            vulnerabilities = []
            dependencies = []
            
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    vulnerabilities = data.get('vulnerabilities', [])
                    dependencies = data.get('dependencies', [])
                except json.JSONDecodeError:
                    logger.error("Failed to parse pip-audit JSON output")
                    return None
            
            # 심각도별 분류
            critical_count = len([v for v in vulnerabilities if v.get('severity') == 'critical'])
            high_count = len([v for v in vulnerabilities if v.get('severity') == 'high'])
            medium_count = len([v for v in vulnerabilities if v.get('severity') == 'medium'])
            low_count = len([v for v in vulnerabilities if v.get('severity') == 'low'])
            
            return DependencyAnalysisResult(
                tool='pip-audit',
                project_path=project_path,
                dependencies=dependencies,
                vulnerabilities=vulnerabilities,
                summary={
                    'total_vulnerabilities': len(vulnerabilities),
                    'critical_vulnerabilities': critical_count,
                    'high_vulnerabilities': high_count,
                    'medium_vulnerabilities': medium_count,
                    'low_vulnerabilities': low_count,
                    'total_packages_scanned': len(dependencies),
                    'dependency_files': dependency_files
                }
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"pip-audit analysis timed out for {project_path}")
            return None
        except Exception as e:
            logger.error(f"Error running pip-audit on {project_path}: {e}")
            return None
    
    def analyze_requirements_file(self, requirements_file: str) -> Optional[Dict[str, Any]]:
        """requirements.txt 파일 직접 분석"""
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            dependencies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # 패키지명과 버전 분리
                    if '==' in line:
                        package, version = line.split('==', 1)
                    elif '>=' in line:
                        package, version = line.split('>=', 1)
                    elif '<=' in line:
                        package, version = line.split('<=', 1)
                    elif '>' in line:
                        package, version = line.split('>', 1)
                    elif '<' in line:
                        package, version = line.split('<', 1)
                    else:
                        package = line
                        version = None
                    
                    dependencies.append({
                        'package': package.strip(),
                        'version': version.strip() if version else None,
                        'raw_line': line
                    })
            
            return {
                'file_path': requirements_file,
                'total_dependencies': len(dependencies),
                'dependencies': dependencies
            }
            
        except Exception as e:
            logger.error(f"Error analyzing requirements file {requirements_file}: {e}")
            return None
    
    def get_analysis_summary(self, results: List[DependencyAnalysisResult]) -> Dict[str, Any]:
        """의존성 분석 결과 요약"""
        summary = {
            'total_analyses': len(results),
            'tools_used': [result.tool for result in results],
            'available_tools': self.available_tools,
            'total_dependencies': 0,
            'total_vulnerabilities': 0,
            'vulnerability_breakdown': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'dependency_files_found': []
        }
        
        for result in results:
            if result.tool == 'pipdeptree':
                summary['total_dependencies'] += result.summary.get('total_packages', 0)
                summary['dependency_files_found'].extend(result.summary.get('dependency_files', []))
            
            elif result.tool == 'pip-audit':
                summary['total_vulnerabilities'] += len(result.vulnerabilities)
                summary['vulnerability_breakdown']['critical'] += result.summary.get('critical_vulnerabilities', 0)
                summary['vulnerability_breakdown']['high'] += result.summary.get('high_vulnerabilities', 0)
                summary['vulnerability_breakdown']['medium'] += result.summary.get('medium_vulnerabilities', 0)
                summary['vulnerability_breakdown']['low'] += result.summary.get('low_vulnerabilities', 0)
                summary['dependency_files_found'].extend(result.summary.get('dependency_files', []))
        
        # 중복 제거
        summary['dependency_files_found'] = list(set(summary['dependency_files_found']))
        
        return summary
    
    def generate_security_report(self, results: List[DependencyAnalysisResult]) -> Dict[str, Any]:
        """보안 취약점 리포트 생성"""
        security_report = {
            'scan_date': None,
            'total_vulnerabilities': 0,
            'critical_issues': [],
            'high_issues': [],
            'medium_issues': [],
            'low_issues': [],
            'recommendations': []
        }
        
        for result in results:
            if result.tool == 'pip-audit':
                for vuln in result.vulnerabilities:
                    severity = vuln.get('severity', 'unknown').lower()
                    
                    issue = {
                        'package': vuln.get('package'),
                        'version': vuln.get('version'),
                        'vulnerability_id': vuln.get('id'),
                        'description': vuln.get('description'),
                        'fix_versions': vuln.get('fix_versions', [])
                    }
                    
                    if severity == 'critical':
                        security_report['critical_issues'].append(issue)
                    elif severity == 'high':
                        security_report['high_issues'].append(issue)
                    elif severity == 'medium':
                        security_report['medium_issues'].append(issue)
                    elif severity == 'low':
                        security_report['low_issues'].append(issue)
        
        security_report['total_vulnerabilities'] = (
            len(security_report['critical_issues']) +
            len(security_report['high_issues']) +
            len(security_report['medium_issues']) +
            len(security_report['low_issues'])
        )
        
        # 권장사항 생성
        if security_report['critical_issues']:
            security_report['recommendations'].append(
                "Critical vulnerabilities found! Update packages immediately."
            )
        if security_report['high_issues']:
            security_report['recommendations'].append(
                "High severity vulnerabilities detected. Plan updates soon."
            )
        
        return security_report