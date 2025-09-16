import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
import asyncio
import os
from services.itsd_service import ItsdService, get_itsd_service
from services.itsd_embedding_service import get_itsd_embedding_service, ItsdEmbeddingService
from datetime import datetime
from models.schemas import ItsdRecommendationRequest
from services.itsd_job_status import JobStatusStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/itsd", tags=["ITSD"])

@router.post(
    "/embed-requests",
    summary="ITSD 요청 데이터(Excel) 임베딩",
    description="과거 ITSD 요청 데이터가 담긴 Excel(.xlsx) 파일을 업로드하여 벡터 DB에 임베딩합니다.",
)
async def embed_itsd_requests_from_file(
    file: UploadFile = File(..., description="ITSD 요청 데이터 Excel(.xlsx) 파일"),
    itsd_service: ItsdService = Depends(get_itsd_service),
):
    """
    Excel(.xlsx) 파일을 받아 ITSD 요청 데이터를 처리하고 임베딩합니다.
    - Excel 필수 컬럼: `request_id`, `title`, `content`, `assignee`
    - 임베딩 시 `itsd_requests` 그룹으로 저장됩니다.
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel(.xlsx) 파일만 업로드할 수 있습니다.",
        )
    
    content = await file.read() # 파일 내용을 먼저 읽습니다.
    try:
        count = await itsd_service.embed_itsd_requests_from_file(content)
        return {"message": "ITSD 요청 데이터 임베딩이 성공적으로 완료되었습니다.", "embedded_count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # 임베딩 실패 시 디버깅을 위해 파일을 임시 저장
        temp_dir = "output/failed_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        # 파일명이 중복되지 않도록 timestamp 사용
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
        failed_file_path = os.path.join(temp_dir, f"{timestamp}_{file.filename}")
        
        try:
            with open(failed_file_path, "wb") as f:
                f.write(content) # try 블록 시작 시 읽어둔 내용을 사용합니다.
        except Exception as write_error:
            logger.error(f"실패한 업로드 파일을 저장하는 중 오류 발생: {write_error}")
            
        logger.error(f"임베딩 실패. 업로드된 파일이 '{failed_file_path}'에 저장되었습니다. 오류: {e}")
        # 원인 메시지를 함께 전달하여 트러블슈팅에 도움을 줍니다.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 임베딩 중 오류가 발생했습니다. (오류 파일: {failed_file_path}) 원인: {str(e)}"
        )

@router.post(
    "/embed-requests-async",
    summary="ITSD 요청 데이터(Excel) 임베딩 — 비동기 처리",
    description="Excel(.xlsx) 업로드를 큐에 저장하고 즉시 job_id를 반환합니다. 진행상태는 별도 API로 조회합니다.",
)
async def embed_itsd_requests_async(
    file: UploadFile = File(..., description="ITSD 요청 데이터 Excel(.xlsx) 파일"),
    itsd_service: ItsdService = Depends(get_itsd_service),
):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel(.xlsx) 파일만 업로드할 수 있습니다.",
        )

    # Store file to disk for background processing
    uploads_dir = "output/uploads"
    os.makedirs(uploads_dir, exist_ok=True)

    content = await file.read()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Job creation
    job_store = JobStatusStore()
    job = job_store.create_job(task="itsd_embed", filename=file.filename)
    saved_path = os.path.join(uploads_dir, f"{job['job_id']}_{timestamp}_{file.filename}")
    try:
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception as e:
        job_store.fail_job(job["job_id"], error=f"파일 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"업로드 파일 저장 실패: {str(e)}")

    # Background processing function
    async def _process(job_id: str, path: str, svc: ItsdService):
        try:
            job_store.start_job(job_id)
            # progress helper
            def _progress(pct: float | int, stage: str | None = None):
                try:
                    JobStatusStore().set_progress(job_id, pct, stage)
                except Exception:
                    pass
            with open(path, "rb") as f:
                bytes_content = f.read()
            _progress(5, "file_loaded")
            count = await svc.embed_itsd_requests_from_file(bytes_content, progress_cb=_progress)
            job_store.complete_job(job_id, result={"embedded_count": int(count) if count is not None else 0})
        except Exception as e:
            job_store.fail_job(job_id, error=str(e))
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    # Fire-and-forget task detached from request lifecycle
    asyncio.create_task(_process(job["job_id"], saved_path, itsd_service))
    return {"job_id": job["job_id"], "status": "queued"}


@router.get(
    "/embed-requests-status/{job_id}",
    summary="임베딩 작업 상태 조회",
)
async def get_embed_status(job_id: str):
    job_store = JobStatusStore()
    data = job_store.get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="해당 job_id를 찾을 수 없습니다.")
    return data

@router.post(
    "/embed-local-requests",
    summary="로컬 ITSD 요청 데이터(Excel) 임베딩",
    description="프로젝트 내 `data/itsd_request_data.xlsx` 파일을 벡터 DB에 임베딩합니다.",
)
async def embed_local_itsd_requests(
    itsd_service: ItsdService = Depends(get_itsd_service),
):
    """
    프로젝트 내부에 위치한 기본 ITSD 데이터 파일을 임베딩합니다.
    """
    local_file_path = "data/itsd_request_data.xlsx"
    try:
        count = await itsd_service.embed_itsd_requests_from_path(local_file_path)
        return {"message": f"'{local_file_path}' 파일의 임베딩이 성공적으로 완료되었습니다.", "embedded_count": count}
    except FileNotFoundError:
        logger.error(f"로컬 ITSD 데이터 파일을 찾을 수 없습니다: {local_file_path}")
        raise HTTPException(status_code=404, detail=f"'{local_file_path}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"로컬 ITSD 데이터 임베딩 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"로컬 파일 임베딩 중 오류가 발생했습니다: {str(e)}")

@router.post(
    "/recommend-assignee",
    summary="ITSD 담당자 추천",
    description="새로운 ITSD 요청 내용(제목, 설명)을 기반으로 최적의 담당자를 추천합니다.",
    response_model=str,
)
async def recommend_assignee(
    request: ItsdRecommendationRequest,
    page: int = 1,
    page_size: int = 5,
    # Optional fusion overrides (per request)
    use_rrf: bool | None = None,
    w_title: float | None = None,
    w_content: float | None = None,
    rrf_k0: int | None = None,
    top_k_each: int | None = None,
    itsd_service: ItsdService = Depends(get_itsd_service),
):
    """
    신규 ITSD 요청에 대해 AI가 과거 데이터를 분석하여 담당자를 추천합니다.
    """
    try:
        # 안전한 기본값 보정
        page = max(1, int(page))
        page_size = max(1, min(50, int(page_size)))
        recommendation = await itsd_service.recommend_assignee(
            request.title,
            request.description,
            page=page,
            page_size=page_size,
            use_rrf=use_rrf,
            w_title=w_title,
            w_content=w_content,
            rrf_k0=rrf_k0,
            top_k_each=top_k_each,
        )
        return recommendation
    except Exception as e:
        logger.error(f"담당자 추천 API 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"담당자 추천 중 서버 오류가 발생했습니다: {str(e)}")


@router.get(
    "/debug/index-stats",
    summary="ITSD 인덱스 상태(필드별 카운트) 조회",
)
async def debug_index_stats(
    svc: ItsdEmbeddingService = Depends(get_itsd_embedding_service),
):
    """듀얼 인덱싱이 정상인지 확인하기 위한 간단한 통계 API"""
    try:
        return svc.get_itsd_index_stats()
    except Exception as e:
        logger.error(f"debug/index-stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/debug/sample",
    summary="ITSD 샘플 문서 조회",
    description="필드(title|content|combined) 별 샘플 문서 메타/내용을 확인합니다.",
)
async def debug_sample(
    field: str = "title",
    limit: int = 3,
    svc: ItsdEmbeddingService = Depends(get_itsd_embedding_service),
):
    try:
        field = field.strip().lower()
        if field not in {"title", "content", "combined"}:
            raise HTTPException(status_code=400, detail="field must be one of: title, content, combined")
        col = getattr(svc.vectorstore, "_collection", None)
        if col is None:
            raise HTTPException(status_code=500, detail="No collection bound")
        where = {"group_name": "itsd_requests", "itsd_field": field}
        out = []
        # Attempt server-side filter first
        try:
            res = col.get(where=where, limit=max(1, min(50, limit)), include=["metadatas", "documents"])  # type: ignore[arg-type]
            if isinstance(res, dict):
                mets = res.get("metadatas", []) or []
                docs = res.get("documents", []) or []
                for m, d in zip(mets, docs):
                    out.append({"metadata": m, "content": d})
        except Exception:
            pass
        # If no items due to filter support, try client-side filtering
        if not out:
            try:
                res = col.get(limit=max(1, min(200, limit * 10)), include=["metadatas", "documents"])  # type: ignore[arg-type]
                if isinstance(res, dict):
                    mets = res.get("metadatas", []) or []
                    docs = res.get("documents", []) or []
                    for m, d in zip(mets, docs):
                        if isinstance(m, dict) and all(m.get(k) == v for k, v in where.items()):
                            out.append({"metadata": m, "content": d})
                            if len(out) >= limit:
                                break
            except Exception:
                pass
        return {"field": field, "sample_count": len(out), "items": out}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"debug/sample failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
