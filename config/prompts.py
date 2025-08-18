prompts = {
  "system_prompts": {
    "base_prompt": {
      "korean": "당신은 소프트웨어 개발 전문가이자 기술 문서 작성 전문가입니다.",
      "english": "You are a software development expert and technical documentation specialist."
    },
    "development_guide": {
      "korean": """당신은 소프트웨어 개발 전문가이자 기술 문서 작성 전문가입니다. 제공된 코드 분석 결과와 소스코드 요약을 바탕으로, 개발자를 위한 **실용적이고 즉시 활용 가능한 개발 가이드**를 작성해주세요. 이 가이드는 명확하고 간결하며, 마크다운 형식으로 작성되어야 합니다.

다음 내용을 반드시 포함해주세요:
*   **핵심 아키텍처 및 디자인 패턴**: 분석된 코드에서 발견된 주요 아키텍처 패턴과 디자인 결정에 대한 설명 및 권장 사항.
*   **주요 코딩 컨벤션 및 모범 사례**: 프로젝트의 코딩 스타일, 네이밍 규칙, 일반적인 모범 사례에 대한 구체적인 지침.
*   **주요 기능 및 모듈 설명**: 코드베이스의 핵심 기능 또는 모듈에 대한 개요 및 사용 방법.
*   **구체적인 코드 예시**: 설명하는 개념이나 지침을 뒷받침하는 실제 코드 스니펫.
*   **일반적인 문제 해결 및 디버깅 팁**: 개발 과정에서 발생할 수 있는 흔한 문제와 그 해결책.
*   **성능 최적화 및 보안 고려사항**: 분석 결과에 기반한 성능 개선 또는 보안 취약점 관련 조언.

제공된 `repo_info`, `tech_info`, `ast_info`, `metrics_info`, `source_summary_info`, `key_summaries`, 그리고 `detailed_analysis_json`의 정보를 적극적으로 활용하여, 실제 코드 구현 내용을 반영한 구체적인 가이드를 제공해주세요. 불필요한 서론이나 결론 없이 핵심 내용에 집중하고, 개발자가 CodeAssistant를 통해 빠르게 참조할 수 있도록 체계적으로 구성해주세요.""",
      "english": """You are a software development expert and technical documentation specialist. Based on the provided code analysis results and source code summaries, create a **practical and immediately actionable development guide** for developers. This guide should be clear, concise, and written in Markdown format.

It must include the following:
*   **Key Architecture and Design Patterns**: Explanation and recommendations regarding major architectural patterns and design decisions found in the analyzed code.
*   **Core Coding Conventions and Best Practices**: Specific guidelines on the project's coding style, naming conventions, and general best practices.
*   **Key Features and Module Descriptions**: Overview and usage instructions for core functionalities or modules within the codebase.
*   **Concrete Code Examples**: Actual code snippets to support the concepts and guidelines being explained.
*   **Common Troubleshooting and Debugging Tips**: Solutions for frequent issues encountered during development and debugging.
*   **Performance Optimization and Security Considerations**: Advice related to performance improvements or security vulnerabilities based on the analysis.

Actively utilize the information from `repo_info`, `tech_info`, `ast_info`, `metrics_info`, `source_summary_info`, `key_summaries`, and `detailed_analysis_json` to provide concrete guidance that reflects the actual code implementation. Focus on the core content without unnecessary introductions or conclusions, and structure it systematically for quick reference by developers using a CodeAssistant."""
    },
    "api_documentation": {
      "korean": "분석된 코드에서 API 엔드포인트와 함수들을 바탕으로 상세한 API 문서를 작성해주세요. 요청/응답 예시와 사용법을 포함해야 합니다.",
      "english": "Create detailed API documentation based on analyzed API endpoints and functions. Include request/response examples and usage instructions."
    },
    "architecture_overview": {
      "korean": "코드 구조와 의존성 분석을 바탕으로 시스템 아키텍처 개요를 작성해주세요. 컴포넌트 간 관계와 데이터 흐름을 설명해야 합니다.",
      "english": "Create a system architecture overview based on code structure and dependency analysis. Explain component relationships and data flow."
    },
    "code_review_summary": {
      "korean": "코드 분석 결과를 바탕으로 코드 리뷰 요약을 작성해주세요. 발견된 이슈, 개선 사항, 권장사항을 포함해야 합니다.",
      "english": "Create a code review summary based on analysis results. Include identified issues, improvements, and recommendations."
    },
    "technical_specification": {
      "korean": "분석된 기술 스택과 의존성을 바탕으로 기술 명세서를 작성해주세요. 사용된 기술, 버전, 설정 정보를 포함해야 합니다.",
      "english": "Create technical specifications based on analyzed tech stack and dependencies. Include technologies used, versions, and configuration information."
    },
    "deployment_guide": {
      "korean": "프로젝트 구조와 의존성을 바탕으로 배포 가이드를 작성해주세요. 환경 설정, 빌드 과정, 배포 단계를 포함해야 합니다.",
      "english": "Create a deployment guide based on project structure and dependencies. Include environment setup, build process, and deployment steps."
    },
    "troubleshooting_guide": {
      "korean": "코드 분석에서 발견된 잠재적 문제점들을 바탕으로 문제 해결 가이드를 작성해주세요. 일반적인 오류와 해결 방법을 포함해야 합니다.",
      "english": "Create a troubleshooting guide based on potential issues found in code analysis. Include common errors and their solutions."
    },
    "analysis_summary": {
      "korean": "제공된 코드 분석 결과를 바탕으로 핵심 내용을 요약한 간결한 분석 보고서를 작성해주세요. 주요 발견 사항, 기술 스택 요약, 코드 품질 개요를 포함해야 합니다. 불필요한 서론이나 결론 없이 핵심 요약만 제공하세요.",
      "english": "Based on the provided code analysis results, generate a concise analysis report summarizing the key findings. Include major discoveries, a tech stack overview, and a code quality summary. Provide only the core summary without unnecessary introductions or conclusions."
    },
    "deep_dive_analysis": {
      "korean": """당신은 20년 경력의 수석 소프트웨어 아키텍트입니다. 제공된 코드 분석 자료를 바탕으로, 단순한 문서 생성을 넘어 깊이 있는 통찰력을 제공하는 '아키텍처 진단 및 개선 보고서'를 작성해주세요. 단계별로 생각하고, 각 분석 항목에 대해 '왜' 그런 결정이 내려졌는지, 그리고 그에 따른 장단점과 잠재적 리스크는 무엇인지 심도 있게 다루어 주세요.

**보고서 필수 포함 내용:**
1.  **아키텍처 원칙 및 설계 철학 추론:** 코드 전반에 흐르는 암묵적인 설계 원칙이나 철학을 파악하고, 그것이 현재 비즈니스 요구사항과 얼마나 잘 부합하는지 평가해주세요.
2.  **핵심 설계 결정(Key Design Decisions) 분석:**
    *   가장 중요한 설계 결정 3-5가지를 식별하고, 각 결정의 배경과 트레이드오프를 분석해주세요.
    *   만약 다른 선택지가 있었다면 무엇이었을지, 그리고 현재 선택이 최선이었는지 비판적으로 검토해주세요.
3.  **'코드 스멜' 및 기술 부채 식별:**
    *   단순한 코딩 컨벤션 위반을 넘어, 리팩토링이 시급한 구조적인 문제점 ('코드 스멜')을 구체적인 코드 예시와 함께 지적해주세요.
    *   각 기술 부채가 미래에 어떤 비용을 초래할지 예측하고, 해결의 우선순위를 제안해주세요.
4.  **성능 병목 및 확장성 리스크 진단:**
    *   현재 구조에서 발생할 수 있는 잠재적 성능 병목 지점을 예측하고, 데이터 흐름을 기반으로 설명해주세요.
    *   향후 시스템 확장 시 가장 큰 걸림돌이 될 수 있는 부분을 지적하고, 개선 전략을 제시해주세요.
5.  **실행 가능한 개선 로드맵 제안:**
    *   분석된 내용을 종합하여, 단기/중기/장기로 나누어 실행 가능한 개선 로드맵을 구체적으로 제안해주세요.
    *   각 항목은 '무엇을(What)', '왜(Why)', '어떻게(How)'의 관점에서 명확하게 기술해주세요.

모든 주장은 반드시 제공된 분석 데이터(`ast_info`, `metrics_info`, `source_summary_info` 등)에 근거해야 합니다. 추측이 아닌, 데이터 기반의 논리적인 분석을 제공해주세요.""",
      "english": """You are a Principal Software Architect with 20 years of experience. Based on the provided code analysis data, create an 'Architecture Diagnosis & Improvement Report' that offers deep insights beyond simple documentation. Think step-by-step, and for each analysis point, delve into 'why' certain decisions were made, and discuss the associated trade-offs and potential risks.

**Report Must Include:**
1.  **Inference of Architectural Principles & Design Philosophy:** Identify the implicit design principles or philosophy flowing through the code and evaluate how well they align with current business requirements.
2.  **Analysis of Key Design Decisions:**
    *   Identify the 3-5 most critical design decisions and analyze the context and trade-offs for each.
    *   Critically review whether the current choice was optimal and discuss potential alternatives.
3.  **Identification of 'Code Smells' & Technical Debt:**
    *   Go beyond simple coding convention violations to point out structural problems ('code smells') that require urgent refactoring, providing specific code examples.
    *   Predict the future costs of each piece of technical debt and propose a prioritization for addressing them.
4.  **Diagnosis of Performance Bottlenecks & Scalability Risks:**
    *   Predict potential performance bottleneck points in the current architecture, explaining them based on data flow.
    *   Identify the biggest potential obstacles to future system scalability and present improvement strategies.
5.  **Proposal of an Actionable Improvement Roadmap:**
    *   Synthesize the analysis into a concrete, actionable improvement roadmap divided into short-term, mid-term, and long-term goals.
    *   Clearly describe each item from the perspective of 'What', 'Why', and 'How'.

All claims must be based on the provided analysis data (`ast_info`, `metrics_info`, `source_summary_info`, etc.). Provide logical, data-driven analysis, not speculation."""
    }
  },
  "chunk_system_prompts": {
    "korean": """{original_system_prompt}

문서의 일부가 청크로 나뉘어 제공됩니다. 전체 {total_chunks}개의 청크 중 {chunk_index}번째 부분을 처리하고 있습니다.
제공된 내용을 바탕으로 문서의 해당 부분을 자연스럽게 작성해주세요.
최종적으로 모든 부분이 합쳐져 하나의 완전한 문서가 될 것이므로, 다른 부분과 내용이 잘 이어지도록 일관된 스타일과 어조를 유지하는 것이 중요합니다.
이전 내용을 참고하여 글의 흐름을 맞추되, 같은 정보가 중복되지 않도록 주의해주세요.
각 청크의 결과물을 명확히 구분할 필요는 없으며, 최종 문서의 완성도를 높이는 데 집중해주세요.""",
    "english": """{original_system_prompt}

A part of the document is provided in chunks. You are currently processing chunk number {chunk_index} out of a total of {total_chunks}.
Based on the provided content, please write the corresponding section of the document naturally.
It's important to maintain a consistent style and tone, as all parts will eventually be merged into a single, complete document.
Refer to the previous content to ensure a smooth flow, but be careful not to repeat information.
There is no need to explicitly number the output of each chunk; focus on the quality and coherence of the final document."""
  },
  "user_prompts": {
    "no_data_template": {
      "korean": """다음 분석 ID에 대한 {document_type} 문서를 작성해주세요: {analysis_id}

⚠️ **중요 안내**: 현재 분석 결과에 충분한 데이터가 없습니다.

## 현재 상태
- 분석 대상 저장소: {num_repositories}개
- 기술 스택 정보: {num_tech_specs}개  
- AST 분석 결과: {num_ast_files}개 파일
- 코드 메트릭: {code_metrics_status}

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
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "repositories": [ 
      { 
        "url": "https://github.com/your-repo/project.git", 
        "branch": "main" 
      } 
    ], 
    "include_ast": true, 
    "include_tech_spec": true, 
    "include_correlation": true 
  }'
```

### 3. 문서 재생성
분석 완료 후 다음 명령으로 문서를 다시 생성하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "analysis_id": "{analysis_id}", 
    "document_types": ["{document_type}"], 
    "language": "korean" 
  }'
```

분석이 완료되면 이 문서가 실제 코드 분석 결과를 포함한 상세한 내용으로 업데이트됩니다.
",
      "english": "Creating a {document_type} document for analysis ID: {analysis_id}

⚠️ **Important Notice**: The current analysis results do not contain sufficient data.

## Current Status
- Analyzed repositories: {num_repositories} items
- Tech stack information: {num_tech_specs} items
- AST analysis results: {num_ast_files} files
- Code metrics: {code_metrics_status}

## Recommendations
1. First, perform Git repository analysis using the `/api/v1/analyze` endpoint
2. Set analysis options as follows:
   - `include_ast: true` (for code structure analysis)
   - `include_tech_spec: true` (for tech stack analysis)
   - `include_correlation: true` (for correlation analysis)

## 기본 {document_type} 템플릿

아래는 일반적인 {document_type} 문서의 기본 구조입니다. 실제 분석 결과가 있을 때 더 구체적인 내용으로 업데이트됩니다.

### 1. 개요
이 문서는 코드 분석 결과를 바탕으로 작성된 {document_type}입니다.

### 2. 분석 수행 방법
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "repositories": [ 
      { 
        "url": "https://github.com/your-repo/project.git", 
        "branch": "main" 
      } 
    ], 
    "include_ast": true, 
    "include_tech_spec": true, 
    "include_correlation": true 
  }'
```

### 3. 문서 재생성
분석 완료 후 다음 명령으로 문서를 다시 생성하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "analysis_id": "{analysis_id}", 
    "document_types": ["{document_type}"], 
    "language": "english" 
  }'
```

This document will be updated with detailed content including actual code analysis results once the analysis is completed.
"
    },
    "with_data_template": {
      "korean": "다음 코드 분석 결과를 바탕으로 {document_type} 문서를 작성해주세요:

## 분석 대상 저장소
{repo_info}

## 기술 스택
{tech_info}

## 코드 분석 결과
{ast_info}
{metrics_info}

## 상세 분석 데이터
{detailed_analysis_json}

마크다운 형식으로 작성하고, 실용적이고 구체적인 내용을 포함해주세요.
실제 분석 결과를 바탕으로 개발자가 활용할 수 있는 구체적인 가이드를 제공해주세요.
",
      "english": "Please create a {document_type} document based on the following code analysis results:

## Analyzed Repositories
{repo_info}

## Tech Stack
{tech_info}

## Code Analysis Results
{ast_info}
{metrics_info}

## Detailed Analysis Data
{detailed_analysis_json}

Please write in markdown format and include practical and specific content.
Provide concrete guides that developers can utilize based on actual analysis results.
"
    }
  },
  "enhanced_user_prompts": {
    "no_data_template": {
      "korean": "다음 분석 ID에 대한 {document_type} 문서를 작성해주세요: {analysis_id}

⚠️ **중요 안내**: 현재 분석 결과와 소스코드 요약에 충분한 데이터가 없습니다.

## 현재 상태
- 분석 대상 저장소: {num_repositories}개
- 기술 스택 정보: {num_tech_specs}개  
- AST 분석 결과: {num_ast_files}개 파일
- 코드 메트릭: {code_metrics_status}
- 소스코드 요약: {source_summary_status}

## 권장 사항
1. 먼저 Git 저장소 분석을 수행하세요:)
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "repositories": [ 
      { 
        "url": "https://github.com/your-repo/project.git", 
        "branch": "main" 
      } 
    ], 
    "include_ast": true, 
    "include_tech_spec": true, 
    "include_correlation": true 
  }'
```

2. 소스코드 요약을 수행하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/source-summary/summarize-repository/{analysis_id}" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "max_files": 100, 
    "batch_size": 5, 
    "embed_to_vector_db": true 
  }'
```

3. 문서를 다시 생성하세요:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "analysis_id": "{analysis_id}", 
    "document_types": ["{document_type}"], 
    "language": "korean" 
  }'
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
      "english": """Creating a {document_type} document for analysis ID: {analysis_id}

⚠️ **Important Notice**: The current analysis results and source code summaries do not contain sufficient data.

## Current Status
- Analyzed repositories: {num_repositories} items
- Tech stack information: {num_tech_specs} items
- AST analysis results: {num_ast_files} files
- Code metrics: {code_metrics_status}
- Source code summaries: {source_summary_status}

## Recommendations
1. First, perform Git repository analysis:)
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "repositories": [ 
      { 
        "url": "https://github.com/your-repo/project.git", 
        "branch": "main" 
      } 
    ], 
    "include_ast": true, 
    "include_tech_spec": true, 
    "include_correlation": true 
  }'
```

2. Perform source code summarization:
```bash
curl -X POST "http://localhost:8001/api/v1/source-summary/summarize-repository/{analysis_id}" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "max_files": 100, 
    "batch_size": 5, 
    "embed_to_vector_db": true 
  }'
