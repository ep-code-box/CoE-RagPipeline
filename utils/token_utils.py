import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenChunk:
    """토큰 청크 데이터 클래스"""
    content: str
    estimated_tokens: int
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any] = None


class TokenUtils:
    """토큰 계산 및 청킹을 위한 유틸리티 클래스"""
    
    # GPT 모델별 토큰 제한 (입력 + 출력) - 보수적으로 설정
    MODEL_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        # SKAX 모델들 - 실제 한계보다 낮게 설정하여 안전 마진 확보
        "SKAX-O1-Preview": 120000,  # 131072에서 안전 마진 적용
        "SKAX-O1-Mini": 120000,
        "SKAX-4O": 120000,
        "SKAX-4O-Mini": 120000,
    }
    
    def __init__(self):
        """토큰 유틸리티 초기화"""
        pass
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        텍스트의 토큰 수를 추정합니다.
        
        GPT 토크나이저의 정확한 계산은 아니지만, 
        실용적인 추정치를 제공합니다. 보수적으로 추정하여 안전 마진을 확보합니다.
        
        Args:
            text: 토큰 수를 계산할 텍스트
            
        Returns:
            추정된 토큰 수 (보수적으로 높게 추정)
        """
        if not text:
            return 0
            
        # 기본적인 토큰 추정 로직
        # 1. 공백으로 분할된 단어 수
        words = len(text.split())
        
        # 2. 문자 수 기반 추정 (영어: ~4자/토큰, 한국어: ~2자/토큰)
        char_count = len(text)
        
        # 3. 특수 문자 및 구두점 고려
        special_chars = len(re.findall(r'[^\w\s]', text))
        
        # 4. 코드 블록 및 JSON 구조 고려
        code_blocks = len(re.findall(r'```[\s\S]*?```', text))
        json_structures = len(re.findall(r'[{}\[\]]', text))
        
        # 5. 한국어 문자 비율 계산
        korean_chars = len(re.findall(r'[가-힣]', text))
        korean_ratio = korean_chars / char_count if char_count > 0 else 0
        
        # 추정 공식 (보수적으로 높게 추정)
        base_estimates = [
            words * 1.5,  # 단어 기반 추정 (더 보수적)
            char_count / (2.5 if korean_ratio > 0.3 else 3.2),  # 한국어 고려한 문자 기반 추정
            (char_count + special_chars * 3 + code_blocks * 15 + json_structures * 2) / 3.5
        ]
        
        estimated_tokens = max(base_estimates)
        
        # 안전 마진 추가 (20% 더 높게 추정)
        estimated_tokens = int(estimated_tokens * 1.2)
        
        return estimated_tokens
    
    @staticmethod
    def get_model_limit(model_name: str, reserve_for_completion: int = 4000) -> int:
        """
        모델의 입력 토큰 제한을 반환합니다.
        
        Args:
            model_name: 모델 이름
            reserve_for_completion: 응답을 위해 예약할 토큰 수
            
        Returns:
            입력에 사용 가능한 최대 토큰 수
        """
        total_limit = TokenUtils.MODEL_LIMITS.get(model_name, 4096)
        # 추가 안전 마진 적용 (시스템 프롬프트, 메타데이터 등을 위해)
        safety_margin = 2000
        usable_limit = total_limit - reserve_for_completion - safety_margin
        return max(usable_limit, 1000)
    
    @staticmethod
    def chunk_text(
        text: str, 
        max_tokens_per_chunk: int = 8000,
        overlap_tokens: int = 200,
        preserve_structure: bool = True
    ) -> List[TokenChunk]:
        """
        텍스트를 토큰 제한에 맞게 청크로 분할합니다.
        
        Args:
            text: 분할할 텍스트
            max_tokens_per_chunk: 청크당 최대 토큰 수
            overlap_tokens: 청크 간 겹치는 토큰 수
            preserve_structure: 구조 보존 여부 (문단, 코드 블록 등)
            
        Returns:
            TokenChunk 객체들의 리스트
        """
        if not text:
            return []
        
        total_tokens = TokenUtils.estimate_tokens(text)
        
        # 텍스트가 충분히 작으면 분할하지 않음
        if total_tokens <= max_tokens_per_chunk:
            return [TokenChunk(
                content=text,
                estimated_tokens=total_tokens,
                chunk_index=0,
                total_chunks=1,
                metadata={"original_length": len(text)}
            )]
        
        chunks = []
        
        if preserve_structure:
            # 구조를 보존하면서 분할
            chunks = TokenUtils._chunk_with_structure_preservation(
                text, max_tokens_per_chunk, overlap_tokens
            )
        else:
            # 단순 분할
            chunks = TokenUtils._chunk_simple(
                text, max_tokens_per_chunk, overlap_tokens
            )
        
        # 청크 인덱스 및 총 개수 설정
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total_chunks
            if not chunk.metadata:
                chunk.metadata = {}
            chunk.metadata.update({
                "original_length": len(text),
                "original_tokens": total_tokens
            })
        
        logger.info(f"Text chunked into {total_chunks} chunks "
                   f"(original: {total_tokens} tokens)")
        
        return chunks
    
    @staticmethod
    def _chunk_with_structure_preservation(
        text: str, 
        max_tokens_per_chunk: int, 
        overlap_tokens: int
    ) -> List[TokenChunk]:
        """구조를 보존하면서 텍스트를 청크로 분할"""
        chunks = []
        
        # 1. 큰 구조 단위로 먼저 분할 (코드 블록, 섹션 등)
        sections = TokenUtils._split_by_structure(text)
        
        current_chunk = ""
        current_tokens = 0
        
        for section in sections:
            section_tokens = TokenUtils.estimate_tokens(section)
            
            # 섹션이 너무 크면 더 작게 분할
            if section_tokens > max_tokens_per_chunk:
                # 현재 청크가 있으면 저장
                if current_chunk:
                    chunks.append(TokenChunk(
                        content=current_chunk.strip(),
                        estimated_tokens=current_tokens,
                        chunk_index=0,  # 나중에 설정
                        total_chunks=0   # 나중에 설정
                    ))
                    current_chunk = ""
                    current_tokens = 0
                
                # 큰 섹션을 더 작게 분할
                sub_chunks = TokenUtils._split_large_section(section, max_tokens_per_chunk)
                chunks.extend(sub_chunks)
                
            elif current_tokens + section_tokens > max_tokens_per_chunk:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(TokenChunk(
                        content=current_chunk.strip(),
                        estimated_tokens=current_tokens,
                        chunk_index=0,
                        total_chunks=0
                    ))
                
                # 새 청크 시작 (오버랩 고려)
                overlap_content = TokenUtils._get_overlap_content(current_chunk, overlap_tokens)
                current_chunk = overlap_content + section
                current_tokens = TokenUtils.estimate_tokens(current_chunk)
                
            else:
                # 현재 청크에 추가
                current_chunk += section
                current_tokens += section_tokens
        
        # 마지막 청크 저장
        if current_chunk:
            chunks.append(TokenChunk(
                content=current_chunk.strip(),
                estimated_tokens=current_tokens,
                chunk_index=0,
                total_chunks=0
            ))
        
        return chunks
    
    @staticmethod
    def _chunk_simple(
        text: str, 
        max_tokens_per_chunk: int, 
        overlap_tokens: int
    ) -> List[TokenChunk]:
        """단순하게 텍스트를 청크로 분할"""
        chunks = []
        
        # 문자 기반으로 대략적인 청크 크기 계산
        avg_chars_per_token = 3.5
        max_chars_per_chunk = int(max_tokens_per_chunk * avg_chars_per_token)
        overlap_chars = int(overlap_tokens * avg_chars_per_token)
        
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + max_chars_per_chunk, text_length)
            
            # 단어 경계에서 자르기
            if end < text_length:
                # 마지막 공백 찾기
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            chunk_text = text[start:end]
            chunk_tokens = TokenUtils.estimate_tokens(chunk_text)
            
            chunks.append(TokenChunk(
                content=chunk_text,
                estimated_tokens=chunk_tokens,
                chunk_index=0,
                total_chunks=0
            ))
            
            # 다음 청크 시작점 (오버랩 고려)
            start = max(end - overlap_chars, start + 1)
        
        return chunks
    
    @staticmethod
    def _split_by_structure(text: str) -> List[str]:
        """텍스트를 구조적 단위로 분할"""
        sections = []
        
        # 코드 블록 분할
        parts = re.split(r'(```[\s\S]*?```)', text)
        
        for part in parts:
            if not part:
                continue
                
            if part.startswith('```'):
                # 코드 블록은 그대로 유지
                sections.append(part)
            else:
                # 일반 텍스트는 문단으로 분할
                paragraphs = re.split(r'\n\s*\n', part)
                for paragraph in paragraphs:
                    if paragraph.strip():
                        sections.append(paragraph + '\n\n')
        
        return sections
    
    @staticmethod
    def _split_large_section(section: str, max_tokens: int) -> List[TokenChunk]:
        """큰 섹션을 더 작은 청크로 분할"""
        # 문장 단위로 분할
        sentences = re.split(r'(?<=[.!?])\s+', section)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = TokenUtils.estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > max_tokens:
                if current_chunk:
                    chunks.append(TokenChunk(
                        content=current_chunk.strip(),
                        estimated_tokens=current_tokens,
                        chunk_index=0,
                        total_chunks=0
                    ))
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append(TokenChunk(
                content=current_chunk.strip(),
                estimated_tokens=current_tokens,
                chunk_index=0,
                total_chunks=0
            ))
        
        return chunks
    
    @staticmethod
    def _get_overlap_content(text: str, overlap_tokens: int) -> str:
        """텍스트의 끝부분에서 오버랩할 내용 추출"""
        if not text or overlap_tokens <= 0:
            return ""
        
        # 대략적인 문자 수 계산
        overlap_chars = int(overlap_tokens * 3.5)
        
        if len(text) <= overlap_chars:
            return text
        
        # 단어 경계에서 자르기
        start_pos = len(text) - overlap_chars
        space_pos = text.find(' ', start_pos)
        
        if space_pos != -1:
            return text[space_pos:] + "\n\n"
        else:
            return text[-overlap_chars:] + "\n\n"
    
    @staticmethod
    def merge_chunk_results(
        chunk_results: List[Dict[str, Any]], 
        merge_strategy: str = "concatenate"
    ) -> Dict[str, Any]:
        """
        청크별 처리 결과를 병합합니다.
        
        Args:
            chunk_results: 청크별 결과 리스트
            merge_strategy: 병합 전략 ("concatenate", "summarize", "structured")
            
        Returns:
            병합된 결과
        """
        if not chunk_results:
            return {}
        
        if len(chunk_results) == 1:
            return chunk_results[0]
        
        if merge_strategy == "concatenate":
            return TokenUtils._merge_concatenate(chunk_results)
        elif merge_strategy == "summarize":
            return TokenUtils._merge_summarize(chunk_results)
        elif merge_strategy == "structured":
            return TokenUtils._merge_structured(chunk_results)
        else:
            logger.warning(f"Unknown merge strategy: {merge_strategy}, using concatenate")
            return TokenUtils._merge_concatenate(chunk_results)
    
    @staticmethod
    def _merge_concatenate(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """단순 연결 병합"""
        merged = {
            "content": "",
            "chunks_processed": len(chunk_results),
            "total_tokens_used": 0,
            "chunk_details": []
        }
        
        for i, result in enumerate(chunk_results):
            content = result.get("content", "")
            if content:
                merged["content"] += f"\n\n## 청크 {i+1}\n\n{content}"
            
            merged["total_tokens_used"] += result.get("tokens_used", 0)
            merged["chunk_details"].append({
                "chunk_index": i,
                "tokens_used": result.get("tokens_used", 0),
                "success": bool(content)
            })
        
        return merged
    
    @staticmethod
    def _merge_summarize(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """요약 병합 (추후 LLM 기반 구현 가능)"""
        # 현재는 단순 연결과 동일하게 처리
        # 추후 LLM을 사용한 지능적 요약 병합 구현 가능
        return TokenUtils._merge_concatenate(chunk_results)
    
    @staticmethod
    def _merge_structured(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """구조화된 병합"""
        merged = {
            "summary": "",
            "detailed_analysis": [],
            "chunks_processed": len(chunk_results),
            "total_tokens_used": 0
        }
        
        summaries = []
        for i, result in enumerate(chunk_results):
            content = result.get("content", "")
            if content:
                summaries.append(f"청크 {i+1}: {content[:200]}...")
                merged["detailed_analysis"].append({
                    "chunk_index": i,
                    "content": content,
                    "tokens_used": result.get("tokens_used", 0)
                })
            
            merged["total_tokens_used"] += result.get("tokens_used", 0)
        
        merged["summary"] = "\n".join(summaries)
        return merged