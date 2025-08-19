import logging
from typing import List, Dict, Any, Optional

from models.schemas import GitRepository, RepositoryAnalysis, TechSpec, CodeMetrics
from utils.tech_utils import detect_tech_stack

logger = logging.getLogger(__name__)

class TechSpecAnalyzer:
    """기술 스펙 분석을 담당하는 클래스"""

    def __init__(self):
        pass

    async def perform_analysis(self, analysis_id: str, request, analysis_results: dict):
        """기술스펙 분석 수행"""
        try:
            if not request.include_tech_spec:
                logger.info(f"Tech spec analysis skipped for {analysis_id}")
                return
                
            logger.info(f"Performing tech spec analysis for {analysis_id}")
            
            # 기술스펙 분석 로직 구현
            if analysis_id in analysis_results and analysis_results[analysis_id].repositories:
                updated_repositories = []

                for repo_dict in analysis_results[analysis_id].repositories:
                    try:
                        # Dictionary를 RepositoryAnalysis 객체로 변환
                        if isinstance(repo_dict, dict):
                            git_repo = GitRepository(
                                url=repo_dict["git_url"],
                                branch=repo_dict.get("branch", "main"),
                                name=repo_dict.get("name")
                            )
                            repo = RepositoryAnalysis(
                                repository=git_repo,
                                clone_path="",  # 실제 클론 경로로 대체 필요
                                code_metrics=CodeMetrics()
                            )
                        else:
                            repo = repo_dict

                        # 기술 스펙 분석 수행 - 동적 감지
                        
                        # 실제 프로젝트 파일들을 분석하여 기술 스택 감지
                        clone_path = repo.clone_path if hasattr(repo, 'clone_path') and repo.clone_path else ""
                        files = repo.files if hasattr(repo, 'files') else []
                        
                        if clone_path and files:
                            detected_tech_stacks = detect_tech_stack(clone_path, files)
                            
                            # 감지된 기술 스택들을 TechSpec 객체로 변환
                            for tech_data in detected_tech_stacks:
                                tech_spec = TechSpec(
                                    language=tech_data.get('language', 'Unknown'),
                                    framework=tech_data.get('framework'),
                                    dependencies=tech_data.get('dependencies', []),
                                    version=tech_data.get('version'),
                                    package_manager=tech_data.get('package_manager')
                                )
                                repo.tech_specs.append(tech_spec)
                        else:
                            # 클론 경로나 파일 정보가 없는 경우 기본값 사용
                            logger.warning(f"No clone path or files available for tech spec analysis: {repo.repository.url}")
                            tech_spec = TechSpec(
                                language="Unknown",
                                framework=None,
                                dependencies=[],
                                version=None,
                                package_manager=None
                            )
                            repo.tech_specs.append(tech_spec)
                        
                        # 코드 메트릭스 업데이트
                        repo.code_metrics.maintainability_index = 85.0  # 실제 값으로 대체
                        repo.code_metrics.cyclomatic_complexity = 7.5   # 실제 값으로 대체
                        
                        updated_repositories.append(repo)
                        logger.info(f"Tech spec analysis completed for repository: {repo.repository.url}")
                        
                    except Exception as e:
                        logger.error(f"Error processing tech spec analysis for repository: {str(e)}")
                        continue
                
                # 업데이트된 저장소 목록으로 교체
                analysis_results[analysis_id].repositories = updated_repositories
                    
        except Exception as e:
            logger.error(f"Tech spec analysis failed for {analysis_id}: {e}")
            raise
