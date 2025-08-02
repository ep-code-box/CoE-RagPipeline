<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

## CoE-RagPipeline 상세 정리

사용자의 요청에 따라 CoE-RagPipeline의 기능을 더 구체적으로 정리하면 다음과 같습니다:

### 주요 처리 흐름

#### 1단계: Git Repository 분석 및 연관관계 추출

- **입력**: 1개 또는 여러 개의 Git repository URL
- **정적 분석 수행**:
    - AST(Abstract Syntax Tree) 파싱
    - 코드 메트릭 계산 (복잡도, 중복도, 라인 수 등)
    - 기술 스택 식별 (언어, 프레임워크, 라이브러리)
    - 의존성 분석 (package.json, requirements.txt, pom.xml 등)
    - 파일/모듈 간 import/include 관계 추출
- **Repository 간 연관관계 추출**[^1][^2]:
    - 공통 의존성 패키지 분석
    - 코드 패턴 유사성 매칭
    - API 호출 관계 추적
    - 공통 모듈/라이브러리 사용 패턴
    - 개발자/커밋 교집합 분석
    - 이슈/PR 상호 참조 관계
- **저장**: 분석 결과를 JSON 형태로 구조화하여 **MariaDB**에 저장[^3][^4]


#### 2단계: 사용자 문서 통합 및 가이드 생성

- **추가 입력**: 개발 관련 문서 또는 정리 문서 URL
- **LLM 기반 문서 생성**[^5][^6][^7]:
    - 1단계 분석 결과 + 2단계 문서를 LLM에 전달
    - **개발가이드 문서** 생성: 프로젝트별 코딩 컨벤션, 아키텍처 가이드라인
    - **공통코드 리스트** 생성: 여러 repository에서 반복 사용되는 코드 패턴
    - **재활용 함수 및 공통함수 리스트** 생성: 중복 제거 가능한 함수들 식별
- **Markdown 파일 생성**: 생성된 가이드를 구조화된 **Markdown 형식**으로 저장
- **MariaDB 저장**: 생성된 문서 메타데이터 및 내용을 데이터베이스에 저장


#### 3단계: 임베딩 및 벡터 저장

- **청킹(Chunking)**: 생성된 Markdown 문서를 의미 단위로 분할
- **임베딩 생성**[^8][^9][^10]: 각 청크를 벡터로 변환 (일반적으로 OpenAI, Anthropic 등의 임베딩 모델 사용)
- **벡터 DB 저장**: 생성된 임베딩을 **ChromaDB**에 저장하여 의미 기반 검색 지원


### API 엔드포인트 설계

```python
# Repository 분석 요청
POST /analyze
{
    "repositories": ["https://github.com/org/repo1", "https://github.com/org/repo2"],
    "documents": ["https://docs.company.com/dev-guide", "https://wiki.internal/standards"]
}

# 분석 결과 조회
GET /results/{analysis_id}

# 의미 기반 검색
POST /search
{
    "query": "React component best practices",
    "limit": 10
}

# 임베딩 통계
GET /embeddings/stats

# 실시간 코드 분석
POST /realtime/analyze
{
    "code": "function example() { ... }",
    "context": "react-component"
}
```


### 데이터 스키마 예시

**MariaDB 스키마**:

```sql
-- 분석 결과 메타데이터
CREATE TABLE analysis_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    repository_urls JSON,
    document_urls JSON,
    analysis_status ENUM('pending', 'completed', 'failed'),
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Repository 연관관계
CREATE TABLE repository_relationships (
    id INT PRIMARY KEY AUTO_INCREMENT,
    repo1_url VARCHAR(255),
    repo2_url VARCHAR(255),
    relationship_type ENUM('dependency', 'similar_pattern', 'common_contributor'),
    confidence_score FLOAT,
    details JSON
);

-- 생성된 가이드 문서
CREATE TABLE generated_guides (
    id INT PRIMARY KEY AUTO_INCREMENT,
    analysis_id INT,
    guide_type ENUM('dev_guide', 'common_code', 'reusable_functions'),
    content LONGTEXT,  -- Markdown 내용
    embedding_chunks INT,  -- 청킹된 개수
    created_at TIMESTAMP
);
```

**ChromaDB 구조**:

- **Collection**: 프로젝트별/분석별로 분리
- **Documents**: 청킹된 Markdown 텍스트
- **Embeddings**: 각 청크의 벡터 표현
- **Metadata**: 원본 문서 정보, 청크 위치, 가이드 타입 등


### 연관관계 분석 알고리즘

