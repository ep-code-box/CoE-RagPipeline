"""Static analysis tools integration for code quality analysis"""

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
class StaticAnalysisResult:
    """정적 분석 결과를 담는 데이터 클래스"""
    tool: str
    file_path: str
    issues: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    summary: Dict[str, Any]


class StaticAnalyzer:
    """정적 분석 도구들을 통합한 분석기"""
    
    def __init__(self):
        self.available_tools = {}
        self._check_available_tools()
    
    def _check_available_tools(self):
        """사용 가능한 정적 분석 도구들을 확인"""
        tools_to_check = {
            'bandit': self._check_bandit,
            'pylint': self._check_pylint,
            'flake8': self._check_flake8,
            'mypy': self._check_mypy,
            'radon': self._check_radon
        }
        
        for tool_name, check_func in tools_to_check.items():
            try:
                if check_func():
                    self.available_tools[tool_name] = True
                    logger.info(f"Static analysis tool '{tool_name}' is available")
                else:
                    self.available_tools[tool_name] = False
                    logger.warning(f"Static analysis tool '{tool_name}' is not available")
            except Exception as e:
                self.available_tools[tool_name] = False
                logger.error(f"Error checking tool '{tool_name}': {e}")
    
    def _check_bandit(self) -> bool:
        """Bandit 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['bandit', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_pylint(self) -> bool:
        """Pylint 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['pylint', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_flake8(self) -> bool:
        """Flake8 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['flake8', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_mypy(self) -> bool:
        """MyPy 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['mypy', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_radon(self) -> bool:
        """Radon 도구 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['radon', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def analyze_files(self, clone_path: str, files: List[FileInfo]) -> Dict[str, List[StaticAnalysisResult]]:
        """파일들의 정적 분석 수행"""
        results = {}
        
        # Python 파일들만 필터링 (대부분의 도구가 Python 전용)
        python_files = [f for f in files if f.language == 'Python']
        
        if not python_files:
            logger.info("No Python files found for static analysis")
            return results
        
        for file_info in python_files:
            file_path = os.path.join(clone_path, file_info.path)
            file_results = []
            
            # 각 도구별로 분석 수행
            if self.available_tools.get('bandit'):
                bandit_result = self._run_bandit(file_path)
                if bandit_result:
                    file_results.append(bandit_result)
            
            if self.available_tools.get('pylint'):
                pylint_result = self._run_pylint(file_path)
                if pylint_result:
                    file_results.append(pylint_result)
            
            if self.available_tools.get('flake8'):
                flake8_result = self._run_flake8(file_path)
                if flake8_result:
                    file_results.append(flake8_result)
            
            if self.available_tools.get('mypy'):
                mypy_result = self._run_mypy(file_path)
                if mypy_result:
                    file_results.append(mypy_result)
            
            if self.available_tools.get('radon'):
                radon_result = self._run_radon(file_path)
                if radon_result:
                    file_results.append(radon_result)
            
            if file_results:
                results[file_info.path] = file_results
        
        return results
    
    def _run_bandit(self, file_path: str) -> Optional[StaticAnalysisResult]:
        """Bandit 보안 분석 실행"""
        try:
            cmd = ['bandit', '-f', 'json', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Bandit은 이슈가 있으면 exit code 1을 반환
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    issues = data.get('results', [])
                    metrics = data.get('metrics', {})
                    
                    return StaticAnalysisResult(
                        tool='bandit',
                        file_path=file_path,
                        issues=issues,
                        metrics=metrics,
                        summary={
                            'total_issues': len(issues),
                            'high_severity': len([i for i in issues if i.get('issue_severity') == 'HIGH']),
                            'medium_severity': len([i for i in issues if i.get('issue_severity') == 'MEDIUM']),
                            'low_severity': len([i for i in issues if i.get('issue_severity') == 'LOW'])
                        }
                    )
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse bandit output for {file_path}")
            
            return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"Bandit analysis timed out for {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error running bandit on {file_path}: {e}")
            return None
    
    def _run_pylint(self, file_path: str) -> Optional[StaticAnalysisResult]:
        """Pylint 코드 품질 분석 실행"""
        try:
            cmd = ['pylint', '--output-format=json', '--reports=no', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                    
                    # 메시지 타입별 분류
                    error_count = len([i for i in issues if i.get('type') == 'error'])
                    warning_count = len([i for i in issues if i.get('type') == 'warning'])
                    convention_count = len([i for i in issues if i.get('type') == 'convention'])
                    refactor_count = len([i for i in issues if i.get('type') == 'refactor'])
                    
                    return StaticAnalysisResult(
                        tool='pylint',
                        file_path=file_path,
                        issues=issues,
                        metrics={},
                        summary={
                            'total_issues': len(issues),
                            'errors': error_count,
                            'warnings': warning_count,
                            'conventions': convention_count,
                            'refactors': refactor_count
                        }
                    )
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse pylint output for {file_path}")
            
            return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"Pylint analysis timed out for {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error running pylint on {file_path}: {e}")
            return None
    
    def _run_flake8(self, file_path: str) -> Optional[StaticAnalysisResult]:
        """Flake8 스타일 검사 실행"""
        try:
            cmd = ['flake8', '--format=json', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            issues = []
            if result.stdout:
                # Flake8 JSON 출력 파싱
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            issue = json.loads(line)
                            issues.append(issue)
                        except json.JSONDecodeError:
                            continue
            
            return StaticAnalysisResult(
                tool='flake8',
                file_path=file_path,
                issues=issues,
                metrics={},
                summary={
                    'total_issues': len(issues),
                    'style_violations': len(issues)
                }
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Flake8 analysis timed out for {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error running flake8 on {file_path}: {e}")
            return None
    
    def _run_mypy(self, file_path: str) -> Optional[StaticAnalysisResult]:
        """MyPy 타입 검사 실행"""
        try:
            cmd = ['mypy', '--show-error-codes', '--no-error-summary', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            issues = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and ':' in line:
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            issues.append({
                                'file': parts[0],
                                'line': parts[1],
                                'column': parts[2] if parts[2].isdigit() else None,
                                'message': parts[3].strip(),
                                'severity': 'error' if 'error:' in line else 'note'
                            })
            
            return StaticAnalysisResult(
                tool='mypy',
                file_path=file_path,
                issues=issues,
                metrics={},
                summary={
                    'total_issues': len(issues),
                    'type_errors': len([i for i in issues if i.get('severity') == 'error'])
                }
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"MyPy analysis timed out for {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error running mypy on {file_path}: {e}")
            return None
    
    def _run_radon(self, file_path: str) -> Optional[StaticAnalysisResult]:
        """Radon 복잡도 분석 실행"""
        try:
            # 순환 복잡도 분석
            cc_cmd = ['radon', 'cc', '-j', file_path]
            cc_result = subprocess.run(cc_cmd, capture_output=True, text=True, timeout=30)
            
            # 유지보수성 지수 분석
            mi_cmd = ['radon', 'mi', '-j', file_path]
            mi_result = subprocess.run(mi_cmd, capture_output=True, text=True, timeout=30)
            
            # 원시 메트릭 분석
            raw_cmd = ['radon', 'raw', '-j', file_path]
            raw_result = subprocess.run(raw_cmd, capture_output=True, text=True, timeout=30)
            
            metrics = {}
            issues = []
            
            # 순환 복잡도 결과 파싱
            if cc_result.stdout:
                try:
                    cc_data = json.loads(cc_result.stdout)
                    metrics['cyclomatic_complexity'] = cc_data
                    
                    # 높은 복잡도를 이슈로 분류
                    for file_data in cc_data.values():
                        for func_data in file_data:
                            if func_data.get('complexity', 0) > 10:
                                issues.append({
                                    'type': 'high_complexity',
                                    'function': func_data.get('name'),
                                    'complexity': func_data.get('complexity'),
                                    'line': func_data.get('lineno')
                                })
                except json.JSONDecodeError:
                    pass
            
            # 유지보수성 지수 결과 파싱
            if mi_result.stdout:
                try:
                    mi_data = json.loads(mi_result.stdout)
                    metrics['maintainability_index'] = mi_data
                except json.JSONDecodeError:
                    pass
            
            # 원시 메트릭 결과 파싱
            if raw_result.stdout:
                try:
                    raw_data = json.loads(raw_result.stdout)
                    metrics['raw_metrics'] = raw_data
                except json.JSONDecodeError:
                    pass
            
            return StaticAnalysisResult(
                tool='radon',
                file_path=file_path,
                issues=issues,
                metrics=metrics,
                summary={
                    'total_issues': len(issues),
                    'high_complexity_functions': len(issues)
                }
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Radon analysis timed out for {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error running radon on {file_path}: {e}")
            return None
    
    def get_analysis_summary(self, results: Dict[str, List[StaticAnalysisResult]]) -> Dict[str, Any]:
        """정적 분석 결과 요약"""
        summary = {
            'total_files_analyzed': len(results),
            'tools_used': list(self.available_tools.keys()),
            'available_tools': self.available_tools,
            'issues_by_tool': {},
            'total_issues': 0,
            'severity_breakdown': {
                'high': 0,
                'medium': 0,
                'low': 0,
                'errors': 0,
                'warnings': 0
            }
        }
        
        for file_path, file_results in results.items():
            for result in file_results:
                tool = result.tool
                
                if tool not in summary['issues_by_tool']:
                    summary['issues_by_tool'][tool] = 0
                
                issue_count = len(result.issues)
                summary['issues_by_tool'][tool] += issue_count
                summary['total_issues'] += issue_count
                
                # 심각도별 분류 (도구별로 다름)
                if tool == 'bandit':
                    summary['severity_breakdown']['high'] += result.summary.get('high_severity', 0)
                    summary['severity_breakdown']['medium'] += result.summary.get('medium_severity', 0)
                    summary['severity_breakdown']['low'] += result.summary.get('low_severity', 0)
                elif tool == 'pylint':
                    summary['severity_breakdown']['errors'] += result.summary.get('errors', 0)
                    summary['severity_breakdown']['warnings'] += result.summary.get('warnings', 0)
        
        return summary