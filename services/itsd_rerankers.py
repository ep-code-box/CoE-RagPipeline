import logging
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)


def rrf_fusion(
    rankings: Dict[str, Dict[str, int]],
    k0: int = 60,
) -> Dict[str, float]:
    """
    Reciprocal Rank Fusion.

    Args:
        rankings: {request_id: {list_name: rank (1-based)}}
        k0: stabilization constant (commonly 60)

    Returns:
        {request_id: fused_score}
    """
    fused: Dict[str, float] = {}
    for rid, ranks in rankings.items():
        score = 0.0
        for r in ranks.values():
            score += 1.0 / (k0 + max(1, int(r)))
        fused[rid] = score
    return fused


class CrossEncoderReranker:
    """Optional cross-encoder reranker (e.g., BAAI/bge-reranker-*)

    Tries to use FlagEmbedding if installed. Falls back gracefully if not.
    """

    def __init__(self, model_name: Optional[str] = None, use_fp16: bool = True):
        self.available = False
        self.model = None
        self.model_name = model_name or "BAAI/bge-reranker-base"
        try:
            from FlagEmbedding import FlagReranker  # type: ignore

            self.model = FlagReranker(self.model_name, use_fp16=use_fp16)
            self.available = True
            logger.info(f"CrossEncoderReranker loaded: {self.model_name}")
        except Exception as e:
            logger.warning(
                f"CrossEncoderReranker unavailable (install FlagEmbedding). Falling back to base ranking. Reason: {e}"
            )

    def rerank(
        self,
        query: str,
        docs: List[Tuple[str, Dict[str, Any]]],
        top_n: int = 50,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Rerank candidate docs.

        Args:
            query: user query
            docs: list of tuples (text, metadata)
            top_n: number of items to return

        Returns:
            list of (doc_text, score, metadata) sorted by score desc
        """
        if not self.available or not self.model:
            # Fallback: no reranking, assign zero delta
            return [(t, 0.0, md) for (t, md) in docs[:top_n]]

        try:
            pairs = [[query, t] for (t, _md) in docs]
            scores = self.model.compute_score(pairs)
            # If single float is returned for single item, normalize to list
            if isinstance(scores, float):
                scores = [scores]
            scored: List[Tuple[str, float, Dict[str, Any]]] = []
            for (text, md), sc in zip(docs, scores):
                try:
                    s = float(sc)
                except Exception:
                    s = 0.0
                scored.append((text, s, md))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_n]
        except Exception as e:
            logger.error(f"CrossEncoderReranker failed: {e}")
            return [(t, 0.0, md) for (t, md) in docs[:top_n]]

