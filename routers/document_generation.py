from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging
import os

from models.schemas import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    DocumentGenerationStatus,
    GeneratedDocument
)
from services.llm_service import LLMDocumentService, DocumentType
from services.analysis_service import AnalysisService
from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/documents", 
    tags=["📄 Document Generation"],
    responses={
        200: {"description": "문서 생성 성공"},
        400: {"description": "잘못된 요청"},
        404: {"description": "분석 결과를 찾을 수 없음"},
        500: {"description": "서버 오류"}
    }
)

# 문서 생성 작업 상태 추적
document_generation_tasks = {}

@router.post(
    "/generate",
    response_model=DocumentGenerationResponse,
    summary="분석 결과 기반 문서 생성",
    description="""
    **분석 완료된 결과를 바탕으로 다양한 타입의 문서를 LLM으로 생성합니다.**
    
    ### 📄 생성 가능한 문서 타입
    - **development_guide**: 개발 가이드 (코딩 컨벤션, 모범 사례)
    - **api_documentation**: API 문서 (엔드포인트, 사용법)
    - **architecture_overview**: 아키텍처 개요 (시스템 구조, 컴포넌트)
    - **code_review_summary**: 코드 리뷰 요약 (이슈, 개선사항)
    - **technical_specification**: 기술 명세서 (기술 스택, 의존성)
    - **deployment_guide**: 배포 가이드 (환경 설정, 배포 과정)
    - **troubleshooting_guide**: 문제 해결 가이드 (일반적 오류, 해결법)
    
    ### 🌐 지원 언어
    - **korean**: 한국어 (기본값)
    - **english**: 영어
    
    ### 📝 사용 예시
    ```bash
    curl -X POST "http://localhost:8001/api/v1/documents/generate" \\
      -H "Content-Type: application/json" \\
      -d '{
        "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c",
        "document_types": ["development_guide", "api_documentation"],
        "language": "korean",
        "custom_prompt": "특히 FastAPI 관련 내용을 중심으로 작성해주세요."
      }'
    ```
    
    ### ⚡ 백그라운드 처리
    - 문서 생성은 백그라운드에서 비동기로 처리됩니다
    - 생성 상태는 `/status/{task_id}` 엔드포인트로 확인 가능합니다
    - 완료된 문서는 `output/documents/{analysis_id}/` 디렉토리에 저장됩니다
    """
)
async def generate_documents(
    request: DocumentGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """분석 결과를 바탕으로 문서를 생성합니다."""
    try:
        # 분석 결과 존재 확인
        analysis_service = AnalysisService()
        analysis_result = analysis_service.load_analysis_result(request.analysis_id)
        
        if not analysis_result:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "분석 결과를 찾을 수 없습니다.",
                    "analysis_id": request.analysis_id,
                    "suggestion": "먼저 /api/v1/analyze 엔드포인트로 분석을 수행하세요."
                }
            )
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        
        # 작업 상태 초기화
        document_generation_tasks[task_id] = {
            "status": DocumentGenerationStatus.PENDING,
            "analysis_id": request.analysis_id,
            "document_types": request.document_types,
            "language": request.language,
            "created_at": datetime.now(),
            "completed_at": None,
            "error_message": None,
            "generated_documents": []
        }
        
        # 백그라운드에서 문서 생성 실행
        background_tasks.add_task(
            _generate_documents_background,
            task_id,
            request,
            analysis_result
        )
        
        logger.info(f"Document generation task started: {task_id} for analysis {request.analysis_id}")
        
        return DocumentGenerationResponse(
            task_id=task_id,
            status=DocumentGenerationStatus.PENDING,
            message="문서 생성이 시작되었습니다.",
            analysis_id=request.analysis_id,
            document_types=request.document_types,
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document generation request failed: {e}")
        raise HTTPException(status_code=500, detail=f"문서 생성 요청 처리 중 오류가 발생했습니다: {str(e)}")


@router.get(
    "/status/{task_id}",
    response_model=DocumentGenerationResponse,
    summary="문서 생성 상태 조회",
    description="""
    **문서 생성 작업의 현재 상태를 조회합니다.**
    
    ### 📊 상태 정보
    - **pending**: 대기 중
    - **running**: 생성 중
    - **completed**: 완료
    - **failed**: 실패
    
    ### 📄 완료 시 제공 정보
    - 생성된 문서 목록
    - 각 문서의 파일 경로
    - 토큰 사용량
    - 생성 시간
    """
)
async def get_document_generation_status(task_id: str):
    """문서 생성 작업 상태를 조회합니다."""
    if task_id not in document_generation_tasks:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "문서 생성 작업을 찾을 수 없습니다.",
                "task_id": task_id,
                "available_tasks": list(document_generation_tasks.keys())
            }
        )
    
    task_info = document_generation_tasks[task_id]
    
    return DocumentGenerationResponse(
        task_id=task_id,
        status=task_info["status"],
        message=_get_status_message(task_info["status"]),
        analysis_id=task_info["analysis_id"],
        document_types=task_info["document_types"],
        language=task_info["language"],
        created_at=task_info["created_at"],
        completed_at=task_info.get("completed_at"),
        error_message=task_info.get("error_message"),
        generated_documents=task_info.get("generated_documents", [])
    )


