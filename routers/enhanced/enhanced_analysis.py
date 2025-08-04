"""Enhanced analysis API endpoints for tree-sitter, static analysis, and dependency analysis"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from analyzers.enhanced import EnhancedAnalyzer
from analyzers.git_analyzer import GitAnalyzer
from models.schemas import GitRepository, FileInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/enhanced", tags=["Enhanced Analysis"])


class EnhancedAnalysisRequest(BaseModel):
    """Enhanced 분석 요청 모델"""
    repositories: List[GitRepository]
    include_tree_sitter: bool = Field(default=True, description="Tree-sitter AST 분석 포함 여부")
    include_static_analysis: bool = Field(default=True, description="정적 분석 포함 여부")
    include_dependency_analysis: bool = Field(default=True, description="의존성 분석 포함 여부")
    generate_report: bool = Field(default=True, description="마크다운 리포트 생성 여부")


class EnhancedAnalysisResponse(BaseModel):
    """Enhanced 분석 응답 모델"""
    analysis_id: str
    status: str
    message: str
    capabilities_available: Dict[str, Any]
    repositories: List[GitRepository]


class AnalysisStatusResponse(BaseModel):
    """분석 상태 응답 모델"""
    analysis_id: str
    status: str
    progress: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    report_path: Optional[str] = None


# 전역 분석기 인스턴스
enhanced_analyzer = EnhancedAnalyzer()
git_analyzer = GitAnalyzer()

# 분석 상태 저장소 (실제 구현에서는 데이터베이스 사용)
analysis_status = {}
analysis_results = {}


@router.get("/capabilities")
async def get_capabilities():
    """Enhanced 분석기의 기능 상태 조회"""
    try:
        capabilities = enhanced_analyzer.get_capabilities_status()
        return {
            "status": "success",
            "capabilities": capabilities,
            "message": "Enhanced analyzer capabilities retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")


@router.post("/analyze", response_model=EnhancedAnalysisResponse)
async def start_enhanced_analysis(
    request: EnhancedAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """Enhanced 분석 시작"""
    try:
        # 분석 ID 생성
        analysis_id = f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(request.repositories)) % 10000}"
        
        # 분석 상태 초기화
        analysis_status[analysis_id] = {
            "status": "started",
            "progress": {
                "current_step": "initializing",
                "completed_steps": [],
                "total_repositories": len(request.repositories),
                "processed_repositories": 0
            },
            "start_time": datetime.now().isoformat(),
            "repositories": request.repositories
        }
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(
            run_enhanced_analysis,
            analysis_id,
            request
        )
        
        # 기능 상태 조회
        capabilities = enhanced_analyzer.get_capabilities_status()
        
        return EnhancedAnalysisResponse(
            analysis_id=analysis_id,
            status="started",
            message="Enhanced analysis started successfully",
            capabilities_available=capabilities,
            repositories=request.repositories
        )
        
    except Exception as e:
        logger.error(f"Error starting enhanced analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")


@router.get("/status/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회"""
    try:
        if analysis_id not in analysis_status:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        status_info = analysis_status[analysis_id]
        results = analysis_results.get(analysis_id)
        
        # 리포트 파일 경로 확인
        report_path = None
        if results and status_info["status"] == "completed":
            report_dir = Path("output/enhanced_reports")
            report_file = report_dir / f"{analysis_id}_report.md"
            if report_file.exists():
                report_path = str(report_file)
        
        return AnalysisStatusResponse(
            analysis_id=analysis_id,
            status=status_info["status"],
            progress=status_info["progress"],
            results=results,
            report_path=report_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/results/{analysis_id}")
async def get_analysis_results(analysis_id: str):
    """분석 결과 조회"""
    try:
        if analysis_id not in analysis_results:
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        return {
            "analysis_id": analysis_id,
            "status": "success",
            "results": analysis_results[analysis_id]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/report/{analysis_id}")
async def get_analysis_report(analysis_id: str):
    """분석 리포트 조회"""
    try:
        if analysis_id not in analysis_results:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # 리포트 파일 경로 확인
        report_dir = Path("output/enhanced_reports")
        report_file = report_dir / f"{analysis_id}_report.md"
        
        if not report_file.exists():
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # 리포트 내용 읽기
        with open(report_file, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        return {
            "analysis_id": analysis_id,
            "status": "success",
            "report_content": report_content,
            "report_path": str(report_file)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")


@router.delete("/results/{analysis_id}")
async def delete_analysis_results(analysis_id: str):
    """분석 결과 삭제"""
    try:
        # 메모리에서 결과 삭제
        if analysis_id in analysis_status:
            del analysis_status[analysis_id]
        if analysis_id in analysis_results:
            del analysis_results[analysis_id]
        
        # 리포트 파일 삭제
        report_dir = Path("output/enhanced_reports")
        report_file = report_dir / f"{analysis_id}_report.md"
        if report_file.exists():
            report_file.unlink()
        
        return {
            "analysis_id": analysis_id,
            "status": "success",
            "message": "Analysis results deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting analysis results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete results: {str(e)}")


@router.get("/list")
async def list_analyses():
    """모든 분석 목록 조회"""
    try:
        analyses = []
        for analysis_id, status_info in analysis_status.items():
            analyses.append({
                "analysis_id": analysis_id,
                "status": status_info["status"],
                "start_time": status_info["start_time"],
                "repositories_count": status_info["progress"]["total_repositories"],
                "processed_count": status_info["progress"]["processed_repositories"]
            })
        
        return {
            "status": "success",
            "total_analyses": len(analyses),
            "analyses": analyses
        }
        
    except Exception as e:
        logger.error(f"Error listing analyses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list analyses: {str(e)}")


async def run_enhanced_analysis(analysis_id: str, request: EnhancedAnalysisRequest):
    """백그라운드에서 실행되는 Enhanced 분석 함수"""
    try:
        logger.info(f"Starting enhanced analysis {analysis_id}")
        
        # 상태 업데이트
        analysis_status[analysis_id]["status"] = "running"
        analysis_status[analysis_id]["progress"]["current_step"] = "cloning_repositories"
        
        all_results = {
            "analysis_id": analysis_id,
            "repositories": [],
            "overall_summary": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 각 레포지토리 분석
        for i, repository in enumerate(request.repositories):
            try:
                logger.info(f"Processing repository {i+1}/{len(request.repositories)}: {repository.url}")
                
                # Git 클론
                analysis_status[analysis_id]["progress"]["current_step"] = f"cloning_{repository.url}"
                clone_path = git_analyzer.clone_repository(repository)
                
                # 파일 목록 생성
                analysis_status[analysis_id]["progress"]["current_step"] = f"analyzing_files_{repository.url}"
                files = git_analyzer.analyze_repository_structure(clone_path)
                
                # Enhanced 분석 수행
                analysis_status[analysis_id]["progress"]["current_step"] = f"enhanced_analysis_{repository.url}"
                repo_results = enhanced_analyzer.analyze_repository(
                    clone_path=clone_path,
                    files=files,
                    include_tree_sitter=request.include_tree_sitter,
                    include_static_analysis=request.include_static_analysis,
                    include_dependency_analysis=request.include_dependency_analysis
                )
                
                # 결과 저장
                repo_results["repository"] = repository.dict()
                all_results["repositories"].append(repo_results)
                
                # 진행 상태 업데이트
                analysis_status[analysis_id]["progress"]["processed_repositories"] = i + 1
                analysis_status[analysis_id]["progress"]["completed_steps"].append(f"repository_{i+1}")
                
                logger.info(f"Completed analysis for repository: {repository.url}")
                
            except Exception as e:
                logger.error(f"Error analyzing repository {repository.url}: {e}")
                # 에러가 발생해도 다른 레포지토리 분석 계속
                continue
        
        # 전체 요약 생성
        analysis_status[analysis_id]["progress"]["current_step"] = "generating_summary"
        all_results["overall_summary"] = generate_overall_summary(all_results["repositories"])
        
        # 리포트 생성
        if request.generate_report:
            analysis_status[analysis_id]["progress"]["current_step"] = "generating_report"
            await generate_enhanced_report(analysis_id, all_results)
        
        # 결과 저장
        analysis_results[analysis_id] = all_results
        
        # 상태 완료로 업데이트
        analysis_status[analysis_id]["status"] = "completed"
        analysis_status[analysis_id]["progress"]["current_step"] = "completed"
        analysis_status[analysis_id]["end_time"] = datetime.now().isoformat()
        
        logger.info(f"Enhanced analysis {analysis_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Enhanced analysis {analysis_id} failed: {e}")
        analysis_status[analysis_id]["status"] = "failed"
        analysis_status[analysis_id]["error"] = str(e)
        analysis_status[analysis_id]["end_time"] = datetime.now().isoformat()


def generate_overall_summary(repository_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """전체 레포지토리 분석 결과 요약 생성"""
    summary = {
        "total_repositories": len(repository_results),
        "total_files": 0,
        "total_ast_nodes": 0,
        "total_code_issues": 0,
        "total_dependencies": 0,
        "total_vulnerabilities": 0,
        "languages_detected": set(),
        "tools_used": set(),
        "capabilities_summary": {
            "tree_sitter_used": 0,
            "static_analysis_used": 0,
            "dependency_analysis_used": 0
        }
    }
    
    for repo_result in repository_results:
        summary["total_files"] += repo_result.get("total_files", 0)
        
        # Tree-sitter 요약
        if "tree_sitter" in repo_result.get("summary", {}):
            ts_summary = repo_result["summary"]["tree_sitter"]
            summary["total_ast_nodes"] += ts_summary.get("total_nodes", 0)
            summary["languages_detected"].update(ts_summary.get("languages", {}).keys())
            summary["capabilities_summary"]["tree_sitter_used"] += 1
        
        # 정적 분석 요약
        if "static_analysis" in repo_result.get("summary", {}):
            static_summary = repo_result["summary"]["static_analysis"]
            summary["total_code_issues"] += static_summary.get("total_issues", 0)
            summary["tools_used"].update(static_summary.get("tools_used", []))
            summary["capabilities_summary"]["static_analysis_used"] += 1
        
        # 의존성 분석 요약
        if "dependency_analysis" in repo_result.get("summary", {}):
            dep_summary = repo_result["summary"]["dependency_analysis"]
            summary["total_dependencies"] += dep_summary.get("total_dependencies", 0)
            summary["total_vulnerabilities"] += dep_summary.get("total_vulnerabilities", 0)
            summary["capabilities_summary"]["dependency_analysis_used"] += 1
    
    # Set을 리스트로 변환
    summary["languages_detected"] = list(summary["languages_detected"])
    summary["tools_used"] = list(summary["tools_used"])
    
    return summary


async def generate_enhanced_report(analysis_id: str, results: Dict[str, Any]):
    """Enhanced 분석 리포트 생성"""
    try:
        # 리포트 디렉토리 생성
        report_dir = Path("output/enhanced_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 리포트 내용 생성
        report_lines = []
        report_lines.append(f"# 🔍 Enhanced Analysis Report - {analysis_id}")
        report_lines.append("")
        report_lines.append(f"**Analysis Date:** {results['timestamp']}")
        report_lines.append(f"**Total Repositories:** {len(results['repositories'])}")
        report_lines.append("")
        
        # 전체 요약
        overall = results.get("overall_summary", {})
        if overall:
            report_lines.append("## 📊 Overall Summary")
            report_lines.append("")
            report_lines.append(f"- **Total Files Analyzed:** {overall.get('total_files', 0)}")
            report_lines.append(f"- **Total AST Nodes:** {overall.get('total_ast_nodes', 0)}")
            report_lines.append(f"- **Total Code Issues:** {overall.get('total_code_issues', 0)}")
            report_lines.append(f"- **Total Dependencies:** {overall.get('total_dependencies', 0)}")
            report_lines.append(f"- **Total Vulnerabilities:** {overall.get('total_vulnerabilities', 0)}")
            
            languages = overall.get('languages_detected', [])
            if languages:
                report_lines.append(f"- **Languages Detected:** {', '.join(languages)}")
            
            tools = overall.get('tools_used', [])
            if tools:
                report_lines.append(f"- **Analysis Tools Used:** {', '.join(tools)}")
            
            report_lines.append("")
        
        # 각 레포지토리별 상세 결과
        for i, repo_result in enumerate(results['repositories'], 1):
            repo_info = repo_result.get('repository', {})
            report_lines.append(f"## 📁 Repository {i}: {repo_info.get('name', 'Unknown')}")
            report_lines.append("")
            report_lines.append(f"**URL:** {repo_info.get('url', 'Unknown')}")
            report_lines.append(f"**Branch:** {repo_info.get('branch', 'main')}")
            report_lines.append("")
            
            # 개별 레포지토리 리포트 생성
            individual_report = enhanced_analyzer.generate_comprehensive_report(repo_result)
            # 헤더 레벨 조정 (## -> ###)
            individual_report = individual_report.replace("## ", "### ")
            individual_report = individual_report.replace("# 🔍 Enhanced Code Analysis Report", "")
            report_lines.append(individual_report)
            report_lines.append("")
        
        # 리포트 파일 저장
        report_content = "\n".join(report_lines)
        report_file = report_dir / f"{analysis_id}_report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Enhanced analysis report generated: {report_file}")
        
    except Exception as e:
        logger.error(f"Error generating enhanced report: {e}")
        raise