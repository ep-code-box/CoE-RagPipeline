import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import HttpUrl
import asyncio

from openai import OpenAI
from config.settings import settings
from utils.token_utils import TokenUtils, TokenChunk
from config.prompts import prompts # Import the prompts dictionary

logger = logging.getLogger(__name__)

# 전역적으로 사용할 수 있는 CustomJSONEncoder 정의
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HttpUrl):
            return str(obj)
        # models.schemas는 필요할 때만 import하여 순환 참조 방지
        from models.schemas import ASTNode
        if isinstance(obj, ASTNode):
            return obj.to_dict()
        return super().default(obj)

def truncate_analysis_data(analysis_data: Dict[str, Any], max_tokens: int = 10000) -> Dict[str, Any]:
    """
    분석 데이터가 너무 클 경우 중요한 부분만 남기고 잘라냅니다.
    """
    try:
        serialized = json.dumps(analysis_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
        estimated_tokens = TokenUtils.estimate_tokens(serialized)
        
        if estimated_tokens <= max_tokens:
            return analysis_data
            
        logger.warning(f"분석 데이터가 너무 큼 ({estimated_tokens} 토큰), 잘라내기 시작)")
        
        truncated_data = {
            "analysis_id": analysis_data.get("analysis_id"),
            "repositories": [],
            "tech_specs": [],
            "ast_analysis": {},
            "code_metrics": analysis_data.get("code_metrics", {})
        }
        
        # Defensively get repositories
        repos_source = analysis_data.get("repositories", [])
        if isinstance(repos_source, list):
            for repo in repos_source[:3]:
                if isinstance(repo, dict):
                    truncated_data["repositories"].append({
                        "url": str(repo.get("url", "Unknown")),
                        "branch": repo.get("branch", "main"),
                        "name": repo.get("name")
                    })
        else:
            logger.warning(f"analysis_data['repositories'] is not a list, but {type(repos_source)}. Skipping.")

        # Defensively get tech_specs
        specs_source = analysis_data.get("tech_specs", [])
        if isinstance(specs_source, list):
            for spec in specs_source[:10]:
                 if isinstance(spec, dict):
                    truncated_data["tech_specs"].append({
                        "name": spec.get("name", "Unknown"),
                        "version": spec.get("version", "Unknown"),
                        "framework": spec.get("framework")
                    })
        else:
            logger.warning(f"analysis_data['tech_specs'] is not a list, but {type(specs_source)}. Skipping.")

        ast_analysis = analysis_data.get("ast_analysis", {})
        if isinstance(ast_analysis, dict):
            for file_path, nodes in list(ast_analysis.items())[:5]:
                if isinstance(nodes, list):
                    truncated_data["ast_analysis"][file_path] = nodes[:5]
        else:
            logger.warning(f"analysis_data['ast_analysis'] is not a dict, but {type(ast_analysis)}. Skipping.")

        truncated_serialized = json.dumps(truncated_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
        final_tokens = TokenUtils.estimate_tokens(truncated_serialized)
        
        logger.info(f"분석 데이터 잘라내기 완료: {estimated_tokens} -> {final_tokens} 토큰")
        
        return truncated_data
        
    except Exception as e:
        logger.error(f"분석 데이터 잘라내기 실패: {e}", exc_info=True) # Add exc_info for more details
        # Return a safe, minimal structure on failure
        return {
            "analysis_id": analysis_data.get("analysis_id"),
            "repositories": [],
            "tech_specs": [],
            "ast_analysis": {},
            "code_metrics": {}
        }


class DocumentType(str, Enum):
    """생성 가능한 문서 타입"""
    DEVELOPMENT_GUIDE = "development_guide"
    API_DOCUMENTATION = "api_documentation"
    ARCHITECTURE_OVERVIEW = "architecture_overview"
    CODE_REVIEW_SUMMARY = "code_review_summary"
    TECHNICAL_SPECIFICATION = "technical_specification"
    DEPLOYMENT_GUIDE = "deployment_guide"
    TROUBLESHOOTING_GUIDE = "troubleshooting_guide"
    ANALYSIS_SUMMARY = "analysis_summary" # Added from prompts.py

class LLMDocumentService:
    """LLM을 활용한 문서 생성 서비스"""
    
    def __init__(self):
        """LLM 서비스 초기화"""
        # SKAX API 클라이언트 초기화
        self.client = OpenAI(
            api_key=settings.SKAX_API_KEY,
            base_url=settings.SKAX_API_BASE
        )
        self.model = settings.SKAX_MODEL_NAME
        # OPEN AI API 클라이언트 초기화
        # self.client = OpenAI(
        #     api_key=settings.OPENAI_API_KEY
        # )
        # self.model = "gpt-4o-mini"

    async def generate_document(
        self,
        analysis_data: Dict[str, Any],
        document_type: DocumentType,
        custom_prompt: Optional[str] = None,
        language: str = "korean",
        enable_chunking: bool = None,
        max_tokens_per_chunk: int = None
    ) -> Dict[str, Any]:
        """
        분석 데이터를 바탕으로 문서를 생성합니다.
        
        Args:
            analysis_data: 분석 결과 데이터
            document_type: 생성할 문서 타입
            custom_prompt: 사용자 정의 프롬프트 (선택사항)
            language: 문서 언어 (korean/english)
            enable_chunking: 청킹 기능 활성화 여부
            max_tokens_per_chunk: 청크당 최대 토큰 수
            
        Returns:
            생성된 문서 정보
        """
        try:
            # 설정에서 기본값 가져오기
            if enable_chunking is None:
                enable_chunking = settings.ENABLE_AUTO_CHUNKING
            if max_tokens_per_chunk is None:
                max_tokens_per_chunk = settings.MAX_TOKENS_PER_CHUNK
            
            # 문서 타입별 프롬프트 생성
            system_prompt = self._get_system_prompt(document_type, language)
            user_prompt = custom_prompt or self._get_user_prompt(document_type, analysis_data, language)
            
            logger.info(f"문서 생성 시작: {document_type}, 언어: {language}")
            
            # 토큰 수 확인 및 청킹 여부 결정
            total_prompt = f"""System: {system_prompt}\n\nUser: {user_prompt}"""
            estimated_tokens = TokenUtils.estimate_tokens(total_prompt)
            model_limit = TokenUtils.get_model_limit(self.model, reserve_for_completion=4000)
            
            logger.info(f"추정 토큰 수: {estimated_tokens}, 모델 제한: {model_limit}")
            
            # 모델 제한의 95%를 기준으로 청킹 여부 결정 (보수적 접근)
            conservative_limit = model_limit * 0.95
            if enable_chunking and estimated_tokens > conservative_limit:

                # 청킹 처리
                logger.info(f"토큰 제한 초과 (보수적 기준 적용), 청킹 처리 시작: {estimated_tokens} > {conservative_limit}")
                result = await self._generate_document_with_chunking(
                    system_prompt, user_prompt, document_type, language, 
                    analysis_data, max_tokens_per_chunk
                )
            else:
                # 일반 처리 - 하지만 여전히 토큰 제한 확인
                if estimated_tokens > model_limit * 0.9:
                    logger.warning(f"토큰 사용량이 높음: {estimated_tokens}/{model_limit}")
                
                result = await self._generate_document_single(
                    system_prompt, user_prompt, document_type, language, analysis_data
                )
            
            logger.info(f"문서 생성 완료: {document_type}, 토큰 사용량: {result.get('tokens_used', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"문서 생성 실패: {document_type}, 오류: {str(e)}")
            # 토큰 제한 오류인 경우 더 작은 청크로 재시도
            if "maximum context length" in str(e).lower() or "token" in str(e).lower():
                logger.warning("토큰 제한 오류 감지, 더 작은 청크로 재시도")
                try:
                    return await self.generate_document(
                        analysis_data, document_type, custom_prompt, language,
                        enable_chunking=True, max_tokens_per_chunk=2000
                    )
                except Exception as retry_e:
                    logger.error(f"재시도도 실패: {str(retry_e)}")
                    raise retry_e
            raise
    
    async def _generate_document_single(
        self,
        system_prompt: str,
        user_prompt: str,
        document_type: DocumentType,
        language: str,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """단일 요청으로 문서 생성"""
        try:
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                timeout=settings.LLM_TIMEOUT_SECONDS
            )
            
            generated_content = response.choices[0].message.content
            
            # 결과 구성
            result = {
                "document_type": document_type,
                "language": language,
                "content": generated_content,
                "generated_at": datetime.now().isoformat(),
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "analysis_id": analysis_data.get("analysis_id"),
                "repositories": [repo.get("url") for repo in analysis_data.get("repositories", [])],
                "chunked": False
            }
            
            return result
            
        except Exception as e:
            logger.error(f"단일 문서 생성 실패: {str(e)}")
            raise
    
    async def _generate_document_with_chunking(
        self,
        system_prompt: str,
        user_prompt: str,
        document_type: DocumentType,
        language: str,
        analysis_data: Dict[str, Any],
        max_tokens_per_chunk: int
    ) -> Dict[str, Any]:
        """청킹을 사용한 문서 생성"""
        try:
            logger.info("청킹 기반 문서 생성 시작")
            
            # 사용자 프롬프트를 청크로 분할
            chunks = TokenUtils.chunk_text(
                user_prompt,
                max_tokens_per_chunk=max_tokens_per_chunk,
                overlap_tokens=200,
                preserve_structure=True
            )
            
            logger.info(f"프롬프트를 {len(chunks)}개 청크로 분할")
            
            # 각 청크에 대해 문서 생성
            chunk_results = []
            total_tokens_used = 0
            
            for i, chunk in enumerate(chunks):
                logger.info(f"청크 {i+1}/{len(chunks)} 처리 중 (토큰: {chunk.estimated_tokens})")
                
                try:
                    # 청크별 시스템 프롬프트 수정
                    chunk_system_prompt = self._get_chunk_system_prompt(
                        system_prompt, document_type, language, chunk, len(chunks)
                    )
                    
                    # API 호출
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": chunk_system_prompt},
                            {"role": "user", "content": chunk.content}
                        ],
                        temperature=0.7,
                        max_tokens=max_tokens_per_chunk
                    )
                    
                    chunk_content = response.choices[0].message.content
                    chunk_tokens = response.usage.total_tokens if response.usage else 0
                    total_tokens_used += chunk_tokens
                    
                    chunk_results.append({
                        "content": chunk_content,
                        "tokens_used": chunk_tokens,
                        "chunk_index": i,
                        "chunk_tokens": chunk.estimated_tokens
                    })
                    
                    logger.info(f"청크 {i+1} 완료, 토큰 사용: {chunk_tokens}")
                    
                    # API 호출 간격 조절 (rate limiting 방지)
                    if i < len(chunks) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"청크 {i+1} 처리 실패: {str(e)}")
                    chunk_results.append({
                        "content": f"[청크 {i+1} 처리 실패: {str(e)}]",
                        "tokens_used": 0,
                        "chunk_index": i,
                        "error": str(e)
                    })
            
            # 청크 결과 병합
            merged_result = TokenUtils.merge_chunk_results(chunk_results, merge_strategy="concatenate")
            
            # 최종 결과 구성
            result = {
                "document_type": document_type,
                "language": language,
                "content": merged_result.get("content", ""),
                "generated_at": datetime.now().isoformat(),
                "model_used": self.model,
                "tokens_used": total_tokens_used,
                "analysis_id": analysis_data.get("analysis_id"),
                "repositories": [repo.get("url") for repo in analysis_data.get("repositories", [])],
                "chunked": True,
                "chunks_processed": len(chunks),
                "chunk_details": merged_result.get("chunk_details", [])
            }
            
            logger.info(f"청킹 기반 문서 생성 완료: {len(chunks)}개 청크, 총 토큰: {total_tokens_used}")
            return result
            
        except Exception as e:
            logger.error(f"청킹 기반 문서 생성 실패: {str(e)}")
            raise
    
    def _get_chunk_system_prompt(
        self,
        original_system_prompt: str,
        document_type: DocumentType,
        language: str,
        chunk: TokenChunk,
        total_chunks: int
    ) -> str:
        """청크별 시스템 프롬프트 생성"""
        # Load from prompts.py
        chunk_instruction_template = prompts["chunk_system_prompts"][language]
        return chunk_instruction_template.format(
            original_system_prompt=original_system_prompt,
            total_chunks=total_chunks,
            chunk_index=chunk.chunk_index + 1 # 0-based to 1-based
        )
    
    def _get_system_prompt(self, document_type: DocumentType, language: str) -> str:
        """문서 타입별 시스템 프롬프트 생성"""
        # Load from prompts.py
        base_prompt = prompts["system_prompts"]["base_prompt"][language]
        type_specific_prompt = prompts["system_prompts"][document_type.value][language]
        return f"{base_prompt} {type_specific_prompt}"
    
    def _get_user_prompt(self, document_type: DocumentType, analysis_data: Dict[str, Any], language: str) -> str:
        """분석 데이터를 바탕으로 사용자 프롬프트 생성"""
        
        # 분석 데이터가 너무 클 경우 잘라내기
        truncated_data = truncate_analysis_data(analysis_data, max_tokens=settings.MAX_ANALYSIS_DATA_TOKENS)
        
        # 잘라낸 분석 데이터에서 주요 정보 추출
        repositories = truncated_data.get("repositories", [])
        tech_specs = truncated_data.get("tech_specs", [])
        ast_analysis = truncated_data.get("ast_analysis", {})
        code_metrics = truncated_data.get("code_metrics", {})
        
        logger.debug(f"Extracted data - repos: {len(repositories)}, tech_specs: {len(tech_specs)}, ast: {len(ast_analysis)}, metrics: {bool(code_metrics)}")
        
        # 기본 정보 구성 (개선된 로직)
        if repositories:
            repo_info = "\n".join([f"- {repo.get('url', 'Unknown')} (브랜치: {repo.get('branch', 'main')})" for repo in repositories])
        else:
            repo_info = "분석된 저장소가 없습니다. 먼저 Git 저장소 분석을 수행해주세요."
        
        # 기술 스택 정보 (개선된 로직)
        if tech_specs:
            tech_info = "\n".join([
                f"- {spec.get('name', 'Unknown')}: {spec.get('version', 'Unknown')}" +
                (f" (프레임워크: {spec.get('framework')})" if spec.get('framework') else "") +
                (f" (의존성: {len(spec.get('dependencies', []))}개)" if spec.get('dependencies') else "")
                for spec in tech_specs
            ])
        else:
            tech_info = "기술 스택 정보가 없습니다. include_tech_spec=true로 분석을 수행해주세요."
        
        # AST 분석 정보 (개선된 로직)
        if ast_analysis:
            total_functions = sum(len(nodes) for nodes in ast_analysis.values() if isinstance(nodes, list))
            file_count = len(ast_analysis)
            ast_info = f"총 {file_count}개 파일에서 {total_functions}개의 함수/클래스 분석됨"
        else:
            ast_info = "AST 분석 정보가 없습니다. include_ast=true로 분석을 수행해주세요."
        
        # 코드 메트릭 정보 (개선된 로직)
        if code_metrics and any(code_metrics.values()):
            metrics_parts = []
            if code_metrics.get('lines_of_code', 0) > 0:
                metrics_parts.append(f"총 코드 라인 수: {code_metrics['lines_of_code']}")
            if code_metrics.get('cyclomatic_complexity'):
                metrics_parts.append(f"순환 복잡도: {code_metrics['cyclomatic_complexity']:.2f}")
            if code_metrics.get('maintainability_index'):
                metrics_parts.append(f"유지보수성 지수: {code_metrics['maintainability_index']:.2f}")
            if code_metrics.get('comment_ratio'):
                metrics_parts.append(f"주석 비율: {code_metrics['comment_ratio']:.2f}%")
            
            metrics_info = ", ".join(metrics_parts) if metrics_parts else "코드 메트릭 데이터가 부족합니다."
        else:
            metrics_info = "코드 메트릭 정보가 없습니다. 분석을 다시 수행해주세요."
        
        # 데이터 유효성 검사
        has_meaningful_data = (
            len(repositories) > 0 or 
            len(tech_specs) > 0 or 
            len(ast_analysis) > 0 or 
            (code_metrics and any(code_metrics.values()))
        )
        
        # 분석 데이터가 있는 경우 기존 로직 사용
        detailed_analysis_json = json.dumps(truncated_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)

        if not has_meaningful_data:
            # Load from prompts.py
            prompt_template = prompts["user_prompts"]["no_data_template"][language]
            return prompt_template.format(
                document_type=document_type.value,
                analysis_id=analysis_data.get('analysis_id', 'Unknown'),
                num_repositories=len(repositories),
                num_tech_specs=len(tech_specs),
                num_ast_files=len(ast_analysis),
                code_metrics_status=('있음' if code_metrics and any(code_metrics.values()) else '없음') if language == 'korean' else ('Available' if code_metrics and any(code_metrics.values()) else 'Not available')
            )
        else:
            # Load from prompts.py
            prompt_template = prompts["user_prompts"]["with_data_template"][language]
            return prompt_template.format(
                document_type=document_type.value,
                repo_info=repo_info,
                tech_info=tech_info,
                ast_info=ast_info,
                metrics_info=metrics_info,
                source_summary_info="",  # Added to prevent KeyError
                key_summaries="",         # Added to prevent KeyError
                detailed_analysis_json=detailed_analysis_json
            )
    
    async def generate_document_with_source_summaries(
        self,
        analysis_data: Dict[str, Any],
        source_summaries: Dict[str, Any],
        document_type: DocumentType,
        custom_prompt: Optional[str] = None,
        language: str = "korean"
    ) -> Dict[str, Any]:
        """
        분석 데이터와 소스코드 요약을 함께 활용하여 문서를 생성합니다.
        내부적으로 청킹 기능이 있는 generate_document를 호출합니다.
        """
        try:
            # 향상된 사용자 프롬프트 생성
            enhanced_user_prompt = self._get_enhanced_user_prompt(
                document_type, analysis_data, source_summaries, language
            )
            
            # 메인 문서 생성 메서드 호출 (청킹 기능 내장)
            result = await self.generate_document(
                analysis_data=analysis_data,
                document_type=document_type,
                custom_prompt=enhanced_user_prompt,
                language=language
            )
            
            # 소스 요약 관련 정보 추가
            result["source_summaries_used"] = True
            result["summarized_files_count"] = len(source_summaries.get("summaries", {})) if source_summaries else 0
            
            logger.info(f"문서 생성 완료 (소스 요약 포함): {document_type}")
            return result

        except Exception as e:
            logger.error(f"문서 생성 실패 (소스 요약 포함): {document_type}, 오류: {str(e)}")
            raise
    
    def _get_enhanced_user_prompt(
        self, 
        document_type: DocumentType, 
        analysis_data: Dict[str, Any], 
        source_summaries: Dict[str, Any],
        language: str
    ) -> str:
        """소스코드 요약을 포함한 향상된 사용자 프롬프트 생성"""
        
        # Safely get the prompt section, falling back to user_prompts
        prompt_section = prompts.get("enhanced_user_prompts")
        if not prompt_section:
            logger.warning("Could not find 'enhanced_user_prompts' in config, falling back to 'user_prompts'.")
            prompt_section = prompts.get("user_prompts", {})

        # 변수 초기화
        source_summary_info = ""
        key_summaries = ""

        # 분석 데이터가 너무 클 경우 잘라내기
        truncated_data = truncate_analysis_data(analysis_data, max_tokens=settings.MAX_ANALYSIS_DATA_TOKENS)

        # 잘라낸 분석 데이터에서 주요 정보 추출
        repositories = truncated_data.get("repositories", [])
        tech_specs = truncated_data.get("tech_specs", [])
        ast_analysis = truncated_data.get("ast_analysis", {})
        code_metrics = truncated_data.get("code_metrics", {})
        
        logger.debug(f"Extracted data - repos: {len(repositories)}, tech_specs: {len(tech_specs)}, ast: {len(ast_analysis)}, metrics: {bool(code_metrics)}")
        
        # 기본 정보 구성 (개선된 로직)
        if repositories:
            repo_info = "\n".join([f"- {repo.get('url', 'Unknown')} (브랜치: {repo.get('branch', 'main')})" for repo in repositories])
        else:
            repo_info = "분석된 저장소가 없습니다. 먼저 Git 저장소 분석을 수행해주세요."
        
        # 기술 스택 정보 (개선된 로직)
        if tech_specs:
            tech_info = "\n".join([
                f"- {spec.get('name', 'Unknown')}: {spec.get('version', 'Unknown')}" +
                (f" (프레임워크: {spec.get('framework')})" if spec.get('framework') else "") +
                (f" (의존성: {len(spec.get('dependencies', []))}개)" if spec.get('dependencies') else "")
                for spec in tech_specs
            ])
        else:
            tech_info = "기술 스택 정보가 없습니다. include_tech_spec=true로 분석을 수행해주세요."
        
        # AST 분석 정보 (개선된 로직)
        if ast_analysis:
            total_functions = sum(len(nodes) for nodes in ast_analysis.values() if isinstance(nodes, list))
            file_count = len(ast_analysis)
            ast_info = f"총 {file_count}개 파일에서 {total_functions}개의 함수/클래스 분석됨"
        else:
            ast_info = "AST 분석 정보가 없습니다. include_ast=true로 분석을 수행해주세요."
        
        # 코드 메트릭 정보 (개선된 로직)
        if code_metrics and any(code_metrics.values()):
            metrics_parts = []
            if code_metrics.get('lines_of_code', 0) > 0:
                metrics_parts.append(f"총 코드 라인 수: {code_metrics['lines_of_code']}")
            if code_metrics.get('cyclomatic_complexity'):
                metrics_parts.append(f"순환 복잡도: {code_metrics['cyclomatic_complexity']:.2f}")
            if code_metrics.get('maintainability_index'):
                metrics_parts.append(f"유지보수성 지수: {code_metrics['maintainability_index']:.2f}")
            if code_metrics.get('comment_ratio'):
                metrics_parts.append(f"주석 비율: {code_metrics['comment_ratio']:.2f}%")
            
            metrics_info = ", ".join(metrics_parts) if metrics_parts else "코드 메트릭 데이터가 부족합니다."
        else:
            metrics_info = "코드 메트릭 정보가 없습니다. 분석을 다시 수행해주세요."
        
        # 소스코드 요약 정보 구성
        source_summary_info = ""
        if source_summaries and "summaries" in source_summaries:
            file_summaries = source_summaries["summaries"]
            source_summary_info = f"총 {len(file_summaries)}개 파일의 소스코드 요약 포함"
            
            # 언어별 통계
            language_stats = {}
            for file_path, summary in file_summaries.items():
                lang = summary.get("language", "Unknown")
                if lang not in language_stats:
                    language_stats[lang] = 0
                language_stats[lang] += 1
            
            lang_info = ", ".join([f"{lang}: {count}개" for lang, count in language_stats.items()])
            source_summary_info += f" ({lang_info})"
        else:
            source_summary_info = "소스코드 요약 정보가 없습니다. 소스코드 요약을 먼저 수행해주세요."
        
        # 주요 소스코드 요약 내용 추출 (상위 10개 파일)
        key_summaries = ""
        if source_summaries and "summaries" in source_summaries:
            file_summaries = source_summaries["summaries"]
            sorted_files = sorted(file_summaries.items(), 
                                key=lambda x: x[1].get("file_size", 0), reverse=True)[:10]

            key_summaries = "\n\n### 주요 소스파일 요약\n"
            for file_path, summary in sorted_files:
                key_summaries += f"\n**{file_path}** ({summary.get('language', 'Unknown')}):\n"
                key_summaries += f"{summary.get('summary', '요약 없음')}\n"
        else:
            key_summaries = f"\n\n### 소스코드 요약 안내\n소스코드 요약을 위해 다음 API를 사용하세요:\n```bash\ncurl -X POST \"http://localhost:8001/api/v1/source-summary/summarize-repository/{analysis_data.get('analysis_id', 'your-analysis-id')}\"\n```"

        # 데이터 유효성 검사 (소스 요약 포함)
        has_meaningful_data = (
            len(repositories) > 0 or 
            len(tech_specs) > 0 or 
            len(ast_analysis) > 0 or 
            (code_metrics and any(code_metrics.values())) or
            (source_summaries and source_summaries.get("summaries"))
        )
        
        detailed_analysis_json = json.dumps(truncated_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)

        if not has_meaningful_data:
            prompt_template = prompt_section.get("no_data_template", {}).get(language, "")
            return prompt_template.format(
                document_type=document_type.value,
                analysis_id=analysis_data.get('analysis_id', 'Unknown'),
                num_repositories=len(repositories),
                num_tech_specs=len(tech_specs),
                num_ast_files=len(ast_analysis),
                code_metrics_status=('있음' if code_metrics and any(code_metrics.values()) else '없음') if language == 'korean' else ('Available' if code_metrics and any(code_metrics.values()) else 'Not available'),
                source_summary_status=('있음' if source_summaries and source_summaries.get("summaries") else '없음') if language == 'korean' else ('Available' if source_summaries and source_summaries.get("summaries") else 'Not available')
            )
        else:
            prompt_template = prompt_section.get("with_data_template", {}).get(language, "")
            return prompt_template.format(
                document_type=document_type.value,
                repo_info=repo_info,
                tech_info=tech_info,
                ast_info=ast_info,
                metrics_info=metrics_info,
                source_summary_info=source_summary_info,
                key_summaries=key_summaries,
                detailed_analysis_json=detailed_analysis_json
            )
    
    async def generate_multiple_documents(
        self,
        analysis_data: Dict[str, Any],
        document_types: List[DocumentType],
        language: str = "korean"
    ) -> List[Dict[str, Any]]:
        """
        여러 타입의 문서를 한 번에 생성합니다.
        
        Args:
            analysis_data: 분석 결과 데이터
            document_types: 생성할 문서 타입 목록
            language: 문서 언어
            
        Returns:
            생성된 문서들의 목록
        """
        results = []
        
        for doc_type in document_types:
            try:
                result = await self.generate_document(analysis_data, doc_type, language=language)
                results.append(result)
            except Exception as e:
                logger.error(f"문서 생성 실패: {doc_type}, 오류: {str(e)}")
                # 실패한 문서도 결과에 포함 (오류 정보와 함께)
                results.append({
                    "document_type": doc_type,
                    "language": language,
                    "error": str(e),
                    "generated_at": datetime.now().isoformat(),
                    "analysis_id": analysis_data.get("analysis_id")
                })
        
        return results
    
    async def generate_documents_with_source_summaries(
        self,
        analysis_data: Dict[str, Any],
        analysis_id: str,
        document_types: List[DocumentType],
        language: str = "korean",
        custom_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        소스코드 요약을 활용하여 여러 타입의 문서를 한 번에 생성합니다.
        
        Args:
            analysis_data: 분석 결과 데이터
            analysis_id: 분석 ID
            document_types: 생성할 문서 타입 목록
            language: 문서 언어
            custom_prompt: 사용자 정의 프롬프트
            
        Returns:
            생성된 문서들의 목록
        """
        results = []
        
        # 소스코드 요약 데이터 로드
        try:
            from services.source_summary_service import SourceSummaryService
            source_summary_service = SourceSummaryService()
            source_summaries = source_summary_service.load_repository_summaries(analysis_id)
            
            if not source_summaries or not source_summaries.get("summaries"):
                logger.warning(f"No source summaries found for analysis {analysis_id}, falling back to basic document generation")
                # 소스 요약이 없으면 기본 문서 생성으로 폴백
                return await self.generate_multiple_documents(analysis_data, document_types, language)
                
        except Exception as e:
            logger.error(f"Failed to load source summaries for analysis {analysis_id}: {e}")
            # 소스 요약 로드 실패 시 기본 문서 생성으로 폴백
            return await self.generate_multiple_documents(analysis_data, document_types, language)
        
        # 각 문서 타입별로 소스 요약을 활용한 문서 생성
        for doc_type in document_types:
            try:
                result = await self.generate_document_with_source_summaries(
                    analysis_data=analysis_data,
                    source_summaries=source_summaries,
                    document_type=doc_type,
                    custom_prompt=custom_prompt,
                    language=language
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"문서 생성 실패 (소스 요약 포함): {doc_type}, 오류: {str(e)}")
                # 실패한 문서도 결과에 포함 (오류 정보와 함께)
                results.append({
                    "document_type": doc_type,
                    "language": language,
                    "error": str(e),
                    "generated_at": datetime.now().isoformat(),
                    "analysis_id": analysis_data.get("analysis_id"),
                    "source_summaries_used": True
                })
        
        return results
    
    def get_available_document_types(self) -> List[str]:
        """사용 가능한 문서 타입 목록 반환"""
        return [doc_type.value for doc_type in DocumentType]