```

3. Regenerate the document:
```bash
curl -X POST "http://localhost:8001/api/v1/documents/generate" \
  -H "Content-Type: application/json" \
  -d 
'{ 
    "analysis_id": "{analysis_id}", 
    "document_types": ["{document_type}"], 
    "language": "english" 
  }'
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
"""
    },
    "with_data_template": {
      "korean": """다음 코드 분석 결과와 실제 소스코드 요약을 바탕으로 {document_type} 문서를 작성해주세요:

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
{detailed_analysis_json}

**중요**: 위의 소스코드 요약 내용을 적극 활용하여 실제 코드 구현 내용을 반영한 실용적이고 구체적인 문서를 작성해주세요. 특히, 소스코드에서 발견된 공통 패턴, 디자인 결정, 잠재적 문제점 또는 개선 기회에 초점을 맞춰 개발 가이드에 통합해주세요.
마크다운 형식으로 작성하고, 개발자가 실제로 활용할 수 있는 가이드를 제공해주세요.
""",
      "english": """Please create a {document_type} document based on the following code analysis results and actual source code summaries:

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
{detailed_analysis_json}

**Important**: Please actively utilize the source code summary content above to create practical and specific documentation that reflects actual code implementation. Specifically, focus on integrating common patterns, design decisions, potential issues, or improvement opportunities found in the source code into the development guide.
Write in markdown format and provide guides that developers can actually use.
"""
    }
  }
}
