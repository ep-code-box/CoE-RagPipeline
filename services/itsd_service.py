import asyncio
import logging
import os
from typing import Dict, Any
from fastapi import Depends
from services.itsd_embedding_service import (
    ItsdEmbeddingService,
    get_itsd_embedding_service,
)
from openai import OpenAI

logger = logging.getLogger(__name__)

# ITSD Excel 컬럼 정의/청크 로직은 임베딩 서비스로 이동했습니다.

class ItsdService:
    """ITSD 관련 데이터 처리 서비스"""

    def __init__(self, embedding_service: ItsdEmbeddingService):
        self.embedding_service = embedding_service
        # LLM 클라이언트 초기화
        # 전역 타임아웃 비적용: 사용자 요구에 따라 기본 동작 유지
        self.llm_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )

    async def embed_itsd_requests_from_path(self, file_path: str, progress_cb=None) -> int:
        """
        지정된 경로의 Excel 파일을 읽어 ITSD 요청 데이터를 임베딩하고 저장합니다.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"지정된 파일을 찾을 수 없습니다: {file_path}")

        with open(file_path, "rb") as f:
            content = f.read()
        return await self.embed_itsd_requests_from_file(content, progress_cb=progress_cb)

    async def embed_itsd_requests_from_file(self, file_content: bytes, progress_cb=None) -> int:
        """
        Excel(.xlsx) 파일 내용을 읽어 ITSD 요청 데이터를 임베딩하고 저장합니다.
        """
        # Run the largely synchronous embedding routine in a worker thread so the
        # event loop remains responsive for status polling and job queuing.
        return await asyncio.to_thread(
            self.embedding_service.embed_itsd_requests_from_excel_bytes,
            file_content,
            progress_cb=progress_cb,
        )

    async def recommend_assignee(
        self,
        title: str,
        description: str,
        top_k: int = 50,
        page: int = 1,
        page_size: int = 5,
        # Optional per-request fusion overrides
        use_rrf: bool | None = None,
        w_title: float | None = None,
        w_content: float | None = None,
        rrf_k0: int | None = None,
        top_k_each: int | None = None,
    ) -> str:
        """새로운 ITSD 요청에 대해 과거 유사 사례를 근거로 담당자를 추천합니다.

        - 기본적으로 유사 사례를 집계해 추천 후보를 산출합니다.
        - LLM에 상세 포맷(마크다운)으로 작성하도록 지시하는 프롬프트를 추가하여 가독성을 높입니다.
        - LLM 호출 실패 시에는 로컬에서 생성한 마크다운을 반환합니다.
        """
        try:
            # 1) 유사 사례 검색: 제목/내용 분리 검색 + Fusion
            # Build fusion kwargs if provided
            fusion_kwargs: Dict[str, Any] = {}
            if use_rrf is not None:
                fusion_kwargs["use_rrf"] = bool(use_rrf)
            if w_title is not None:
                fusion_kwargs["w_title"] = float(w_title)
            if w_content is not None:
                fusion_kwargs["w_content"] = float(w_content)
            if rrf_k0 is not None:
                fusion_kwargs["rrf_k0"] = int(rrf_k0)
            if top_k_each is not None:
                fusion_kwargs["top_k_each"] = int(top_k_each)

            similar_requests = await self.embedding_service.search_similar_itsd_requests_dual(
                title=title,
                content=description,
                k=top_k,
                **fusion_kwargs,
            )

            if not similar_requests:
                return "유사한 과거 ITSD 요청을 찾을 수 없어 담당자를 추천할 수 없습니다. 데이터가 충분히 학습되었는지 확인해주세요."

            # 2) 후보 점수 집계 (담당자별 건수 및 가중치)
            from collections import defaultdict, Counter
            assignee_counts = Counter()
            assignee_scores = defaultdict(float)
            assignee_systems = defaultdict(list)
            by_assignee_examples = defaultdict(list)

            for item in similar_requests:
                md = item.get("metadata", {}) or {}
                assignee = str(md.get("assignee", "미지정"))
                score = float(item.get("rerank_score", item.get("original_score", 0.0)) or 0.0)
                assignee_counts[assignee] += 1
                assignee_scores[assignee] += score
                sys = md.get("applied_system")
                if sys:
                    assignee_systems[assignee].append(str(sys))
                by_assignee_examples[assignee].append(item)

            # 점수 기준: (평균 유사도 우선, 동점 시 건수)
            # avg_score = total_score / count, 안전한 0-division 방지
            assignee_avg = {
                a: (assignee_scores[a] / max(1, assignee_counts[a])) for a in assignee_counts
            }
            ranked_assignees = sorted(
                assignee_counts.keys(),
                key=lambda a: (assignee_avg[a], assignee_counts[a]),
                reverse=True,
            )
            top_assignees = ranked_assignees[:3]

            def fmt(v):
                return v if v is not None else "N/A"

            # 3) 추천 결과 마크다운 구성 (LLM 실패시 사용할 로컬 백업 출력)
            md_lines = []
            md_lines.append("### ITSD 담당자 추천 결과")
            md_lines.append("")
            for idx, a in enumerate(top_assignees, start=1):
                count = assignee_counts[a]
                avg_score = assignee_scores[a] / max(1, count)
                top_systems = ", ".join([s for s, _ in Counter(assignee_systems[a]).most_common(3)]) if assignee_systems[a] else "-"
                md_lines.append(f"**{idx}. {a} (과거 유사 요청 처리: {count}건, 평균 유사도: {avg_score:.3f})**")
                md_lines.append(f"- 주요 시스템 이력: {top_systems}")
                # 사례 전체 요약 (모든 건)
                examples = by_assignee_examples[a]
                for i, ex in enumerate(examples, start=1):
                    m = ex.get("metadata", {}) or {}
                    score = float(ex.get("rerank_score", ex.get("original_score", 0.0)) or 0.0)
                    md_lines.append(
                        f"  - 사례 {i}: [ID {fmt(m.get('request_id'))}] {fmt(m.get('title'))} (시스템: {fmt(m.get('applied_system'))}, 유형: {fmt(m.get('request_type'))}, 유사도: {score:.3f})"
                    )
                md_lines.append("")

            # 4) 유사 사례 상세 표 (상위 3명 담당자만, 페이지네이션 없이 전체 표시)
            filtered_reqs = []
            for ex in similar_requests:
                m = ex.get("metadata", {}) or {}
                if str(m.get("assignee", "미지정")) in top_assignees:
                    filtered_reqs.append(ex)

            table_lines = []
            table_lines.append("### 유사 사례 상세 — 상위 3명 담당자")
            table_lines.append("| ID | 제목 | 시스템 | 유형 | 담당자 | 유사도 |")
            table_lines.append("|---:|---|---|---|---|---:|")
            for ex in filtered_reqs:
                m = ex.get("metadata", {}) or {}
                score = float(ex.get("rerank_score", ex.get("original_score", 0.0)) or 0.0)
                # 파이프 이스케이프: 값 내 '|'는 '／'로 대체해 테이블 파손 방지
                def esc(v: str) -> str:
                    return (v or "").replace("|", "／")
                table_lines.append(
                    f"| {esc(fmt(m.get('request_id')))} | {esc(fmt(m.get('title')))} | {esc(fmt(m.get('applied_system')))} | {esc(fmt(m.get('request_type')))} | {esc(fmt(m.get('assignee')))} | {score:.3f} |"
                )

            # 로컬 백업 출력에는 표를 그대로 포함
            md_lines.extend(table_lines)

            # 5) 배정 가이드
            md_lines.append("")
            md_lines.append("> 배정 가이드: 위 추천 순서대로 검토 후 1순위 담당자에게 배정하시고, 부재/부적합 시 다음 순위로 이관하세요.")

            local_fallback_md = "\n".join(md_lines)

            # 4) LLM 프롬프트 구성 및 호출 (항상 LLM 포맷팅 사용)
            try:
                # 준비된 데이터(JSON)를 LLM에 전달해 보기 좋은 마크다운으로 정리하도록 요청
                from collections import Counter
                def safe(v):
                    return v if v is not None else "N/A"

                # LLM에 전달하는 예시는 담당자별 상위 N개로 제한하여 프롬프트 크기 제어(기본 5)
                try:
                    # 0 이면 모든 사례 사용(정확도 우선). 필요 시 환경변수로 제한 가능
                    max_examples_per_assignee = int(os.getenv("LLM_MAX_EXAMPLES_PER_ASSIGNEE", "0"))
                except Exception:
                    max_examples_per_assignee = 0

                candidates_payload = []
                for a in top_assignees:
                    count = assignee_counts[a]
                    avg_score = assignee_scores[a] / max(1, count)
                    systems = [s for s, _ in Counter(assignee_systems[a]).most_common(5)] if assignee_systems[a] else []

                    # 점수 기준 상위 N개 선택
                    sorted_examples = sorted(
                        by_assignee_examples[a],
                        key=lambda ex: float(ex.get("rerank_score", ex.get("original_score", 0.0)) or 0.0),
                        reverse=True,
                    )
                    limited = sorted_examples[:max_examples_per_assignee] if max_examples_per_assignee > 0 else sorted_examples

                    examples = []
                    for ex in limited:
                        m = ex.get("metadata", {}) or {}
                        examples.append({
                            "request_id": safe(m.get('request_id')),
                            "title": safe(m.get('title')),
                            "applied_system": safe(m.get('applied_system')),
                            "request_type": safe(m.get('request_type')),
                            "assignee": safe(m.get('assignee')),
                            "score": float(ex.get("rerank_score", ex.get("original_score", 0.0)) or 0.0),
                        })
                    candidates_payload.append({
                        "assignee": a,
                        "count": count,
                        "avg_score": round(avg_score, 4),
                        "top_systems": systems,
                        "examples": examples,
                    })

                examples_table = []
                for ex in similar_requests[:5]:
                    m = ex.get("metadata", {}) or {}
                    score = float(ex.get("rerank_score", ex.get("original_score", 0.0)) or 0.0)
                    examples_table.append({
                        "request_id": safe(m.get('request_id')),
                        "title": safe(m.get('title')),
                        "applied_system": safe(m.get('applied_system')),
                        "request_type": safe(m.get('request_type')),
                        "assignee": safe(m.get('assignee')),
                        "score": round(score, 4),
                    })

                payload = {
                    "new_request": {"title": title, "description": description},
                    "candidates": candidates_payload,
                    "top_examples": examples_table,
                }

                system_msg = (
                    "You are an expert IT service desk assignment assistant. "
                    "Write a concise, actionable recommendation in Markdown for operators to assign immediately. "
                    "Only use the provided data; do not invent people or facts."
                )
                user_msg = (
                    "Generate a Korean report with the following sections in Markdown:\n"
                    "1) 제목: 'ITSD 담당자 추천 결과'\n"
                    "2) 상위 3명 추천: 각 항목에 '이름, 과거 유사 처리 건수, 평균 유사도, 주요 시스템 이력(최대 3개), 사례 전체 요약(모든 건, 각 사례에 유사도 표시)' 포함\n"
                    "3) 유사 사례 상세 표는 렌더링하지 마세요. 아래에서 별도로 제공됩니다.\n"
                    "4) 배정 가이드: 1순위 우선 배정 후 부재/부적합 시 다음 순위로 이관 안내\n"
                    "형식 규칙: 굵은 텍스트, 리스트, 표를 활용하되 과도하게 길지 않게. 수치는 소수 3자리까지.\n"
                    f"데이터(JSON):\n{payload}"
                )

                resp = self.llm_client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                )
                llm_text = resp.choices[0].message.content
                # LLM 결과 뒤에 우리가 생성한 표를 덧붙여 일관된 테이블을 보장
                table_md = "\n".join(table_lines)
                return f"{llm_text}\n\n{table_md}"
            except Exception as llm_err:
                logger.warning(f"LLM formatting failed, using local fallback: {llm_err}")
                return local_fallback_md

        except Exception as e:
            logger.error(f"담당자 추천 중 오류 발생: {e}")
            raise

    

def get_itsd_service(
    embedding_service: ItsdEmbeddingService = Depends(get_itsd_embedding_service),
) -> ItsdService:
    return ItsdService(embedding_service)