@router.get(
    "/types",
    response_model=List[str],
    summary="사용 가능한 문서 타입 목록",
    description="""
    **생성 가능한 모든 문서 타입의 목록을 반환합니다.**
    
    각 문서 타입은 특정 목적과 구조를 가지고 있으며,
    분석 결과에 따라 적절한 내용으로 생성됩니다.
    """
)
async def get_available_document_types():
    """사용 가능한 문서 타입 목록을 반환합니다."""
    try:
        llm_service = LLMDocumentService()
        return llm_service.get_available_document_types()
    except Exception as e:
        logger.error(f"Failed to get document types: {e}")
        raise HTTPException(status_code=500, detail="문서 타입 목록을 가져오는 중 오류가 발생했습니다.")


@router.get(
    "/list/{analysis_id}",
    response_model=List[GeneratedDocument],
    summary="분석별 생성된 문서 목록",
    description="""
    **특정 분석 ID에 대해 생성된 모든 문서의 목록을 반환합니다.**
    
    ### 📁 문서 저장 위치
    - 경로: `output/documents/{analysis_id}/`
    - 파일명 형식: `{document_type}_{language}.md`
    
    ### 📄 반환 정보
    - 문서 타입
    - 파일 경로
    - 생성 시간
    - 파일 크기
    - 언어
    """
)
async def list_generated_documents(analysis_id: str):
    """특정 분석 ID에 대해 생성된 문서 목록을 반환합니다."""
    try:
        documents_dir = f"output/documents/{analysis_id}"
        
        if not os.path.exists(documents_dir):
            return []
        
        documents = []
        for filename in os.listdir(documents_dir):
            if filename.endswith('.md'):
                file_path = os.path.join(documents_dir, filename)
                file_stat = os.stat(file_path)
                
                # 파일명에서 문서 타입과 언어 추출
                name_parts = filename[:-3].split('_')  # .md 제거
                document_type = name_parts[0] if len(name_parts) > 0 else "unknown"
                language = name_parts[1] if len(name_parts) > 1 else "korean"
                
                documents.append(GeneratedDocument(
                    document_type=document_type,
                    language=language,
                    file_path=file_path,
                    file_size=file_stat.st_size,
                    created_at=datetime.fromtimestamp(file_stat.st_ctime),
                    analysis_id=analysis_id
                ))
        
        return documents
        
    except Exception as e:
        logger.error(f"Failed to list documents for analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="문서 목록을 가져오는 중 오류가 발생했습니다.")


@router.delete(
    "/delete/{analysis_id}",
    summary="분석별 생성된 문서 삭제",
    description="""
    **특정 분석 ID에 대해 생성된 모든 문서를 삭제합니다.**
    
    ### ⚠️ 주의사항
    - 삭제된 문서는 복구할 수 없습니다
    - 디렉토리 전체가 삭제됩니다
    """
)
async def delete_generated_documents(analysis_id: str):
    """특정 분석 ID에 대해 생성된 문서들을 삭제합니다."""
    try:
        documents_dir = f"output/documents/{analysis_id}"
        
        if not os.path.exists(documents_dir):
            raise HTTPException(
                status_code=404,
                detail=f"분석 ID {analysis_id}에 대한 문서가 존재하지 않습니다."
            )
        
        import shutil
        shutil.rmtree(documents_dir)
        
        logger.info(f"Deleted documents directory: {documents_dir}")
        
        return {"message": f"분석 ID {analysis_id}의 모든 문서가 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete documents for analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="문서 삭제 중 오류가 발생했습니다.")


async def _generate_documents_background(
    task_id: str,
    request: DocumentGenerationRequest,
    analysis_result: Any
):
    """백그라운드에서 문서 생성을 수행합니다."""
    try:
        # 작업 상태를 실행 중으로 변경
        document_generation_tasks[task_id]["status"] = DocumentGenerationStatus.RUNNING
        
        logger.info(f"Starting document generation for task {task_id}")
        
        # LLM 서비스 초기화
        llm_service = LLMDocumentService()
        
        # 분석 결과를 딕셔너리로 변환 (analysis_service의 로직과 동일)
        analysis_data = {
            "analysis_id": request.analysis_id,
            "repositories": [],
            "tech_specs": [],
            "ast_analysis": {},
            "code_metrics": {}
        }
        
        # 저장소 정보 추출
        if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
            for repo in analysis_result.repositories:
                repo_data = {
                    "url": repo.repository.url if hasattr(repo, 'repository') else "Unknown",
                    "branch": repo.repository.branch if hasattr(repo, 'repository') else "main",
                    "name": repo.repository.name if hasattr(repo, 'repository') else None
                }
                analysis_data["repositories"].append(repo_data)
                
                # 기술 스펙 정보 추가
                if hasattr(repo, 'tech_specs') and repo.tech_specs:
                    for tech_spec in repo.tech_specs:
                        tech_data = {
                            "name": tech_spec.language if hasattr(tech_spec, 'language') else "Unknown",
                            "version": tech_spec.version if hasattr(tech_spec, 'version') else "Unknown",
                            "framework": tech_spec.framework if hasattr(tech_spec, 'framework') else None,
                            "dependencies": tech_spec.dependencies if hasattr(tech_spec, 'dependencies') else []
                        }
                        analysis_data["tech_specs"].append(tech_data)
                
                # AST 분석 정보 추가
                if hasattr(repo, 'ast_analysis') and repo.ast_analysis:
                    analysis_data["ast_analysis"].update(repo.ast_analysis)
                
                # 코드 메트릭 정보 추가
                if hasattr(repo, 'code_metrics') and repo.code_metrics:
                    metrics = repo.code_metrics
                    analysis_data["code_metrics"] = {
                        "total_files": metrics.total_files if hasattr(metrics, 'total_files') else 0,
                        "total_lines": metrics.total_lines if hasattr(metrics, 'total_lines') else 0,
                        "cyclomatic_complexity": metrics.cyclomatic_complexity if hasattr(metrics, 'cyclomatic_complexity') else 0,
                        "maintainability_index": metrics.maintainability_index if hasattr(metrics, 'maintainability_index') else 0
                    }
        
        # 문서 타입을 DocumentType enum으로 변환
        document_types = [DocumentType(doc_type) for doc_type in request.document_types]
        
        # 문서 생성
        generated_documents = await llm_service.generate_multiple_documents(
            analysis_data=analysis_data,
            document_types=document_types,
            language=request.language
        )
        
        # 생성된 문서들을 파일로 저장
        documents_dir = f"output/documents/{request.analysis_id}"
        os.makedirs(documents_dir, exist_ok=True)
        
        saved_documents = []
        for doc in generated_documents:
            if "error" not in doc:  # 성공적으로 생성된 문서만 저장
                doc_filename = f"{doc['document_type']}_{doc['language']}.md"
                doc_path = os.path.join(documents_dir, doc_filename)
                
                with open(doc_path, 'w', encoding='utf-8') as f:
                    f.write(doc['content'])
                
                # 저장된 문서 정보 추가
                file_stat = os.stat(doc_path)
                saved_documents.append(GeneratedDocument(
                    document_type=doc['document_type'],
                    language=doc['language'],
                    file_path=doc_path,
                    file_size=file_stat.st_size,
                    created_at=datetime.fromtimestamp(file_stat.st_ctime),
                    analysis_id=request.analysis_id,
                    tokens_used=doc.get('tokens_used', 0)
                ))
                
                logger.info(f"Document saved: {doc_path}")
            else:
                logger.error(f"Failed to generate document {doc['document_type']}: {doc.get('error')}")
        
        # 작업 완료 처리
        document_generation_tasks[task_id].update({
            "status": DocumentGenerationStatus.COMPLETED,
            "completed_at": datetime.now(),
            "generated_documents": saved_documents
        })
        
        logger.info(f"Document generation completed for task {task_id}. Generated {len(saved_documents)} documents.")
        
    except Exception as e:
        logger.error(f"Document generation failed for task {task_id}: {e}")
        
        # 작업 실패 처리
        document_generation_tasks[task_id].update({
            "status": DocumentGenerationStatus.FAILED,
            "completed_at": datetime.now(),
            "error_message": str(e)
        })


def _get_status_message(status: DocumentGenerationStatus) -> str:
    """상태에 따른 메시지를 반환합니다."""
    messages = {
        DocumentGenerationStatus.PENDING: "문서 생성 대기 중입니다.",
        DocumentGenerationStatus.RUNNING: "문서를 생성하고 있습니다.",
        DocumentGenerationStatus.COMPLETED: "문서 생성이 완료되었습니다.",
        DocumentGenerationStatus.FAILED: "문서 생성에 실패했습니다."
    }
    return messages.get(status, "알 수 없는 상태입니다.")