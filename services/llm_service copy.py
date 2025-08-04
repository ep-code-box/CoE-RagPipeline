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
        if not settings.SKAX_API_KEY:
            raise ValueError("SKAX_API_KEY가 설정되지 않았습니다.")
        
        # SKAX API 클라이언트 초기화
        self.client = OpenAI(
            api_key=settings.SKAX_API_KEY,
            base_url=settings.SKAX_API_BASE
        )
        self.model = settings.SKAX_MODEL_NAME
        
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
        
        # Define a custom encoder for handling HttpUrl and ASTNode serialization
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, HttpUrl):
                    return str(obj)
                # Handle ASTNode objects by converting them to dictionaries
                from models.schemas import ASTNode
                if isinstance(obj, ASTNode):
                    return obj.to_dict()
                return super().default(obj)
        
        # 분석 데이터에서 주요 정보 추출
        repositories = analysis_data.get("repositories", [])
        tech_specs = analysis_data.get("tech_specs", [])
        ast_analysis = analysis_data.get("ast_analysis", {})
        code_metrics = analysis_data.get("code_metrics", {})
        
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
        
        if not has_meaningful_data:
            # 분석 데이터가 없는 경우 안내 메시지 포함
            prompt_templates = {
                "korean": f"""
다음 분석 ID에 대한 {document_type} 문서를 작성해주세요: {analysis_data.get('analysis_id', 'Unknown')}

⚠️ **중요 안내**: 현재 분석 결과에 충분한 데이터가 없습니다.

## 현재 상태
- 분석 대상 저장소: {len(repositories)}개
- 기술 스택 정보: {len(tech_specs)}개  
- AST 분석 결과: {len(ast_analysis)}개 파일
- 코드 메트릭: {'있음' if code_metrics and any(code_metrics.values()) else '없음'}

## 권장 사항
1. 먼저 `/api/v1/analyze` 엔드포인트로 Git 저장소 분석을 수행하세요
2. 분석 옵션을 다음과 같이 설정하세요:
   - `include_ast: true` (코드 구조 분석)
   - `include_tech_spec: true` (기술 스택 분석)
   - `include_correlation: true` (연관성 분석)

## 기본 {document_type} 템플릿

아래는 일반적인 {document_type} 문서의 기본 구조입니다. 실제 분석 결과가 있을 때 더 구체적인 내용으로 업데이트됩니다.

### 1. 개요
이 문서는 코드 분석 결과를 바탕으로 작성된 {document_type}입니다.

### 2. 분석 수행 방법
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "repositories": [
      {{
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }}
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }}'
```

### 3. 문서 재생성
분석 완료 후 다음 명령으로 문서를 다시 생성하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "analysis_id": "{analysis_data.get('analysis_id', 'your-analysis-id')}",
    "document_types": ["{document_type}"],
    "language": "korean"
  }}'
```

분석이 완료되면 이 문서가 실제 코드 분석 결과를 포함한 상세한 내용으로 업데이트됩니다.
""",
                "english": f"""
Creating a {document_type} document for analysis ID: {analysis_data.get('analysis_id', 'Unknown')}

⚠️ **Important Notice**: The current analysis results do not contain sufficient data.

## Current Status
- Analyzed repositories: {len(repositories)}
- Tech stack information: {len(tech_specs)} items
- AST analysis results: {len(ast_analysis)} files
- Code metrics: {'Available' if code_metrics and any(code_metrics.values()) else 'Not available'}

## Recommendations
1. First, perform Git repository analysis using the `/api/v1/analyze` endpoint
2. Set analysis options as follows:
   - `include_ast: true` (for code structure analysis)
   - `include_tech_spec: true` (for tech stack analysis)
   - `include_correlation: true` (for correlation analysis)

## Basic {document_type} Template

Below is the basic structure of a typical {document_type} document. It will be updated with more specific content when actual analysis results are available.

### 1. Overview
This document is a {document_type} created based on code analysis results.

### 2. How to Perform Analysis
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "repositories": [
      {{
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }}
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }}'
```

### 3. Document Regeneration
After analysis completion, regenerate the document with:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "analysis_id": "{analysis_data.get('analysis_id', 'your-analysis-id')}",
    "document_types": ["{document_type}"],
    "language": "english"
  }}'
```

This document will be updated with detailed content including actual code analysis results once the analysis is completed.
"""
            }
        else:
            # 분석 데이터가 있는 경우 기존 로직 사용
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
실제 분석 결과를 바탕으로 개발자가 활용할 수 있는 구체적인 가이드를 제공해주세요.
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
Provide concrete guides that developers can utilize based on actual analysis results.
"""
            }
        
        return prompt_templates[language]
    
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
        
        Args:
            analysis_data: 분석 결과 데이터
            source_summaries: 소스코드 요약 결과
            document_type: 생성할 문서 타입
            custom_prompt: 사용자 정의 프롬프트 (선택사항)
            language: 문서 언어 (korean/english)
            
        Returns:
            생성된 문서 정보
        """
        try:
            # 문서 타입별 프롬프트 생성
            system_prompt = self._get_system_prompt(document_type, language)
            user_prompt = custom_prompt or self._get_enhanced_user_prompt(
                document_type, analysis_data, source_summaries, language
            )
            
            logger.info(f"문서 생성 시작 (소스 요약 포함): {document_type}, 언어: {language}")
            
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
                "repositories": [repo.get("url") for repo in analysis_data.get("repositories", [])],
                "source_summaries_used": True,
                "summarized_files_count": len(source_summaries.get("summaries", {})) if source_summaries else 0
            }
            
            logger.info(f"문서 생성 완료 (소스 요약 포함): {document_type}, 토큰 사용량: {result['tokens_used']}")
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
        
        # Define a custom encoder for handling HttpUrl and ASTNode serialization
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, HttpUrl):
                    return str(obj)
                # Handle ASTNode objects by converting them to dictionaries
                from models.schemas import ASTNode
                if isinstance(obj, ASTNode):
                    return obj.to_dict()
                return super().default(obj)
        
        # 분석 데이터에서 주요 정보 추출
        repositories = analysis_data.get("repositories", [])
        tech_specs = analysis_data.get("tech_specs", [])
        ast_analysis = analysis_data.get("ast_analysis", {})
        code_metrics = analysis_data.get("code_metrics", {})
        
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
            key_summaries = "\n\n### 소스코드 요약 안내\n소스코드 요약을 위해 다음 API를 사용하세요:\n```bash\ncurl -X POST \"http://localhost:8001/api/v1/source-summary/summarize-repository/{analysis_data.get('analysis_id', 'your-analysis-id')}\"\n```"
        
        # 데이터 유효성 검사 (소스 요약 포함)
        has_meaningful_data = (
            len(repositories) > 0 or 
            len(tech_specs) > 0 or 
            len(ast_analysis) > 0 or 
            (code_metrics and any(code_metrics.values())) or
            (source_summaries and source_summaries.get("summaries"))
        )
        
        if not has_meaningful_data:
            # 분석 데이터가 없는 경우 안내 메시지 포함
            prompt_templates = {
                "korean": f"""
다음 분석 ID에 대한 {document_type} 문서를 작성해주세요: {analysis_data.get('analysis_id', 'Unknown')}

⚠️ **중요 안내**: 현재 분석 결과와 소스코드 요약에 충분한 데이터가 없습니다.

## 현재 상태
- 분석 대상 저장소: {len(repositories)}개
- 기술 스택 정보: {len(tech_specs)}개  
- AST 분석 결과: {len(ast_analysis)}개 파일
- 코드 메트릭: {'있음' if code_metrics and any(code_metrics.values()) else '없음'}
- 소스코드 요약: {'있음' if source_summaries and source_summaries.get("summaries") else '없음'}

## 권장 사항
1. 먼저 Git 저장소 분석을 수행하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "repositories": [
      {{
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }}
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }}'
```

2. 소스코드 요약을 수행하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/source-summary/summarize-repository/{analysis_data.get('analysis_id', 'your-analysis-id')}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "max_files": 100,
    "batch_size": 5,
    "embed_to_vector_db": true
  }}'
```

3. 문서를 다시 생성하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "analysis_id": "{analysis_data.get('analysis_id', 'your-analysis-id')}",
    "document_types": ["{document_type}"],
    "language": "korean"
  }}'
```

## 기본 {document_type} 템플릿

아래는 일반적인 {document_type} 문서의 기본 구조입니다. 실제 분석 결과와 소스코드 요약이 있을 때 더 구체적인 내용으로 업데이트됩니다.

### 1. 개요
이 문서는 코드 분석 결과와 소스코드 요약을 바탕으로 작성된 {document_type}입니다.

### 2. 완전한 분석을 위한 단계
1. **Git 저장소 분석**: 코드 구조, 기술 스택, 의존성 분석
2. **소스코드 요약**: 실제 코드 내용을 LLM이 분석하여 요약
3. **문서 생성**: 분석 결과와 소스코드 요약을 바탕으로 실용적인 문서 생성

분석이 완료되면 이 문서가 실제 코드 분석 결과와 소스코드 요약을 포함한 상세한 내용으로 업데이트됩니다.
""",
                "english": f"""
Creating a {document_type} document for analysis ID: {analysis_data.get('analysis_id', 'Unknown')}

⚠️ **Important Notice**: The current analysis results and source code summaries do not contain sufficient data.

## Current Status
- Analyzed repositories: {len(repositories)}
- Tech stack information: {len(tech_specs)} items
- AST analysis results: {len(ast_analysis)} files
- Code metrics: {'Available' if code_metrics and any(code_metrics.values()) else 'Not available'}
- Source code summaries: {'Available' if source_summaries and source_summaries.get("summaries") else 'Not available'}

## Recommendations
1. First, perform Git repository analysis:
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "repositories": [
      {{
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }}
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": true
  }}'
```

2. Perform source code summarization:
```bash
curl -X POST "http://localhost:8001/api/v1/source-summary/summarize-repository/{analysis_data.get('analysis_id', 'your-analysis-id')}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "max_files": 100,
    "batch_size": 5,
    "embed_to_vector_db": true
  }}'
```

3. Regenerate the document:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "analysis_id": "{analysis_data.get('analysis_id', 'your-analysis-id')}",
    "document_types": ["{document_type}"],
    "language": "english"
  }}'
```

## Basic {document_type} Template

Below is the basic structure of a typical {document_type} document. It will be updated with more specific content when actual analysis results and source code summaries are available.

### 1. Overview
This document is a {document_type} created based on code analysis results and source code summaries.

### 2. Steps for Complete Analysis
1. **Git Repository Analysis**: Code structure, tech stack, and dependency analysis
2. **Source Code Summarization**: LLM analyzes and summarizes actual code content
3. **Document Generation**: Creates practical documentation based on analysis results and source code summaries

This document will be updated with detailed content including actual code analysis results and source code summaries once the analysis is completed.
"""
            }
        else:
            # 분석 데이터가 있는 경우 기존 로직 사용
            prompt_templates = {
                "korean": f"""
다음 코드 분석 결과와 실제 소스코드 요약을 바탕으로 {document_type} 문서를 작성해주세요:

## 분석 대상 저장소
{repo_info}

## 기술 스택
{tech_info}

## 코드 분석 결과
{ast_info}
{metrics_info}

## 소스코드 요약 정보
{source_summary_info}

{key_summaries}

## 상세 분석 데이터
{json.dumps(analysis_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)}

**중요**: 위의 소스코드 요약 내용을 적극 활용하여 실제 코드 구현 내용을 반영한 실용적이고 구체적인 문서를 작성해주세요. 
마크다운 형식으로 작성하고, 개발자가 실제로 활용할 수 있는 가이드를 제공해주세요.
""",
                "english": f"""
Please create a {document_type} document based on the following code analysis results and actual source code summaries:

## Analyzed Repositories
{repo_info}

## Tech Stack
{tech_info}

## Code Analysis Results
{ast_info}
{metrics_info}

## Source Code Summary Information
{source_summary_info}

{key_summaries}

## Detailed Analysis Data
{json.dumps(analysis_data, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)}

**Important**: Please actively utilize the source code summary content above to create practical and specific documentation that reflects actual code implementation. 
Write in markdown format and provide guides that developers can actually use.
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
            source_summaries = source_summary_service.get_repository_summaries(analysis_id)
            
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