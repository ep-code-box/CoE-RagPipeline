import os
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
import pandas as pd

from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from config.settings import settings
from services.embedding_service import EmbeddingService
from utils.token_utils import TokenUtils
from openai import OpenAI

logger = logging.getLogger(__name__)


class ItsdEmbeddingService(EmbeddingService):
    """ITSD 전용 임베딩/검색 유틸리티.

    - ITSD 요청 텍스트/메타데이터 저장(embed_and_store)
    - ITSD 전용 검색(search_similar_itsd_requests)
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
    ):
        # OpenAI/Chroma 설정
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.openai_api_base = openai_api_base or os.getenv("OPENAI_API_BASE")
        self.chroma_host = settings.CHROMA_HOST
        self.chroma_port = settings.CHROMA_PORT
        self.collection_name = settings.CHROMA_COLLECTION_NAME

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        # ITSD 전용 토큰/배치 파라미터
        self.max_tokens_per_request = int(os.getenv("OPENAI_EMBED_MAX_TOKENS_PER_REQUEST", "250000"))
        self.max_tokens_per_doc = int(os.getenv("OPENAI_EMBED_MAX_TOKENS_PER_DOC", "8000"))
        self.max_docs_per_batch = int(os.getenv("OPENAI_EMBED_MAX_DOCS_PER_BATCH", "128"))

        # Embeddings 초기화 (모델 선택 포함)
        embedding_kwargs: Dict[str, Any] = {"api_key": self.openai_api_key}
        if self.openai_api_base:
            embedding_kwargs["base_url"] = self.openai_api_base
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")
        embedding_kwargs["model"] = embedding_model
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)

        # 텍스트 분할기
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        # Chroma 클라이언트 + 연결 확인 + 코사인 메트릭 컬렉션
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        try:
            chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False),
            )
            # 연결 확인
            try:
                hb = chroma_client.heartbeat()
                logger.info(f"ChromaDB heartbeat OK: {hb}")
            except Exception as e:
                raise RuntimeError(
                    f"ChromaDB 연결 실패: {self.chroma_host}:{self.chroma_port}. 서버가 실행 중인지 확인하세요. 원인: {e}"
                )

            self.vectorstore = Chroma(
                client=chroma_client,
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                collection_metadata={"hnsw:space": "cosine"},
            )
            try:
                meta = getattr(self.vectorstore, "_collection", None)
                space = None
                if meta is not None:
                    space = getattr(meta, "metadata", {}).get("hnsw:space")
                logger.info(
                    f"Connected to ChromaDB at {self.chroma_host}:{self.chroma_port}, collection: {self.collection_name}, metric={(space or 'unknown')}"
                )
                if space and str(space).lower() != "cosine":
                    logger.warning(
                        f"Chroma collection '{self.collection_name}' metric is '{space}', not 'cosine'. Consider recreating the collection."
                    )
            except Exception:
                logger.info("Chroma collection metadata check skipped")
        except Exception as e:
            logger.error(f"ChromaDB 초기화 실패: {e}")
            raise

        # LLM 클라이언트 (리랭킹용)
        # 전역 타임아웃 비적용: 기본 동작 유지
        self.llm_client = OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base,
        )
        logger.info("LLM client initialized for reranking (ITSD).")

    # --- ITSD Excel embedding (moved from ItsdService) ---
    async def embed_itsd_requests_from_excel_bytes(self, file_content: bytes, progress_cb=None) -> int:
        """
        Excel(.xlsx) 파일 바이트를 파싱하여 ITSD 요청 데이터를 임베딩합니다.

        - 필수 컬럼 검증: request_id, title, content, assignee, applied_system
        - combined/title/content 변형과 메타데이터 구성
        - 목표 평균 토큰 크기에 맞게 분할 파라미터 선택
        """
        try:
            excel_file = BytesIO(file_content)
            try:
                df = pd.read_excel(excel_file, engine="openpyxl")
            except Exception as e:
                logger.error(f"Pandas Excel 파일 파싱 중 오류 발생: {e}")
                raise ValueError("Excel 파일을 파싱할 수 없습니다. 파일이 손상되었거나 형식이 올바르지 않을 수 있습니다.")

            # 초기 진행 상황 보고
            if callable(progress_cb):
                try:
                    progress_cb(2, "parsing_excel")
                except Exception:
                    pass

            required = ["request_id", "title", "content", "assignee", "applied_system"]
            if not all(c in df.columns for c in required):
                missing = [c for c in required if c not in df.columns]
                raise ValueError(f"Excel 파일에 필수 컬럼이 없습니다: {missing}")

            METADATA_COLUMNS = [
                "request_id",
                "request_group_id",
                "request_type",
                "title",
                "request_status",
                "applied_system",
                "applied_date",
                "requesters_parent_department",
                "requesters_department",
                "requester",
                "requester_employee_id",
                "assignees_parent_department",
                "assignees_department",
                "assignee",
                "assignee_employee_id",
                "registration_date",
            ]

            base_texts: List[str] = []
            base_metadatas: List[Dict[str, Any]] = []
            for _, row in df.iterrows():
                title = str(row.get("title", "") or "")
                raw_content = str(row.get("content", "") or "")
                sanitized_content = TokenUtils.sanitize_text_basic(raw_content)
                base_texts.append(f"요청 제목: {title}\n요청 내용: {sanitized_content}")

                md: Dict[str, Any] = {"source": "itsd_xlsx"}
                for col in METADATA_COLUMNS:
                    if col in df.columns and pd.notna(row[col]):
                        md[col] = str(row[col])
                meta_combined = dict(md)
                meta_combined["itsd_field"] = "combined"
                base_metadatas.append(meta_combined)

            candidate_chunk_sizes = [256, 384, 512]
            candidate_overlaps = [50, 80, 100]
            target_avg_tokens = float(os.getenv("OPENAI_EMBED_TARGET_CHUNK_TOKENS", "350"))
            best_cs, best_ov = TokenUtils.choose_split_params(
                base_texts[: min(20, len(base_texts))],
                candidate_chunk_sizes,
                candidate_overlaps,
                target_avg_tokens,
            )

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=best_cs, chunk_overlap=best_ov, length_function=len
            )

            texts_to_embed: List[str] = []
            metadatas: List[Dict[str, Any]] = []
            stats = {"title": 0, "content": 0, "combined": 0}

            include_combined = str(os.getenv("ITSD_EMBED_INCLUDE_COMBINED", "false")).lower() in ("1", "true", "yes")
            include_title = str(os.getenv("ITSD_EMBED_INCLUDE_TITLE", "true")).lower() in ("1", "true", "yes")
            include_content = str(os.getenv("ITSD_EMBED_INCLUDE_CONTENT", "true")).lower() in ("1", "true", "yes")

            if include_combined:
                for base_text, base_meta in zip(base_texts, base_metadatas):
                    chunks = splitter.split_text(base_text)
                    total = len(chunks)
                    for idx, chunk in enumerate(chunks):
                        meta = dict(base_meta)
                        meta["chunk_index"] = idx
                        meta["total_chunks"] = total
                        texts_to_embed.append(chunk)
                        metadatas.append(meta)
                        stats["combined"] += 1

            for _, row in df.iterrows():
                title = str(row.get("title", "") or "")
                raw_content = str(row.get("content", "") or "")
                sanitized_content = TokenUtils.sanitize_text_basic(raw_content)

                base_meta: Dict[str, Any] = {"source": "itsd_xlsx"}
                for col in METADATA_COLUMNS:
                    if col in df.columns and pd.notna(row[col]):
                        base_meta[col] = str(row[col])

                if include_title and title:
                    meta_title = dict(base_meta)
                    meta_title["itsd_field"] = "title"
                    meta_title["chunk_index"] = 0
                    meta_title["total_chunks"] = 1
                    texts_to_embed.append(title)
                    metadatas.append(meta_title)
                    stats["title"] += 1

                if include_content and sanitized_content:
                    content_chunks = splitter.split_text(sanitized_content)
                    total_c = len(content_chunks)
                    for cidx, cchunk in enumerate(content_chunks):
                        meta_content = dict(base_meta)
                        meta_content["itsd_field"] = "content"
                        meta_content["chunk_index"] = cidx
                        meta_content["total_chunks"] = total_c
                        texts_to_embed.append(cchunk)
                        metadatas.append(meta_content)
                        stats["content"] += 1

            # 분할 완료 보고
            if callable(progress_cb):
                try:
                    progress_cb(10, "preparing_documents")
                except Exception:
                    pass

            self.embed_and_store(
                texts_to_embed,
                metadatas,
                group_name="itsd_requests",
                replace_by_request_id=True,
                progress_cb=progress_cb,
            )
            logger.info(
                f"Embedded {len(texts_to_embed)} chunks to group 'itsd_requests' "
                f"(chunk_size={best_cs}, overlap={best_ov}), breakdown: "
                f"title={stats['title']}, content={stats['content']}, combined={stats['combined']}"
            )
            return len(texts_to_embed)
        except Exception:
            logger.exception("ITSD Excel embedding failed")
            raise

    def get_itsd_index_stats(self) -> Dict[str, Any]:
        """Return quick stats of ITSD index by field.

        Helps verify that dual indexing exists (title/content docs present).
        """
        try:
            col = getattr(self.vectorstore, "_collection", None)
            if col is None:
                return {"error": "No collection bound"}

            def _count(where: Dict[str, Any]) -> int:
                """Count documents matching a filter with robust fallbacks.

                1) Prefer server-side `count(where=...)` if supported.
                2) Fallback to paged `get(where=..., include=['ids'], limit, offset)` and sum page sizes.
                3) Last resort: single `get(where=..., include=['ids'])` and len(ids).
                Returns -1 only if all strategies fail.
                """
                # 1) Try native count(where=...)
                try:
                    return int(col.count(where=where))  # type: ignore[arg-type]
                except Exception:
                    pass
                # 2) Bulk single-shot fallback (large limit)
                try:
                    bulk_limit = max(1000, int(os.getenv("ITSD_COUNT_BULK_LIMIT", "200000")))
                    res_bulk = col.get(where=where, include=["metadatas"], limit=bulk_limit)  # type: ignore[arg-type]
                    if isinstance(res_bulk, dict):
                        ids_b = res_bulk.get("ids", []) or []
                        if isinstance(ids_b, list):
                            return len(ids_b)
                except Exception as be:
                    logger.debug(f"Bulk count fallback failed for where={where}: {be}")
                # 3) Paged fallback with client-side filtering (no server-side where)
                try:
                    page_size = max(1, int(os.getenv("ITSD_COUNT_PAGE_SIZE", "1000")))
                    max_pages = max(1, int(os.getenv("ITSD_COUNT_MAX_PAGES", "2000")))
                    total = 0
                    offset = 0
                    for _ in range(max_pages):
                        res = col.get(  # type: ignore[arg-type]
                            include=["metadatas"],
                            limit=page_size,
                            offset=offset,
                        )
                        if not isinstance(res, dict):
                            break
                        metas = res.get("metadatas", []) or []
                        if not metas:
                            break
                        for m in metas:
                            if isinstance(m, dict) and all(m.get(k) == v for k, v in where.items()):
                                total += 1
                        if len(metas) < page_size:
                            break
                        offset += page_size
                    return total
                except Exception as pe:
                    logger.debug(f"Paged count fallback failed for where={where}: {pe}")
                # 4) Last single-shot fallback
                try:
                    res2 = col.get(where=where, include=["metadatas"])  # type: ignore[arg-type]
                    if isinstance(res2, dict):
                        return len(res2.get("ids", []) or [])
                except Exception:
                    pass
                return -1

            # Collection-wide total (no filter)
            try:
                collection_total = int(col.count())
            except Exception:
                try:
                    r_all = col.get(include=["ids"])  # type: ignore[arg-type]
                    collection_total = len(r_all.get("ids", []) or []) if isinstance(r_all, dict) else -1
                except Exception:
                    collection_total = -1

            base = {"group_name": "itsd_requests"}
            total = _count(base)
            title = _count({**base, "itsd_field": "title"})
            content = _count({**base, "itsd_field": "content"})
            combined = _count({**base, "itsd_field": "combined"})

            # Sample one per field (metadata only)
            def _sample(where: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                # Try server-side filter; if not supported, filter client-side
                try:
                    r = col.get(where=where, limit=1, include=["metadatas"])  # type: ignore[arg-type]
                    metas = r.get("metadatas", []) if isinstance(r, dict) else []
                    return metas[0] if metas else None
                except Exception:
                    pass
                try:
                    r = col.get(limit=50, include=["metadatas"])  # type: ignore[arg-type]
                    if isinstance(r, dict):
                        for m in r.get("metadatas", []) or []:
                            if isinstance(m, dict) and all(m.get(k) == v for k, v in where.items()):
                                return m
                except Exception:
                    pass
                return None

            samples = {
                "title": _sample({**base, "itsd_field": "title"}),
                "content": _sample({**base, "itsd_field": "content"}),
                "combined": _sample({**base, "itsd_field": "combined"}),
            }

            out = {
                "group": "itsd_requests",
                "counts": {
                    "collection_total": collection_total,
                    "total": total,
                    "title": title,
                    "content": content,
                    "combined": combined,
                },
                "samples": samples,
            }
            return out
        except Exception as e:
            logger.error(f"get_itsd_index_stats failed: {e}")
            return {"error": str(e)}

    def _get_collection_embedding_dim(self, where: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Best-effort read of an embedding vector length from the collection.

        Returns None if unavailable (e.g., server disabled embedding return).
        """
        try:
            col = getattr(self.vectorstore, "_collection", None)
            if col is None:
                return None
            res = col.get(where=where, include=["embeddings"], limit=1)  # type: ignore[arg-type]
            if isinstance(res, dict):
                embs = res.get("embeddings", []) or []
                if embs and isinstance(embs[0], (list, tuple)):
                    return len(embs[0])
        except Exception:
            pass
        return None

    def _get_query_embedding_dim(self) -> Optional[int]:
        try:
            v = self.embeddings.embed_query("ping")
            if isinstance(v, list):
                return len(v)
        except Exception:
            return None
        return None

    def embed_and_store(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        group_name: str,
        replace_by_request_id: bool = False,
        progress_cb=None,
    ) -> List[str]:
        """
        텍스트와 메타데이터를 받아 임베딩하고 벡터 DB에 저장합니다.
        ITSD 요청과 같은 간단한 텍스트 목록을 처리하기 위해 사용됩니다.
        """
        if len(texts) != len(metadatas):
            raise ValueError("Texts and metadatas must have the same length.")

        # 선택적으로 동일 request_id 문서를 미리 삭제하여 upsert 효과 제공
        if replace_by_request_id:
            try:
                request_ids = sorted({
                    str(m.get("request_id"))
                    for m in metadatas
                    if isinstance(m, dict) and m.get("request_id") is not None
                })
                if request_ids:
                    collection = getattr(self.vectorstore, "_collection", None)
                    if collection is not None:
                        for rid in request_ids:
                            try:
                                collection.delete(where={"group_name": group_name, "request_id": rid})
                                logger.info(f"Deleted existing documents for request_id={rid} in group={group_name}")
                            except Exception as de:
                                logger.warning(f"Failed to delete existing docs for request_id={rid}: {de}")
            except Exception as e:
                logger.warning(f"Pre-delete step failed (replace_by_request_id): {e}")

        documents: List[Document] = []
        for i, text in enumerate(texts):
            # --- Sanitize content and metadata ---
            def _sanitize(val: str) -> str:
                # Remove carriage returns and normalize all whitespace to single spaces
                if not isinstance(val, str):
                    return val
                # 1) Remove actual control chars
                val = val.replace("\r", " ")
                val = val.replace("\u000d", " ")
                # 2) Remove Excel escape tokens like _x000D_, _x000A_, etc.
                #    Excel uses pattern _xHHHH_ to encode control chars.
                val = re.sub(r"_x[0-9A-Fa-f]{4}_", " ", val)
                # Replace newlines and tabs with spaces and collapse multiple spaces
                val = re.sub(r"[\n\t]+", " ", val)
                val = re.sub(r"\s+", " ", val).strip()
                return val

            safe_text = _sanitize(text)

            metadata = metadatas[i] if isinstance(metadatas[i], dict) else {}
            # Sanitize string metadata values to avoid CR characters stored in DB
            for k, v in list(metadata.items()):
                if isinstance(v, str):
                    metadata[k] = _sanitize(v)
            metadata['group_name'] = group_name
            doc = Document(page_content=safe_text, metadata=metadata)
            documents.append(doc)

        if not documents:
            logger.warning(f"No documents to store for group: {group_name}")
            return []

        try:
            # 1) 단일 문서 토큰 가드: 필요 시 문서 단위 추가 분할
            guarded_docs: List[Document] = []
            for d in documents:
                guarded_docs.extend(self._split_document_if_needed(d))

            # 2) 요청당 토큰 예산으로 배치 분할
            total_ids: List[str] = []
            batches = self._batch_by_token_budget(guarded_docs)
            logger.info(
                f"Embedding {len(guarded_docs)} docs for group {group_name} in {len(batches)} batch(es)"
            )
            total_docs = len(guarded_docs)
            processed_docs = 0
            if callable(progress_cb):
                try:
                    progress_cb(15, "embedding_started")
                except Exception:
                    pass

            def _doc_id(d: Document) -> Optional[str]:
                """문서 청크별로 안정적이고 유일한 ID를 생성합니다.

                포맷: `itsd:{request_id}:{itsd_field}:{chunk_index}[:{sub_chunk_index}]`
                - `itsd_field`: `title | content | combined` (기본값: `combined`)
                - `chunk_index`: 1차 청크 분할 인덱스(제목은 항상 0, 총 1개)
                - `sub_chunk_index`: 토큰 가드에 의해 2차로 추가 분할된 경우에만 추가됨

                비고:
                - `request_id` 및 `chunk_index`가 없으면 명시적 ID를 부여하지 않습니다(Chroma 자동 ID 사용).
                - 현재 ITSD는 단일 그룹(`itsd_requests`)을 사용하므로 `group_name`은 ID에 포함하지 않습니다.
                  복수 그룹을 동시에 운용할 경우에는 충돌 방지를 위해 ID에 그룹명을 포함하는 확장을 고려할 수 있습니다.
                """
                try:
                    md = d.metadata or {}
                    rid = md.get("request_id")
                    cidx = md.get("chunk_index")
                    if rid is None or cidx is None:
                        return None
                    field = str(md.get("itsd_field", "combined"))
                    rid_s = str(rid)
                    cidx_i = int(cidx)
                    sub = md.get("sub_chunk_index")
                    if sub is not None:
                        sub_i = int(sub)
                        return f"itsd:{rid_s}:{field}:{cidx_i}:{sub_i}"
                    return f"itsd:{rid_s}:{field}:{cidx_i}"
                except Exception:
                    return None

            # 3) Chroma 서버로의 단일 add 요청 크기를 추가로 제한하여 413(too large) 방지
            #    환경변수 CHROMA_ADD_MAX_DOCS 로 제어(기본 64)
            try:
                chroma_add_max_docs = int(os.getenv("CHROMA_ADD_MAX_DOCS", "64"))
            except Exception:
                chroma_add_max_docs = 64
            chroma_add_max_docs = max(1, chroma_add_max_docs)

            for i, batch in enumerate(batches, start=1):
                # 서브 배치로 잘라서 OpenAI 임베딩 호출과 Chroma add 요청의 페이로드를 제한
                for j in range(0, len(batch), chroma_add_max_docs):
                    sub = batch[j : j + chroma_add_max_docs]
                    ids_sub = [_doc_id(d) for d in sub]
                    # ids가 모두 유효할 때만 명시적으로 전달 (부분 None이면 전달하지 않음)
                    if all(x is not None for x in ids_sub):
                        sub_ids = self.vectorstore.add_documents(sub, ids=ids_sub)
                    else:
                        sub_ids = self.vectorstore.add_documents(sub)
                    total_ids.extend(sub_ids)
                    processed_docs += len(sub)
                    if callable(progress_cb) and total_docs > 0:
                        try:
                            # 15%~98% 구간을 실제 처리량에 매핑
                            ratio = processed_docs / total_docs
                            pct = 15 + int(ratio * 83)
                            progress_cb(min(98, max(15, pct)), f"embedding {processed_docs}/{total_docs}")
                        except Exception:
                            pass
                    logger.info(
                        f"Batch {i}/{len(batches)} sub[{j//chroma_add_max_docs+1}]: {len(sub)} docs (cum {len(total_ids)})"
                    )
            return total_ids
        except Exception as e:
            logger.error(f"Failed to embed documents for group {group_name}: {e}")
            raise

    # --- Token utility & batching (moved from base) ---
    def _estimate_tokens(self, text: str) -> int:
        """Shared token estimation (delegates to TokenUtils)."""
        return TokenUtils.estimate_tokens(text or "")

    def _split_document_if_needed(self, doc: Document) -> List[Document]:
        """단일 문서가 토큰 한도를 넘으면 자동으로 더 작은 조각으로 분할합니다."""
        content = doc.page_content or ""
        tokens = self._estimate_tokens(content)
        # 기본 한도: 환경변수에서 설정(EmbeddingService에서 읽음). 0이면 비활성화
        max_tokens_per_doc = getattr(self, "max_tokens_per_doc", 0)
        if max_tokens_per_doc <= 0 or tokens <= max_tokens_per_doc:
            return [doc]
        # 목표 토큰 크기(보수적으로 2000 토큰 또는 문서 한도의 절반)
        target_tokens = max(500, min(2000, max_tokens_per_doc // 2))
        # 대략적 문자 길이로 변환 (4 char ~= 1 token)
        chunk_size_chars = max(500, target_tokens * 4)
        overlap_chars = max(50, int(chunk_size_chars * 0.1))
        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size_chars,
                chunk_overlap=overlap_chars,
                length_function=len,
            )
            parts = splitter.split_text(content)
        except Exception:
            # 실패 시 단순 슬라이싱
            parts = [content[i:i+chunk_size_chars] for i in range(0, len(content), chunk_size_chars)]
        sub_docs: List[Document] = []
        total = len(parts)
        for idx, part in enumerate(parts):
            md = dict(doc.metadata) if isinstance(doc.metadata, dict) else {}
            md["sub_chunk_index"] = idx
            sub_docs.append(Document(page_content=part, metadata=md))
        return sub_docs

    def _batch_by_token_budget(self, documents: List[Document]) -> List[List[Document]]:
        """문서 목록을 OpenAI 임베딩 API 토큰 제한에 맞춰 배치로 분할합니다."""
        batches: List[List[Document]] = []
        current: List[Document] = []
        current_tokens = 0
        max_tokens_per_request = getattr(self, "max_tokens_per_request", 250000)
        max_docs_per_batch = getattr(self, "max_docs_per_batch", 128)
        for doc in documents:
            tks = self._estimate_tokens(doc.page_content or "")
            # 단일 문서가 예산을 초과하는 경우: 문서 자체가 너무 큼 → 바로 단독 배치로 보냄
            if tks >= max_tokens_per_request:
                if current:
                    batches.append(current)
                    current = []
                    current_tokens = 0
                batches.append([doc])
                continue
            # 현재 배치에 추가했을 때 예산 초과 or 최대 문서 수 초과하면 새 배치 시작
            over_token_budget = current_tokens + tks > max_tokens_per_request
            over_doc_limit = max_docs_per_batch > 0 and len(current) >= max_docs_per_batch
            if over_token_budget or over_doc_limit:
                if current:
                    batches.append(current)
                current = [doc]
                current_tokens = tks
            else:
                current.append(doc)
                current_tokens += tks
        if current:
            batches.append(current)
        return batches

    async def search_similar_itsd_requests(self, query: str, k: int = 5) -> List[Dict]:
        """
        ITSD 전용 유사도 검색(부모 검색 로직에 의존하지 않음).

        - 항상 group_name = 'itsd_requests' 필터 적용
        - Chroma distance → similarity(0~1) 정규화
        - LLM 리랭크(옵션): DISABLE_RERANK=true 시 비활성화
        - 반환 형식: [{content, metadata, original_score(similarity), rerank_score?}]
        """
        try:
            # Optional: quick dimension sanity check (helps diagnose silent empty results)
            try:
                dim_col = self._get_collection_embedding_dim(where={"group_name": "itsd_requests"})
                dim_q = self._get_query_embedding_dim()
                if dim_col and dim_q and dim_col != dim_q:
                    logger.error(
                        f"Embedding dimension mismatch: collection={dim_col}, query={dim_q}. "
                        f"Check OPENAI_EMBEDDING_MODEL_NAME and re-embed to match."
                    )
            except Exception:
                pass
            # 1) 초기 검색 풀 확장(k*5 기본, 상한 옵션)
            try:
                initial_pool_cap = int(os.getenv("INITIAL_RERANK_POOL", "0"))
            except Exception:
                initial_pool_cap = 0
            initial_k = max(k * 5, k)
            if initial_pool_cap > 0:
                initial_k = min(initial_k, initial_pool_cap)

            # 2) 그룹 필터로 검색
            filter_md = {"group_name": "itsd_requests"}
            results = self.vectorstore.similarity_search_with_score(query, k=initial_k, filter=filter_md)
            if not results:
                return []

            # 3) distance → similarity 변환 (기본 metric=cosine)
            metric = "cosine"
            try:
                col = getattr(self.vectorstore, "_collection", None)
                if col is not None:
                    metric = (getattr(col, "metadata", {}) or {}).get("hnsw:space", "cosine")
            except Exception:
                pass

            def to_similarity(score: float) -> float:
                try:
                    s = float(score)
                except Exception:
                    return 0.0
                m = (metric or "cosine").lower()
                if m == "cosine":
                    return max(0.0, min(1.0, 1.0 - s))
                return 1.0 / (1.0 + max(0.0, s))

            docs: List[Dict[str, Any]] = []
            for i, (doc, dist) in enumerate(results):
                docs.append({
                    "index": i,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "original_score": to_similarity(dist),
                })

            # 4) 리랭크 토글 (환경변수)
            disable_rerank = str(os.getenv("DISABLE_RERANK", "false")).lower() in ("1", "true", "yes")
            if disable_rerank:
                docs.sort(key=lambda x: x["original_score"], reverse=True)
                return docs[:k]

            # 5) LLM 기반 리랭킹 — 배치 토큰 예산
            def _estimate_tokens(txt: str) -> int:
                return TokenUtils.estimate_tokens(txt or "")

            try:
                batch_budget = int(os.getenv("RERANK_BATCH_TOKEN_BUDGET", "12000"))
            except Exception:
                batch_budget = 12000

            batches: List[List[Dict[str, Any]]] = []
            current: List[Dict[str, Any]] = []
            current_tokens = 0
            for item in docs:
                import json as _json
                tks = _estimate_tokens(_json.dumps({"content": item["content"]}, ensure_ascii=False))
                if tks >= batch_budget:
                    if current:
                        batches.append(current)
                        current = []
                        current_tokens = 0
                    batches.append([item])
                    continue
                if current_tokens + tks > batch_budget and current:
                    batches.append(current)
                    current = [item]
                    current_tokens = tks
                else:
                    current.append(item)
                    current_tokens += tks
            if current:
                batches.append(current)

            # 6) 각 배치 리랭크 실행 및 병합
            import json
            reranked: List[Dict[str, Any]] = []
            for batch in batches:
                # 인덱스 → 항목 매핑 준비 (LLM 출력 안전 매칭)
                idx_map = {it["index"]: it for it in batch}
                prompt_messages = [
                    {"role": "system", "content": "You are a helpful assistant that reranks documents based on their relevance to a query. Provide the reranked documents as a JSON array of objects, each with 'index' and 'rerank_score' (a float between 0 and 1)."},
                    {"role": "user", "content": f"Query: {query}\n\nDocuments to rerank (JSON array of objects with 'index' and 'content'):\n{json.dumps([{k: v for k, v in i.items() if k in ('index','content')} for i in batch], ensure_ascii=False, indent=2)}\n\nRerank these documents based on their relevance to the query. Output a JSON array of objects, each with 'index' and 'rerank_score' (a float between 0 and 1)."}
                ]
                try:
                    llm_response = self.llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=prompt_messages,
                        temperature=0.0,
                        max_tokens=1024,
                    )
                    out = llm_response.choices[0].message.content
                    scores = json.loads(out)
                    for s in scores:
                        idx = s.get("index")
                        rr = float(s.get("rerank_score", 0.0) or 0.0)
                        base = idx_map.get(idx)
                        if not base:
                            continue
                        merged = dict(base)
                        merged["rerank_score"] = rr
                        reranked.append(merged)
                except Exception as be:
                    logger.error(f"ITSD rerank batch failed, fallback to original score: {be}")
                    for it in batch:
                        fallback = dict(it)
                        fallback["rerank_score"] = it["original_score"]
                        reranked.append(fallback)

            reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
            return reranked[:k]

        except Exception as e:
            logger.exception(f"Failed to search ITSD similar documents: {e}")
            return []

    async def search_similar_itsd_requests_dual(
        self,
        title: str,
        content: str,
        k: int = 50,
        w_title: float = 0.4,
        w_content: float = 0.6,
        use_rrf: bool = True,
        rrf_k0: int = 60,
        top_k_each: Optional[int] = None,
        cross_encoder_top_n: int = 150,
        cross_encoder_model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        제목과 본문을 분리 검색하고 Late Fusion(RRF) 또는 가중합으로 결합 후 반환합니다.

        - 필드별로 Chroma에서 검색: itsd_field in {'title','content'}
        - 결합 방식: 기본 RRF(k0=60), 비활성화 시 w_title*sim_t + w_content*sim_c
        - 선택적 2차 리랭킹: Cross-encoder(bge-reranker 등) 사용 가능(FlagEmbedding 설치 필요)
        - 최종 반환 항목: [{content, metadata, original_score, rerank_score?}]
        """
        try:
            # 0) 환경변수 오버라이드 적용(명시 인자보다 낮은 우선순위)
            try:
                env_use_rrf = os.getenv("ITSD_FUSION_USE_RRF")
                if env_use_rrf is not None:
                    use_rrf = str(env_use_rrf).strip().lower() in ("1", "true", "yes")
            except Exception:
                pass
            try:
                env_wt = os.getenv("ITSD_FUSION_W_TITLE")
                if env_wt is not None:
                    w_title = float(env_wt)
            except Exception:
                pass
            try:
                env_wc = os.getenv("ITSD_FUSION_W_CONTENT")
                if env_wc is not None:
                    w_content = float(env_wc)
            except Exception:
                pass
            try:
                env_k0 = os.getenv("ITSD_FUSION_RRF_K0")
                if env_k0 is not None:
                    rrf_k0 = int(env_k0)
            except Exception:
                pass
            try:
                env_top_each = os.getenv("ITSD_FUSION_TOP_K_EACH")
                if env_top_each is not None:
                    top_k_each = int(env_top_each)
            except Exception:
                pass

            # 1) 검색 풀 크기 결정
            if top_k_each is None:
                top_k_each = max(k, 50)
            try:
                initial_pool_cap = int(os.getenv("INITIAL_RERANK_POOL", "0"))
            except Exception:
                initial_pool_cap = 0
            k_title = min(top_k_each, initial_pool_cap) if initial_pool_cap > 0 else top_k_each
            k_content = k_title

            # 2) 필드별 검색 (+ 안전 가드)
            filter_title = {"group_name": "itsd_requests", "itsd_field": "title"}
            filter_content = {"group_name": "itsd_requests", "itsd_field": "content"}

            try:
                # Optional dimension sanity check once
                dim_t = self._get_collection_embedding_dim(where=filter_title)
                dim_q = self._get_query_embedding_dim()
                if dim_t and dim_q and dim_t != dim_q:
                    logger.error(
                        f"Embedding dimension mismatch (dual): collection={dim_t}, query={dim_q}. "
                        f"Verify OPENAI_EMBEDDING_MODEL_NAME used for indexing matches runtime."
                    )
            except Exception:
                pass

            try:
                res_t = self.vectorstore.similarity_search_with_score(title, k=k_title, filter=filter_title)
                res_c = self.vectorstore.similarity_search_with_score(content, k=k_content, filter=filter_content)
            except Exception as se:
                logger.exception(f"Chroma similarity search failed (dual fields): {se}")
                # Fallback to legacy combined search to avoid hard zero
                query = f"요청 제목: {title}\n요청 내용: {content}"
                try:
                    legacy = await self.search_similar_itsd_requests(query, k=k)
                    return legacy
                except Exception:
                    raise
            logger.debug(f"ITSD dual-search: title_hits={len(res_t) if res_t else 0}, content_hits={len(res_c) if res_c else 0}")

            # Early fallback: If both empty, try legacy combined/group search to avoid hard zero results
            if (not res_t) and (not res_c):
                try:
                    query = f"요청 제목: {title}\n요청 내용: {content}"
                    legacy = await self.search_similar_itsd_requests(query, k=k)
                    if legacy:
                        logger.debug("ITSD dual-search fallback used: legacy combined/group search returned results")
                        return legacy
                except Exception:
                    pass

            # 3) 점수 정규화 (distance → similarity)
            metric = "cosine"
            try:
                col = getattr(self.vectorstore, "_collection", None)
                if col is not None:
                    metric = (getattr(col, "metadata", {}) or {}).get("hnsw:space", "cosine")
            except Exception:
                pass

            def to_similarity(score: float) -> float:
                try:
                    s = float(score)
                except Exception:
                    return 0.0
                m = (metric or "cosine").lower()
                if m == "cosine":
                    return max(0.0, min(1.0, 1.0 - s))
                return 1.0 / (1.0 + max(0.0, s))

            # 4) request_id 단위로 최대 점수 집계
            from collections import defaultdict
            best_t = defaultdict(float)
            best_c = defaultdict(float)
            # 대표 콘텐츠(최고 점수 청크)도 함께 보관
            rep_t: Dict[str, Dict[str, Any]] = {}
            rep_c: Dict[str, Dict[str, Any]] = {}

            def rid_of(md: Dict[str, Any]) -> str:
                return str((md or {}).get("request_id", ""))

            try:
                for (doc, dist) in res_t or []:
                    sim = to_similarity(dist)
                    md = doc.metadata or {}
                    rid = rid_of(md)
                    if not rid:
                        continue
                    if sim > best_t[rid]:
                        best_t[rid] = sim
                        rep_t[rid] = {
                            "content": doc.page_content,
                            "metadata": md,
                            "original_score": sim,
                        }

                for (doc, dist) in res_c or []:
                    sim = to_similarity(dist)
                    md = doc.metadata or {}
                    rid = rid_of(md)
                    if not rid:
                        continue
                    if sim > best_c[rid]:
                        best_c[rid] = sim
                        rep_c[rid] = {
                            "content": doc.page_content,
                            "metadata": md,
                            "original_score": sim,
                        }
            except Exception as agg_err:
                logger.warning(f"ITSD dual-search aggregation failed: {agg_err}")
                # Extremely defensive fallback: return naive merge of raw hits
                naive: Dict[str, Dict[str, Any]] = {}
                def _add(items):
                    for d, dist in items or []:
                        md = d.metadata or {}
                        rid = rid_of(md)
                        if not rid or rid in naive:
                            continue
                        naive[rid] = {
                            "content": d.page_content,
                            "metadata": md,
                            "original_score": to_similarity(dist),
                            "rerank_score": to_similarity(dist),
                        }
                _add(res_c)
                _add(res_t)
                out = list(naive.values())
                out.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
                return out[:k]

            # 5) 결합 점수 산출
            candidate_ids = set(best_t.keys()) | set(best_c.keys())

            try:
                fused_scores: Dict[str, float] = {}
                if use_rrf:
                    # 타이틀/내용 각각의 rank 산출(내림차순)
                    sorted_t = sorted(best_t.items(), key=lambda x: x[1], reverse=True)
                    sorted_c = sorted(best_c.items(), key=lambda x: x[1], reverse=True)
                    rank_t = {rid: i + 1 for i, (rid, _s) in enumerate(sorted_t)}
                    rank_c = {rid: i + 1 for i, (rid, _s) in enumerate(sorted_c)}
                    from services.itsd_rerankers import rrf_fusion
                    rankings = {}
                    for rid in candidate_ids:
                        ranks = {}
                        if rid in rank_t:
                            ranks["t"] = rank_t[rid]
                        if rid in rank_c:
                            ranks["c"] = rank_c[rid]
                        if ranks:
                            rankings[rid] = ranks
                    fused_scores = rrf_fusion(rankings, k0=rrf_k0)
                else:
                    for rid in candidate_ids:
                        fused_scores[rid] = (w_title * best_t.get(rid, 0.0)) + (w_content * best_c.get(rid, 0.0))
            except Exception as fuse_err:
                logger.warning(f"ITSD dual-search fusion failed, using content/title max: {fuse_err}")
                fused_scores = {rid: max(best_t.get(rid, 0.0), best_c.get(rid, 0.0)) for rid in candidate_ids}

            # 6) 초기 결합 순위 생성
            ranked_ids = sorted(candidate_ids, key=lambda r: fused_scores.get(r, 0.0), reverse=True)
            base_ranked = ranked_ids[: max(k * 3, k)]
            logger.debug(
                f"ITSD dual-search: fused_candidates={len(candidate_ids)}, base_ranked={len(base_ranked)} (k={k})"
            )

            # 7) 크로스 인코더 리랭커(옵션)
            use_cross = str(os.getenv("ENABLE_CROSS_ENCODER_RERANK", "false")).lower() in ("1", "true", "yes")
            final_list: List[Dict[str, Any]] = []
            if use_cross and base_ranked:
                try:
                    from services.itsd_rerankers import CrossEncoderReranker
                    model_name = cross_encoder_model or os.getenv("CROSS_ENCODER_MODEL", "BAAI/bge-reranker-base")
                    reranker = CrossEncoderReranker(model_name=model_name)
                    # 후보 구성: 각 request_id에 대해 대표 텍스트(내용 우선, 없으면 제목)
                    candidates: List[Tuple[str, Dict[str, Any]]] = []
                    for rid in base_ranked[:cross_encoder_top_n]:
                        rep = rep_c.get(rid) or rep_t.get(rid)
                        if not rep:
                            continue
                        candidates.append((rep["content"], rep["metadata"]))
                    # 쿼리는 결합 문자열 사용
                    query = f"요청 제목: {title}\n요청 내용: {content}"
                    scored = reranker.rerank(query=query, docs=candidates, top_n=k)
                    # 스코어 기반 최종 결과 작성
                    rid_seen = set()
                    for text, ce_score, md in scored:
                        rid = str((md or {}).get("request_id", ""))
                        if not rid or rid in rid_seen:
                            continue
                        rid_seen.add(rid)
                        final_list.append({
                            "content": text,
                            "metadata": md,
                            "original_score": max(best_t.get(rid, 0.0), best_c.get(rid, 0.0)),
                            "rerank_score": float(ce_score),
                        })
                except Exception as e:
                    logger.warning(f"Cross-encoder rerank failed; falling back to base fusion: {e}")

            # 8) 크로스 인코더 미사용/실패 시: 결합 점수 순으로 반환
            if not final_list:
                for rid in base_ranked[:k * 2]:
                    rep = rep_c.get(rid) or rep_t.get(rid)
                    if not rep:
                        continue
                    item = dict(rep)
                    item["rerank_score"] = fused_scores.get(rid, 0.0)
                    final_list.append(item)

            # 상위 k개로 제한
            final_list.sort(key=lambda x: x.get("rerank_score", x.get("original_score", 0.0)), reverse=True)
            return final_list[:k]
        except Exception as e:
            logger.exception(f"Dual-field ITSD search failed: {e}")
            return []

    # --- DB viewer helpers (moved/copied for ITSD context) ---
    def get_all_documents(self, group_name: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """DB에 저장된 문서를 페이지별로 반환합니다."""
        try:
            collection = self.vectorstore._collection
            
            where_filter: Dict[str, Any] = {}
            if group_name:
                where_filter = {"group_name": group_name}
            
            results = collection.get(
                where=where_filter if where_filter else None,
                limit=limit,
                offset=offset,
                include=["metadatas", "documents"]
            )
            
            return results
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return {"error": str(e)}

    def delete_documents_by_group(self, group_name: str) -> Dict[str, Any]:
        """주어진 group_name에 해당하는 모든 문서를 삭제합니다."""
        try:
            collection = self.vectorstore._collection
            # 삭제 대상 개수 추정
            results = collection.get(where={"group_name": group_name}, include=["metadatas"])
            to_delete = len(results.get("ids", [])) if isinstance(results, dict) else 0
            collection.delete(where={"group_name": group_name})
            logger.info(f"Deleted {to_delete} documents for group '{group_name}'")
            return {"deleted": to_delete, "group_name": group_name}
        except Exception as e:
            logger.error(f"Failed to delete documents by group '{group_name}': {e}")
            return {"error": str(e)}

    def create_embedding(self, text: str) -> List[float]:
        """
        Generates an embedding for a single text string.
        """
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to create embedding for text: {e}")
            raise

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of text strings.
        """
        try:
            embeddings = self.embeddings.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to create embeddings for texts: {e}")
            raise


# --- Dependency Injection ---
def get_itsd_embedding_service() -> ItsdEmbeddingService:
    return ItsdEmbeddingService()
