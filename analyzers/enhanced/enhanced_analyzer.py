"""Enhanced analyzer that integrates tree-sitter, static analysis, and dependency analysis"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from models.schemas import FileInfo
from .tree_sitter_analyzer import TreeSitterAnalyzer
from .static_analyzer import StaticAnalyzer, StaticAnalysisResult
from .dependency_analyzer import DependencyAnalyzer, DependencyAnalysisResult

logger = logging.getLogger(__name__)


class EnhancedAnalyzer:
    """통합 분석기 - Tree-sitter, 정적 분석, 의존성 분석을 모두 수행"""
    
    def __init__(self):
        self.tree_sitter_analyzer = TreeSitterAnalyzer()
        self.static_analyzer = StaticAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
        
        # 분석기 가용성 확인
        self.capabilities = {
            'tree_sitter': self.tree_sitter_analyzer.is_available(),
            'static_analysis': any(self.static_analyzer.available_tools.values()),
            'dependency_analysis': any(self.dependency_analyzer.available_tools.values())
        }
        
        logger.info(f"Enhanced analyzer initialized with capabilities: {self.capabilities}")
    
    def analyze_repository(self, clone_path: str, files: List[FileInfo], 
                          include_tree_sitter: bool = True,
                          include_static_analysis: bool = True,
                          include_dependency_analysis: bool = True) -> Dict[str, Any]:
        """레포지토리 전체 분석 수행"""
        
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'clone_path': clone_path,
            'total_files': len(files),
            'capabilities_used': {},
            'tree_sitter_results': {},
            'static_analysis_results': {},
            'dependency_analysis_results': {},
            'summary': {}
        }
        
        # Tree-sitter AST 분석
        if include_tree_sitter and self.capabilities['tree_sitter']:
            try:
                logger.info("Starting tree-sitter AST analysis...")
                tree_sitter_results = self.tree_sitter_analyzer.analyze_files(clone_path, files)
                analysis_results['tree_sitter_results'] = tree_sitter_results
                analysis_results['capabilities_used']['tree_sitter'] = True
                
                # Tree-sitter 요약 생성
                if tree_sitter_results:
                    tree_sitter_summary = self.tree_sitter_analyzer.get_ast_summary(tree_sitter_results)
                    analysis_results['summary']['tree_sitter'] = tree_sitter_summary
                    logger.info(f"Tree-sitter analysis completed: {tree_sitter_summary.get('total_nodes', 0)} nodes analyzed")
                
            except Exception as e:
                logger.error(f"Tree-sitter analysis failed: {e}")
                analysis_results['capabilities_used']['tree_sitter'] = False
        else:
            analysis_results['capabilities_used']['tree_sitter'] = False
            if include_tree_sitter:
                logger.warning("Tree-sitter analysis requested but not available")
        
        # 정적 분석
        if include_static_analysis and self.capabilities['static_analysis']:
            try:
                logger.info("Starting static analysis...")
                static_results = self.static_analyzer.analyze_files(clone_path, files)
                analysis_results['static_analysis_results'] = self._serialize_static_results(static_results)
                analysis_results['capabilities_used']['static_analysis'] = True
                
                # 정적 분석 요약 생성
                if static_results:
                    static_summary = self.static_analyzer.get_analysis_summary(static_results)
                    analysis_results['summary']['static_analysis'] = static_summary
                    logger.info(f"Static analysis completed: {static_summary.get('total_issues', 0)} issues found")
                
            except Exception as e:
                logger.error(f"Static analysis failed: {e}")
                analysis_results['capabilities_used']['static_analysis'] = False
        else:
            analysis_results['capabilities_used']['static_analysis'] = False
            if include_static_analysis:
                logger.warning("Static analysis requested but not available")
        
        # 의존성 분석
        if include_dependency_analysis and self.capabilities['dependency_analysis']:
            try:
                logger.info("Starting dependency analysis...")
                dependency_results = self.dependency_analyzer.analyze_project(clone_path, files)
                analysis_results['dependency_analysis_results'] = self._serialize_dependency_results(dependency_results)
                analysis_results['capabilities_used']['dependency_analysis'] = True
                
                # 의존성 분석 요약 생성
                if dependency_results:
                    dependency_summary = self.dependency_analyzer.get_analysis_summary(dependency_results)
                    analysis_results['summary']['dependency_analysis'] = dependency_summary
                    
                    # 보안 리포트 생성
                    security_report = self.dependency_analyzer.generate_security_report(dependency_results)
                    analysis_results['summary']['security_report'] = security_report
                    
                    logger.info(f"Dependency analysis completed: {dependency_summary.get('total_dependencies', 0)} dependencies, {dependency_summary.get('total_vulnerabilities', 0)} vulnerabilities")
                
            except Exception as e:
                logger.error(f"Dependency analysis failed: {e}")
                analysis_results['capabilities_used']['dependency_analysis'] = False
        else:
            analysis_results['capabilities_used']['dependency_analysis'] = False
            if include_dependency_analysis:
                logger.warning("Dependency analysis requested but not available")
        
        # 전체 요약 생성
        analysis_results['summary']['overall'] = self._generate_overall_summary(analysis_results)
        
        return analysis_results
    
    def _serialize_static_results(self, results: Dict[str, List[StaticAnalysisResult]]) -> Dict[str, Any]:
        """정적 분석 결과를 직렬화 가능한 형태로 변환"""
        serialized = {}
        
        for file_path, file_results in results.items():
            serialized[file_path] = []
            for result in file_results:
                serialized[file_path].append({
                    'tool': result.tool,
                    'file_path': result.file_path,
                    'issues': result.issues,
                    'metrics': result.metrics,
                    'summary': result.summary
                })
        
        return serialized
    
    def _serialize_dependency_results(self, results: List[DependencyAnalysisResult]) -> List[Dict[str, Any]]:
        """의존성 분석 결과를 직렬화 가능한 형태로 변환"""
        serialized = []
        
        for result in results:
            serialized.append({
                'tool': result.tool,
                'project_path': result.project_path,
                'dependencies': result.dependencies,
                'vulnerabilities': result.vulnerabilities,
                'summary': result.summary
            })
        
        return serialized
    
    def _generate_overall_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """전체 분석 결과 요약 생성"""
        overall_summary = {
            'analysis_timestamp': analysis_results['timestamp'],
            'total_files_analyzed': analysis_results['total_files'],
            'capabilities_used': analysis_results['capabilities_used'],
            'analysis_coverage': {}
        }
        
        # Tree-sitter 분석 커버리지
        if analysis_results['capabilities_used'].get('tree_sitter'):
            tree_sitter_files = len(analysis_results['tree_sitter_results'])
            overall_summary['analysis_coverage']['tree_sitter'] = {
                'files_analyzed': tree_sitter_files,
                'coverage_percentage': (tree_sitter_files / analysis_results['total_files']) * 100 if analysis_results['total_files'] > 0 else 0
            }
        
        # 정적 분석 커버리지
        if analysis_results['capabilities_used'].get('static_analysis'):
            static_files = len(analysis_results['static_analysis_results'])
            overall_summary['analysis_coverage']['static_analysis'] = {
                'files_analyzed': static_files,
                'coverage_percentage': (static_files / analysis_results['total_files']) * 100 if analysis_results['total_files'] > 0 else 0
            }
        
        # 의존성 분석 결과
        if analysis_results['capabilities_used'].get('dependency_analysis'):
            dependency_count = len(analysis_results['dependency_analysis_results'])
            overall_summary['analysis_coverage']['dependency_analysis'] = {
                'analyses_performed': dependency_count
            }
        
        # 주요 지표 집계
        overall_summary['key_metrics'] = {}
        
        # Tree-sitter 지표
        if 'tree_sitter' in analysis_results['summary']:
            ts_summary = analysis_results['summary']['tree_sitter']
            overall_summary['key_metrics']['total_ast_nodes'] = ts_summary.get('total_nodes', 0)
            overall_summary['key_metrics']['languages_detected'] = list(ts_summary.get('languages', {}).keys())
        
        # 정적 분석 지표
        if 'static_analysis' in analysis_results['summary']:
            static_summary = analysis_results['summary']['static_analysis']
            overall_summary['key_metrics']['total_code_issues'] = static_summary.get('total_issues', 0)
            overall_summary['key_metrics']['tools_used'] = static_summary.get('tools_used', [])
        
        # 의존성 분석 지표
        if 'dependency_analysis' in analysis_results['summary']:
            dep_summary = analysis_results['summary']['dependency_analysis']
            overall_summary['key_metrics']['total_dependencies'] = dep_summary.get('total_dependencies', 0)
            overall_summary['key_metrics']['total_vulnerabilities'] = dep_summary.get('total_vulnerabilities', 0)
        
        # 보안 리포트 요약
        if 'security_report' in analysis_results['summary']:
            security = analysis_results['summary']['security_report']
            overall_summary['key_metrics']['critical_vulnerabilities'] = len(security.get('critical_issues', []))
            overall_summary['key_metrics']['high_vulnerabilities'] = len(security.get('high_issues', []))
        
        return overall_summary
    
    def generate_comprehensive_report(self, analysis_results: Dict[str, Any]) -> str:
        """종합 분석 리포트를 마크다운 형식으로 생성"""
        
        report_lines = []
        report_lines.append("# 🔍 Enhanced Code Analysis Report")
        report_lines.append("")
        report_lines.append(f"**Analysis Date:** {analysis_results['timestamp']}")
        report_lines.append(f"**Repository Path:** {analysis_results['clone_path']}")
        report_lines.append("")
        
        # 전체 요약
        overall = analysis_results['summary'].get('overall', {})
        report_lines.append("## 📊 Overall Summary")
        report_lines.append("")
        report_lines.append(f"- **Total Files:** {overall.get('total_files_analyzed', 0)}")
        
        # 사용된 분석 도구
        capabilities = overall.get('capabilities_used', {})
        enabled_tools = [tool for tool, enabled in capabilities.items() if enabled]
        report_lines.append(f"- **Analysis Tools Used:** {', '.join(enabled_tools)}")
        report_lines.append("")
        
        # 주요 지표
        metrics = overall.get('key_metrics', {})
        if metrics:
            report_lines.append("### 🎯 Key Metrics")
            report_lines.append("")
            
            if 'total_ast_nodes' in metrics:
                report_lines.append(f"- **AST Nodes Analyzed:** {metrics['total_ast_nodes']}")
            
            if 'total_code_issues' in metrics:
                report_lines.append(f"- **Code Issues Found:** {metrics['total_code_issues']}")
            
            if 'total_dependencies' in metrics:
                report_lines.append(f"- **Dependencies:** {metrics['total_dependencies']}")
            
            if 'total_vulnerabilities' in metrics:
                report_lines.append(f"- **Security Vulnerabilities:** {metrics['total_vulnerabilities']}")
                
                if 'critical_vulnerabilities' in metrics:
                    report_lines.append(f"  - Critical: {metrics['critical_vulnerabilities']}")
                if 'high_vulnerabilities' in metrics:
                    report_lines.append(f"  - High: {metrics['high_vulnerabilities']}")
            
            report_lines.append("")
        
        # Tree-sitter 분석 결과
        if 'tree_sitter' in analysis_results['summary']:
            ts_summary = analysis_results['summary']['tree_sitter']
            report_lines.append("## 🌳 AST Analysis (Tree-sitter)")
            report_lines.append("")
            report_lines.append(f"- **Files Analyzed:** {ts_summary.get('total_files', 0)}")
            report_lines.append(f"- **Total Nodes:** {ts_summary.get('total_nodes', 0)}")
            
            languages = ts_summary.get('languages', {})
            if languages:
                report_lines.append("- **Languages:**")
                for lang, count in languages.items():
                    report_lines.append(f"  - {lang}: {count} nodes")
            
            report_lines.append("")
        
        # 정적 분석 결과
        if 'static_analysis' in analysis_results['summary']:
            static_summary = analysis_results['summary']['static_analysis']
            report_lines.append("## 🔍 Static Analysis")
            report_lines.append("")
            report_lines.append(f"- **Files Analyzed:** {static_summary.get('total_files_analyzed', 0)}")
            report_lines.append(f"- **Total Issues:** {static_summary.get('total_issues', 0)}")
            
            tools_used = static_summary.get('tools_used', [])
            if tools_used:
                report_lines.append(f"- **Tools Used:** {', '.join(tools_used)}")
            
            severity = static_summary.get('severity_breakdown', {})
            if severity:
                report_lines.append("- **Issue Breakdown:**")
                for level, count in severity.items():
                    if count > 0:
                        report_lines.append(f"  - {level.title()}: {count}")
            
            report_lines.append("")
        
        # 의존성 분석 결과
        if 'dependency_analysis' in analysis_results['summary']:
            dep_summary = analysis_results['summary']['dependency_analysis']
            report_lines.append("## 📦 Dependency Analysis")
            report_lines.append("")
            report_lines.append(f"- **Total Dependencies:** {dep_summary.get('total_dependencies', 0)}")
            report_lines.append(f"- **Vulnerabilities Found:** {dep_summary.get('total_vulnerabilities', 0)}")
            
            vuln_breakdown = dep_summary.get('vulnerability_breakdown', {})
            if any(vuln_breakdown.values()):
                report_lines.append("- **Vulnerability Breakdown:**")
                for level, count in vuln_breakdown.items():
                    if count > 0:
                        report_lines.append(f"  - {level.title()}: {count}")
            
            report_lines.append("")
        
        # 보안 리포트
        if 'security_report' in analysis_results['summary']:
            security = analysis_results['summary']['security_report']
            report_lines.append("## 🛡️ Security Report")
            report_lines.append("")
            
            critical_issues = security.get('critical_issues', [])
            if critical_issues:
                report_lines.append("### ⚠️ Critical Issues")
                for issue in critical_issues[:5]:  # 상위 5개만 표시
                    report_lines.append(f"- **{issue.get('package')}** ({issue.get('version')}): {issue.get('vulnerability_id')}")
                report_lines.append("")
            
            recommendations = security.get('recommendations', [])
            if recommendations:
                report_lines.append("### 💡 Recommendations")
                for rec in recommendations:
                    report_lines.append(f"- {rec}")
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def get_capabilities_status(self) -> Dict[str, Any]:
        """분석기 기능 상태 반환"""
        return {
            'tree_sitter': {
                'available': self.capabilities['tree_sitter'],
                'supported_languages': list(self.tree_sitter_analyzer.languages.keys()) if self.capabilities['tree_sitter'] else []
            },
            'static_analysis': {
                'available': self.capabilities['static_analysis'],
                'available_tools': self.static_analyzer.available_tools
            },
            'dependency_analysis': {
                'available': self.capabilities['dependency_analysis'],
                'available_tools': self.dependency_analyzer.available_tools
            }
        }