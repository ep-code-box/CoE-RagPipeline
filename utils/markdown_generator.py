import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from models.schemas import AnalysisResult, RepositoryAnalysis, TechSpec, CorrelationAnalysis


class MarkdownGenerator:
    """분석 결과를 마크다운 형식으로 변환하는 클래스"""
    
    def __init__(self, output_dir: str = "output/markdown"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_analysis_report(self, analysis_result: AnalysisResult) -> str:
        """분석 결과 전체를 마크다운 리포트로 생성"""
        md_content = []
        
        # 헤더 생성
        md_content.append(self._generate_header(analysis_result))
        
        # 분석 개요
        md_content.append(self._generate_overview(analysis_result))
        
        # 레포지토리별 상세 분석
        for i, repo in enumerate(analysis_result.repositories, 1):
            md_content.append(self._generate_repository_section(repo, i))
        
        # 연관도 분석 (있는 경우)
        if analysis_result.correlation_analysis:
            md_content.append(self._generate_correlation_section(analysis_result.correlation_analysis))
        
        # 요약 및 권장사항
        md_content.append(self._generate_summary_section(analysis_result))
        
        return "\n\n".join(md_content)
    
    def _generate_header(self, analysis_result: AnalysisResult) -> str:
        """마크다운 헤더 생성"""
        created_date = analysis_result.created_at.strftime("%Y-%m-%d %H:%M:%S") if analysis_result.created_at else "Unknown"
        completed_date = analysis_result.completed_at.strftime("%Y-%m-%d %H:%M:%S") if analysis_result.completed_at else "In Progress"
        
        return f"""# 📊 코드 분석 리포트

**분석 ID**: `{analysis_result.analysis_id}`  
**생성 일시**: {created_date}  
**완료 일시**: {completed_date}  
**상태**: {analysis_result.status.value}  
**분석 대상**: {len(analysis_result.repositories)}개 레포지토리

---"""
    
    def _generate_overview(self, analysis_result: AnalysisResult) -> str:
        """분석 개요 섹션 생성"""
        total_files = sum(len(repo.files) for repo in analysis_result.repositories)
        total_lines = sum(repo.code_metrics.lines_of_code for repo in analysis_result.repositories)
        
        languages = set()
        frameworks = set()
        
        for repo in analysis_result.repositories:
            for tech_spec in repo.tech_specs:
                if tech_spec.language:
                    languages.add(tech_spec.language)
                if tech_spec.framework:
                    frameworks.add(tech_spec.framework)
        
        overview = f"""## 📋 분석 개요

### 📊 통계 정보
- **총 파일 수**: {total_files:,}개
- **총 코드 라인 수**: {total_lines:,}줄
- **사용 언어**: {', '.join(sorted(languages)) if languages else 'N/A'}
- **주요 프레임워크**: {', '.join(sorted(frameworks)) if frameworks else 'N/A'}

### 🎯 분석 범위
- **AST 분석**: {'✅ 포함' if any(repo.ast_analysis for repo in analysis_result.repositories) else '❌ 제외'}
- **기술 스펙 분석**: {'✅ 포함' if any(repo.tech_specs for repo in analysis_result.repositories) else '❌ 제외'}
- **연관도 분석**: {'✅ 포함' if analysis_result.correlation_analysis else '❌ 제외'}"""
        
        return overview
    
    def _generate_repository_section(self, repo: RepositoryAnalysis, index: int) -> str:
        """레포지토리별 상세 분석 섹션 생성"""
        section = f"""## {index}. 📁 {repo.repository.name}

**URL**: [{repo.repository.url}]({repo.repository.url})  
**브랜치**: `{repo.repository.branch}`  
**클론 경로**: `{repo.clone_path}`

### 📊 코드 메트릭스
- **파일 수**: {len(repo.files)}개
- **코드 라인 수**: {repo.code_metrics.lines_of_code:,}줄
- **순환 복잡도**: {repo.code_metrics.cyclomatic_complexity:.2f}
- **유지보수성 지수**: {repo.code_metrics.maintainability_index:.2f}"""
        
        # 기술 스펙 정보
        if repo.tech_specs:
            section += "\n\n### 🛠️ 기술 스택"
            for tech_spec in repo.tech_specs:
                section += f"""
- **언어**: {tech_spec.language}
- **프레임워크**: {tech_spec.framework}
- **버전**: {tech_spec.version}
- **패키지 매니저**: {tech_spec.package_manager}
- **주요 의존성**: {', '.join(tech_spec.dependencies[:10]) if tech_spec.dependencies else 'N/A'}"""
        
        # AST 분석 정보
        if repo.ast_analysis:
            section += f"\n\n### 🌳 AST 분석 결과"
            total_nodes = sum(len(nodes) for nodes in repo.ast_analysis.values())
            section += f"\n- **총 노드 수**: {total_nodes}개"
            
            # 파일별 AST 통계
            for file_path, nodes in repo.ast_analysis.items():
                functions = [node for node in nodes if node.type == "function"]
                classes = [node for node in nodes if node.type == "class"]
                
                if functions or classes:
                    section += f"\n- **{file_path}**: 함수 {len(functions)}개, 클래스 {len(classes)}개"
        
        # 파일 목록 (상위 10개만)
        if repo.files:
            section += "\n\n### 📄 주요 파일 목록"
            for file in repo.files[:10]:
                section += f"\n- `{file.path}` ({file.language}, {file.lines_of_code}줄)"
            
            if len(repo.files) > 10:
                section += f"\n- ... 외 {len(repo.files) - 10}개 파일"
        
        return section
    
    def _generate_correlation_section(self, correlation: CorrelationAnalysis) -> str:
        """연관도 분석 섹션 생성"""
        section = f"""## 🔗 레포지토리 연관도 분석

### 📊 연관도 점수
- **전체 유사도**: {correlation.overall_similarity:.2f}%
- **기술 스택 유사도**: {correlation.tech_stack_similarity:.2f}%
- **코드 패턴 유사도**: {correlation.code_pattern_similarity:.2f}%
- **아키텍처 유사도**: {correlation.architecture_similarity:.2f}%"""
        
        # 공통 의존성
        if correlation.common_dependencies:
            section += "\n\n### 🔧 공통 의존성"
            for dep in correlation.common_dependencies[:15]:  # 상위 15개만
                section += f"\n- `{dep}`"
        
        # 공통 패턴
        if correlation.common_patterns:
            section += "\n\n### 🎨 공통 코드 패턴"
            for pattern in correlation.common_patterns[:10]:  # 상위 10개만
                section += f"\n- {pattern}"
        
        # 권장사항
        if correlation.recommendations:
            section += "\n\n### 💡 권장사항"
            for rec in correlation.recommendations:
                section += f"\n- {rec}"
        
        return section
    
    def _generate_summary_section(self, analysis_result: AnalysisResult) -> str:
        """요약 및 권장사항 섹션 생성"""
        section = """## 📝 분석 요약

### 🎯 주요 발견사항"""
        
        # 언어별 통계
        language_stats = {}
        for repo in analysis_result.repositories:
            for file in repo.files:
                lang = file.language
                if lang not in language_stats:
                    language_stats[lang] = {"files": 0, "lines": 0}
                language_stats[lang]["files"] += 1
                language_stats[lang]["lines"] += (file.lines_of_code or 0)
        
        if language_stats:
            section += "\n\n#### 📊 언어별 통계"
            for lang, stats in sorted(language_stats.items(), key=lambda x: x[1]["lines"], reverse=True):
                section += f"\n- **{lang}**: {stats['files']}개 파일, {stats['lines']:,}줄"
        
        # 코드 품질 평가
        avg_complexity = sum(repo.code_metrics.cyclomatic_complexity for repo in analysis_result.repositories) / len(analysis_result.repositories)
        avg_maintainability = sum(repo.code_metrics.maintainability_index for repo in analysis_result.repositories) / len(analysis_result.repositories)
        
        section += f"""

#### 🏆 코드 품질 평가
- **평균 순환 복잡도**: {avg_complexity:.2f} {'🟢 양호' if avg_complexity < 10 else '🟡 보통' if avg_complexity < 20 else '🔴 개선 필요'}
- **평균 유지보수성**: {avg_maintainability:.2f} {'🟢 우수' if avg_maintainability > 80 else '🟡 보통' if avg_maintainability > 60 else '🔴 개선 필요'}

### 🚀 개선 권장사항
- 코드 복잡도가 높은 함수들의 리팩토링 검토
- 공통 의존성을 활용한 코드 재사용성 향상
- 일관된 코딩 스타일 가이드 적용
- 단위 테스트 커버리지 확대

---

*이 리포트는 CoE RAG Pipeline에 의해 자동 생성되었습니다.*  
*생성 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""
        
        return section
    
    def save_markdown_report(self, analysis_result: AnalysisResult, filename: Optional[str] = None) -> str:
        """마크다운 리포트를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_report_{analysis_result.analysis_id}_{timestamp}.md"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            md_content = self.generate_analysis_report(analysis_result)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            print(f"✅ 마크다운 리포트 생성 완료: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 마크다운 리포트 생성 실패: {e}")
            raise
    
    def generate_simple_summary(self, analysis_result: AnalysisResult) -> str:
        """간단한 요약 마크다운 생성"""
        total_files = sum(len(repo.files) for repo in analysis_result.repositories)
        total_lines = sum(repo.code_metrics.lines_of_code for repo in analysis_result.repositories)
        
        return f"""# 분석 요약 - {analysis_result.analysis_id}

- **레포지토리 수**: {len(analysis_result.repositories)}개
- **총 파일 수**: {total_files:,}개  
- **총 코드 라인**: {total_lines:,}줄
- **분석 상태**: {analysis_result.status.value}
- **완료 시간**: {analysis_result.completed_at.strftime("%Y-%m-%d %H:%M:%S") if analysis_result.completed_at else "진행중"}

상세 분석 결과는 전체 리포트를 참조하세요."""


def generate_markdown_report(analysis_result: AnalysisResult, output_dir: str = "output/markdown") -> str:
    """편의 함수: 분석 결과를 마크다운 리포트로 생성하고 저장"""
    generator = MarkdownGenerator(output_dir)
    return generator.save_markdown_report(analysis_result)