여러 repository 간의 연관성을 추출하기 위해 다음과 같은 방법들을 조합 사용[^1][^11][^2]:

1. **의존성 그래프 분석**: 공통 패키지/라이브러리 사용 패턴
2. **코드 유사도 분석**: AST 기반 구조적 유사성 계산
3. **API 호출 패턴**: 서비스 간 통신 관계 추적
4. **개발자 협업 네트워크**: Git log 기반 공통 기여자 분석
5. **이슈/PR 교차 참조**: GitHub/GitLab 메타데이터 분석

이러한 종합적인 분석을 통해 MSA 환경에서 분산된 여러 repository 간의 숨겨진 연관성을 발견하고, 이를 바탕으로 통합된 개발 가이드를 자동 생성하는 것이 CoE-RagPipeline의 핵심 기능입니다.

<div style="text-align: center">⁂</div>

[^1]: https://www.codiga.io/static-code-analysis/github/

[^2]: https://github.com/multilang-depends/depends

[^3]: https://mariadb.com/docs/server/reference/system-tables/information-schema/information-schema-tables/information-schema-metadata_lock_info-table

[^4]: https://github.com/FromDual/mariadb-sys

[^5]: https://docs.crawl4ai.com/core/markdown-generation/

[^6]: https://artifex.com/blog/rag-llm-and-pdf-conversion-to-markdown-text-with-pymupdf

[^7]: https://developer.webex.com/blog/boosting-ai-performance-the-power-of-llm-friendly-content-in-markdown

[^8]: https://www.pinecone.io/learn/vector-database/

[^9]: https://aws.amazon.com/what-is/vector-databases/

[^10]: https://weaviate.io/blog/vector-embeddings-explained

[^11]: https://github.com/thunlp/OpenNRE

[^12]: tonghab-seolgye.md

[^13]: http://mohitmayank.com/a_lazy_data_science_guide/natural_language_processing/relation_extraction/

[^14]: https://www.mathworks.com/help/matlab/ref/dependencyanalyzer-app.html

[^15]: https://stackoverflow.com/questions/69933548/getting-static-analysis-of-github-repositories

[^16]: https://explosion.ai/blog/relation-extraction

[^17]: https://www.qodo.ai/glossary/code-dependency-analysis/

[^18]: https://owasp.org/www-community/Source_Code_Analysis_Tools

[^19]: https://www.ndepend.com

[^20]: https://livablesoftware.com/tools-mine-analyze-github-git-software-data/

[^21]: http://nlpprogress.com/english/relationship_extraction.html

[^22]: https://github.com/analysis-tools-dev/static-analysis

[^23]: https://forum.knime.com/t/nlp-relation-extraction/85892

[^24]: https://en.wikipedia.org/wiki/List_of_tools_for_static_code_analysis

[^25]: https://www.reddit.com/r/codereview/comments/1j5xhcn/best_aipowered_code_analysis_tool_for_github_repos/

[^26]: https://arxiv.org/html/2409.04934v1

[^27]: https://www.reddit.com/r/dotnet/comments/1f6c5zy/free_code_analysis_tools/

[^28]: https://github.com/semgrep/semgrep

[^29]: https://direct.mit.edu/dint/article/5/3/824/114952/Relation-Extraction-Based-on-Prompt-Information

[^30]: https://www.reddit.com/r/vectordatabase/comments/1fkfabo/calculating_storage_requirements_for_vector/

[^31]: https://www.linkedin.com/pulse/complete-guide-creating-storing-vector-embeddings-pavan-belagatti-5fyfc

[^32]: https://cobaya.readthedocs.io/en/latest/llm_context.html

[^33]: https://github.com/mariadb

[^34]: https://stackoverflow.com/questions/16288579/how-to-include-mysql-database-schema-on-github

[^35]: https://community.n8n.io/t/get-consistent-well-formatted-markdown-json-outputs-from-llms/80749

[^36]: https://www.reddit.com/r/SQL/comments/1bx86k5/git_versioning_for_our_mssql_and_mysql/

[^37]: https://cloud.google.com/discover/what-is-a-vector-database

[^38]: https://github.com/orgs/dita-ot/discussions/4476

[^39]: https://www.reddit.com/r/webdev/comments/28456k/how_to_use_github_with_a_mysql_database/

[^40]: https://community.openai.com/t/which-database-tools-suit-for-storing-embeddings-generated-by-the-embedding-endpoint/23337

[^41]: https://forum.cursor.com/t/its-hard-to-generate-a-markdown-document/14909

