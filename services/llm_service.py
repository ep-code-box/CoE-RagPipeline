import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import HttpUrl

from openai import OpenAI
from config.settings import settings

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """생성 가능한 문서 타입"""
    DEVELOPMENT_GUIDE = "development_guide"
    API_DOCUMENTATION = "api_documentation"
    ARCHITECTURE_OVERVIEW = "architecture_overview"
    CODE_REVIEW_SUMMARY = "code_review_summary"
    TECHNICAL_SPECIFICATION = "technical_specification"
    DEPLOYMENT_GUIDE = "deployment_guide"
    TROUBLESHOOTING_GUIDE = "troubleshooting_guide"


class LLMDocumentService:
    """LLM을 활용한 문서 생성 서비스"""
    
    def __init__(self):
        """LLM 서비스 초기화"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # 비용 효율적인 모델 사용
        
    async def generate_document(
        self,
        analysis_data: Dict[str, Any],
        document_type: DocumentType,
        custom_prompt: Optional[str] = None,
        language: str = "korean"
    ) -> Dict[str, Any]:
        """
        분석 데이터를 바탕으로 문서를 생성합니다.
        
        Args:
            analysis_data: 분석 결과 데이터
            document_type: 생성할 문서 타입
            custom_prompt: 사용자 정의 프롬프트 (선택사항)
            language: 문서 언어 (korean/english)
            
        Returns:
            생성된 문서 정보
        """
        try:
            # 문서 타입별 프롬프트 생성
            system_prompt = self._get_system_prompt(document_type, language)
            user_prompt = custom_prompt or self._get_user_prompt(document_type, analysis_data, language)
            
            logger.info(f"문서 생성 시작: {document_type}, 언어: {language}")
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
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
                "repositories": [repo.get("url") for repo in analysis_data.get("repositories", [])]
            }
            
            logger.info(f"문서 생성 완료: {document_type}, 토큰 사용량: {result['tokens_used']}")
            return result
            
        except Exception as e:
            logger.error(f"문서 생성 실패: {document_type}, 오류: {str(e)}")
            raise
    
    def _get_system_prompt(self, document_type: DocumentType, language: str) -> str:
        """문서 타입별 시스템 프롬프트 생성"""
        
        base_prompt = {
            "korean": "당신은 소프트웨어 개발 전문가이자 기술 문서 작성 전문가입니다.",
            "english": "You are a software development expert and technical documentation specialist."
        }
        
        type_specific_prompts = {
            DocumentType.DEVELOPMENT_GUIDE: {
                "korean": "코드 분석 결과를 바탕으로 개발자를 위한 실용적인 개발 가이드를 작성해주세요. 코딩 컨벤션, 아키텍처 패턴, 모범 사례를 포함해야 합니다.",
                "english": "Create a practical development guide for developers based on code analysis results. Include coding conventions, architecture patterns, and best practices."
            },
            DocumentType.API_DOCUMENTATION: {
                "korean": "분석된 코드에서 API 엔드포인트와 함수들을 바탕으로 상세한 API 문서를 작성해주세요. 요청/응답 예시와 사용법을 포함해야 합니다.",
                "english": "Create detailed API documentation based on analyzed API endpoints and functions. Include request/response examples and usage instructions."
            },
            DocumentType.ARCHITECTURE_OVERVIEW: {
                "korean": "코드 구조와 의존성 분석을 바탕으로 시스템 아키텍처 개요를 작성해주세요. 컴포넌트 간 관계와 데이터 흐름을 설명해야 합니다.",
                "english": "Create a system architecture overview based on code structure and dependency analysis. Explain component relationships and data flow."
            },
            DocumentType.CODE_REVIEW_SUMMARY: {
                "korean": "코드 분석 결과를 바탕으로 코드 리뷰 요약을 작성해주세요. 발견된 이슈, 개선 사항, 권장사항을 포함해야 합니다.",
                "english": "Create a code review summary based on analysis results. Include identified issues, improvements, and recommendations."
            },
            DocumentType.TECHNICAL_SPECIFICATION: {
                "korean": "분석된 기술 스택과 의존성을 바탕으로 기술 명세서를 작성해주세요. 사용된 기술, 버전, 설정 정보를 포함해야 합니다.",
                "english": "Create technical specifications based on analyzed tech stack and dependencies. Include technologies used, versions, and configuration information."
            },
            DocumentType.DEPLOYMENT_GUIDE: {
                "korean": "프로젝트 구조와 의존성을 바탕으로 배포 가이드를 작성해주세요. 환경 설정, 빌드 과정, 배포 단계를 포함해야 합니다.",
                "english": "Create a deployment guide based on project structure and dependencies. Include environment setup, build process, and deployment steps."
            },
            DocumentType.TROUBLESHOOTING_GUIDE: {
                "korean": "코드 분석에서 발견된 잠재적 문제점들을 바탕으로 문제 해결 가이드를 작성해주세요. 일반적인 오류와 해결 방법을 포함해야 합니다.",
                "english": "Create a troubleshooting guide based on potential issues found in code analysis. Include common errors and their solutions."
            }
        }
        
        return f"{base_prompt[language]} {type_specific_prompts[document_type][language]}"
    
    def _get_user_prompt(self, document_type: DocumentType, analysis_data: Dict[str, Any], language: str) -> str:
        """분석 데이터를 바탕으로 사용자 프롬프트 생성"""
        
        # Define a custom encoder for handling HttpUrl serialization
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, HttpUrl):
                    return str(obj)
                return super().default(obj)
        
        # 분석 데이터에서 주요 정보 추출
        repositories = analysis_data.get("repositories", [])
        tech_specs = analysis_data.get("tech_specs", [])
        ast_analysis = analysis_data.get("ast_analysis", {})
        code_metrics = analysis_data.get("code_metrics", {})
        
        # 기본 정보 구성
        repo_info = "\n".join([f"- {repo.get('url', 'Unknown')}" for repo in repositories])
        
        # 기술 스택 정보
        tech_info = ""
        if tech_specs:
            tech_info = "\n".join([f"- {spec.get('name', 'Unknown')}: {spec.get('version', 'Unknown')}" for spec in tech_specs])
        
        # AST 분석 정보
        ast_info = ""
        if ast_analysis:
            total_functions = sum(len(nodes) for nodes in ast_analysis.values() if isinstance(nodes, list))
            ast_info = f"총 {total_functions}개의 함수/클래스 분석됨"
        
        # 코드 메트릭 정보
        metrics_info = ""
        if code_metrics:
            metrics_info = f"총 파일 수: {code_metrics.get('total_files', 0)}, 총 라인 수: {code_metrics.get('total_lines', 0)}"
        
        prompt_templates = {
            "korean": f"""
다음 코드 분석 결과를 바탕으로 {document_type} 문서를 작성해주세요:

## 분석 대상 저장소
{repo_info}

## 기술 스택
{tech_info}

## 코드 분석 결과
{ast_info}
{metrics_info}

## 상세 분석 데이터
{json.dumps(analysis_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)}

마크다운 형식으로 작성하고, 실용적이고 구체적인 내용을 포함해주세요.
""",
            "english": f"""
Please create a {document_type} document based on the following code analysis results:

## Analyzed Repositories
{repo_info}

## Tech Stack
{tech_info}

## Code Analysis Results
{ast_info}
{metrics_info}

## Detailed Analysis Data
{json.dumps(analysis_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)}

Please write in markdown format and include practical and specific content.
"""
        }
        
        return prompt_templates[language]
    
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
    
    def get_available_document_types(self) -> List[str]:
        """사용 가능한 문서 타입 목록 반환"""
        return [doc_type.value for doc_type in DocumentType]