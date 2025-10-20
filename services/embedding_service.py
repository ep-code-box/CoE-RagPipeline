import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
try:
    from langchain_core.documents import Document
except ImportError:  # Fallback for older langchain releases
    from langchain.schema import Document

from models.schemas import AnalysisResult, RepositoryAnalysis, ASTNode
from config.settings import settings

logger = logging.getLogger(__name__)


_embedding_service_singleton = None


def get_embedding_service() -> "EmbeddingService":
    """Process-wide singleton provider for EmbeddingService.

    Avoids reinitializing embeddings model, Chroma client, and LLM client per request.
    """
    global _embedding_service_singleton
    if _embedding_service_singleton is None:
        _embedding_service_singleton = EmbeddingService()
    return _embedding_service_singleton


class EmbeddingService:
    """분석 결과를 embedding하고 Chroma에 저장하는 서비스"""
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None):
        """
        EmbeddingService 초기화
        
        Args:
            openai_api_key: OpenAI API 키
            openai_api_base: OpenAI API 베이스 URL
        """
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.openai_api_base = openai_api_base or os.getenv("OPENAI_API_BASE")
        self.chroma_host = settings.CHROMA_HOST
        self.chroma_port = settings.CHROMA_PORT
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        # OpenAI Embeddings 초기화
        embedding_kwargs = {"api_key": self.openai_api_key}
        if self.openai_api_base:
            embedding_kwargs["base_url"] = self.openai_api_base
            
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        
        # 텍스트 분할기 초기화 (설정 기반)
        from config.settings import settings as _settings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(getattr(_settings, "EMBEDDING_CHUNK_SIZE", 1000)),
            chunk_overlap=int(getattr(_settings, "EMBEDDING_CHUNK_OVERLAP", 200)),
            length_function=len,
        )
        
        # Chroma 벡터스토어 초기화
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        try:
            chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
            )
        except Exception as e:
            logger.error(
                f"Failed to connect to ChromaDB at {self.chroma_host}:{self.chroma_port}. "
                f"Ensure the Chroma server is running and CHROMA_HOST/CHROMA_PORT are correct. Error: {e}"
            )
            raise
        
        self.vectorstore = Chroma(
            client=chroma_client,
            embedding_function=self.embeddings,
            collection_name=self.collection_name
        )
        logger.info(f"Connected to ChromaDB server at {self.chroma_host}:{self.chroma_port}, collection: {self.collection_name}")

        # LLM 클라이언트 초기화 (리랭킹용, 필요 시에만)
        self.llm_client = None
        try:
            from config.settings import settings as _settings
            if getattr(_settings, "ENABLE_RERANKING", False):
                from openai import OpenAI  # OpenAI 임포트
                self.llm_client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_api_base
                )
                logger.info("LLM client initialized for reranking.")
            else:
                logger.info("LLM reranking disabled by settings (ENABLE_RERANKING=false).")
        except Exception as e:
            logger.warning(f"LLM client init skipped/failed: {e}")
    
    def process_analysis_result(self, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        분석 결과를 처리하여 embedding하고 Chroma에 저장
        
        Args:
            analysis_result: 분석 결과 객체
            
        Returns:
            처리 결과 정보
        """
        try:
            # Build documents from analysis
            documents = self._create_documents_from_analysis(analysis_result)
            # Chunk long documents and attach group_name
            chunked_documents: List[Document] = []
            for doc in documents:
                text = doc.page_content or ""
                group_name = getattr(analysis_result, 'group_name', None)
                chunks = self.text_splitter.split_text(text) if text else []
                total = max(len(chunks), 1)
                if not chunks:
                    # empty or very small doc
                    new_meta = dict(doc.metadata)
                    if group_name:
                        new_meta["group_name"] = group_name
                    new_meta["chunk_index"] = 0
                    new_meta["total_chunks"] = 1
                    chunked_documents.append(Document(page_content=text, metadata=new_meta))
                else:
                    for idx, chunk in enumerate(chunks):
                        new_meta = dict(doc.metadata)
                        if group_name:
                            new_meta["group_name"] = group_name
                        new_meta["chunk_index"] = idx
                        new_meta["total_chunks"] = total
                        chunked_documents.append(Document(page_content=chunk, metadata=new_meta))
            documents = chunked_documents
            
            if not documents:
                logger.warning(f"No documents created for analysis {analysis_result.analysis_id}")
                return {"status": "no_documents", "count": 0}
            
            # 문서들을 Chroma에 저장 (stable IDs)
            import hashlib
            ids: List[str] = []
            for d in documents:
                base = (
                    f"{analysis_result.analysis_id}|"
                    f"{d.metadata.get('document_type','')}|"
                    f"{d.metadata.get('repository_url','')}|"
                    f"{d.metadata.get('file_path','')}|"
                    f"{d.metadata.get('chunk_index',0)}"
                )
                ids.append(hashlib.sha1(base.encode('utf-8')).hexdigest())
            doc_ids = self.vectorstore.add_documents(documents, ids=ids)
            
            logger.info(f"Successfully embedded {len(documents)} documents for analysis {analysis_result.analysis_id}")
            
            return {
                "status": "success",
                "count": len(documents),
                "document_ids": doc_ids,
                "analysis_id": analysis_result.analysis_id
            }
            
        except Exception as e:
            logger.error(f"Failed to process analysis result {analysis_result.analysis_id}: {str(e)}")
            raise
    
    def embed_source_summaries(
        self, 
        summaries: Dict[str, Any], 
        analysis_id: str,
        group_name: Optional[str] = None # <-- 이 파라미터 추가
    ) -> Dict[str, Any]:
        """
        소스코드 요약 결과를 embedding하고 Chroma에 저장
        
        Args:
            summaries: 소스코드 요약 결과
            analysis_id: 분석 ID
            
        Returns:
            처리 결과 정보
        """
        try:
            if not summaries or "summaries" not in summaries:
                logger.warning(f"No summaries found for analysis {analysis_id}")
                return {"status": "no_summaries", "count": 0}
            
            documents = []
            file_summaries = summaries["summaries"]
            
            import hashlib
            ids: List[str] = []
            for file_path, summary_data in file_summaries.items():
                if not summary_data or "summary" not in summary_data:
                    continue
                
                # Chunk summary content
                summary_text = summary_data.get("summary", "")
                chunks = self.text_splitter.split_text(summary_text) if summary_text else []
                total = max(len(chunks), 1)
                if not chunks:
                    chunks = [summary_text]
                for idx, chunk in enumerate(chunks):
                    meta = {
                        "analysis_id": analysis_id,
                        "source_type": "source_summary",
                        "file_path": file_path,
                        "file_name": summary_data.get("file_name", ""),
                        "language": summary_data.get("language", "Unknown"),
                        "file_size": summary_data.get("file_size", 0),
                        "tokens_used": summary_data.get("tokens_used", 0),
                        "summarized_at": summary_data.get("summarized_at", ""),
                        "model_used": summary_data.get("model_used", ""),
                        "file_hash": summary_data.get("file_hash", ""),
                        "chunk_index": idx,
                        "total_chunks": total
                    }
                    if group_name:
                        meta["group_name"] = group_name
                    documents.append(Document(page_content=chunk, metadata=meta))
                    # Stable ID per file+chunk
                    base = f"{analysis_id}|{file_path}|{summary_data.get('file_hash','')}|{idx}"
                    ids.append(hashlib.sha1(base.encode('utf-8')).hexdigest())
            
            if not documents:
                logger.warning(f"No valid summary documents created for analysis {analysis_id}")
                return {"status": "no_valid_summaries", "count": 0}
            
            # 문서들을 Chroma에 저장
            doc_ids = self.vectorstore.add_documents(documents, ids=ids if ids else None)
            
            logger.info(f"Successfully embedded {len(documents)} source summary documents for analysis {analysis_id}")
            
            return {
                "status": "success",
                "count": len(documents),
                "document_ids": doc_ids,
                "analysis_id": analysis_id,
                "source_type": "source_summary"
            }
            
        except Exception as e:
            logger.error(f"Failed to embed source summaries for analysis {analysis_id}: {str(e)}")
            raise
    
    def _create_documents_from_analysis(self, analysis_result: AnalysisResult) -> List[Document]:
        """
        분석 결과로부터 Document 객체들을 생성
        
        Args:
            analysis_result: 분석 결과 객체
            
        Returns:
            Document 객체 리스트
        """
        documents = []
        
        for repo_analysis in analysis_result.repositories:
            # 1. 레포지토리 기본 정보 문서
            repo_summary = self._create_repository_summary(repo_analysis)
            if repo_summary:
                documents.append(Document(
                    page_content=repo_summary,
                    metadata={
                        "analysis_id": analysis_result.analysis_id,
                        "repository_url": str(repo_analysis.repository.url),
                        "repository_name": repo_analysis.repository.name or "unknown",
                        "document_type": "repository_summary",
                        "created_at": analysis_result.created_at.isoformat() if analysis_result.created_at else None,
                        "group_name": getattr(analysis_result, 'group_name', None)
                    }
                ))
            
            # 2. 기술스펙 문서들
            for tech_spec in repo_analysis.tech_specs:
                tech_content = self._create_tech_spec_content(tech_spec)
                if tech_content:
                    documents.append(Document(
                        page_content=tech_content,
                        metadata={
                            "analysis_id": analysis_result.analysis_id,
                            "repository_url": str(repo_analysis.repository.url),
                            "repository_name": repo_analysis.repository.name or "unknown",
                            "document_type": "tech_spec",
                            "language": tech_spec.language,
                            "package_manager": tech_spec.package_manager,
                            "group_name": getattr(analysis_result, 'group_name', None)
                        }
                ))
            
            # 3. AST 분석 결과 문서들
            for file_path, ast_nodes in repo_analysis.ast_analysis.items():
                ast_content = self._create_ast_content(file_path, ast_nodes)
                if ast_content:
                    # 큰 AST 내용은 청크로 분할
                    chunks = self.text_splitter.split_text(ast_content)
                    for i, chunk in enumerate(chunks):
                        documents.append(Document(
                            page_content=chunk,
                            metadata={
                                "analysis_id": analysis_result.analysis_id,
                                "repository_url": str(repo_analysis.repository.url),
                                "repository_name": repo_analysis.repository.name or "unknown",
                                "document_type": "ast_analysis",
                                "file_path": file_path,
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            }
                        ))
            
            # 4. 코드 메트릭 문서
            metrics_content = self._create_metrics_content(repo_analysis)
            if metrics_content:
                documents.append(Document(
                    page_content=metrics_content,
                    metadata={
                        "analysis_id": analysis_result.analysis_id,
                        "repository_url": str(repo_analysis.repository.url),
                        "repository_name": repo_analysis.repository.name or "unknown",
                        "document_type": "code_metrics"
                    }
                ))
        
        # 5. 연관도 분석 문서
        if analysis_result.correlation_analysis:
            correlation_content = self._create_correlation_content(analysis_result.correlation_analysis)
            if correlation_content:
                documents.append(Document(
                    page_content=correlation_content,
                    metadata={
                        "analysis_id": analysis_result.analysis_id,
                        "document_type": "correlation_analysis",
                        "repository_count": len(analysis_result.repositories),
                        "group_name": getattr(analysis_result, 'group_name', None)
                    }
                ))
        
        return documents
    
    def _create_repository_summary(self, repo_analysis: RepositoryAnalysis) -> str:
        """레포지토리 요약 텍스트 생성"""
        summary_parts = []
        
        # 기본 정보
        summary_parts.append(f"Repository: {repo_analysis.repository.name or 'Unknown'}")
        summary_parts.append(f"URL: {repo_analysis.repository.url}")
        if repo_analysis.repository.branch:
            summary_parts.append(f"Branch: {repo_analysis.repository.branch}")
        
        # 파일 통계
        if repo_analysis.files:
            file_count = len(repo_analysis.files)
            languages = set(f.language for f in repo_analysis.files if f.language)
            summary_parts.append(f"Total files: {file_count}")
            if languages:
                summary_parts.append(f"Languages: {', '.join(sorted(languages))}")
        
        # 문서 파일들
        if repo_analysis.documentation_files:
            summary_parts.append(f"Documentation files: {', '.join(repo_analysis.documentation_files)}")
        
        # 설정 파일들
        if repo_analysis.config_files:
            summary_parts.append(f"Configuration files: {', '.join(repo_analysis.config_files)}")
        
        return "\n".join(summary_parts)
    
    def _create_tech_spec_content(self, tech_spec) -> str:
        """기술스펙 내용 생성"""
        content_parts = []
        
        content_parts.append(f"Language: {tech_spec.language}")
        if tech_spec.package_manager:
            content_parts.append(f"Package Manager: {tech_spec.package_manager}")
        
        if tech_spec.dependencies:
            content_parts.append("Dependencies:")
            for dep in tech_spec.dependencies:
                content_parts.append(f"  - {dep}")
        
        return "\n".join(content_parts)
    
    def _create_ast_content(self, file_path: str, ast_nodes: List[ASTNode]) -> str:
        """AST 분석 내용 생성"""
        content_parts = []
        
        content_parts.append(f"File: {file_path}")
        content_parts.append("AST Analysis:")
        
        for node in ast_nodes:
            node_info = f"  {node.type}"
            if node.name:
                node_info += f" '{node.name}'"
            if node.line_start:
                if node.line_end and node.line_end != node.line_start:
                    node_info += f" (lines {node.line_start}-{node.line_end})"
                else:
                    node_info += f" (line {node.line_start})"
            content_parts.append(node_info)
            
            if node.metadata:
                for key, value in node.metadata.items():
                    content_parts.append(f"    {key}: {value}")
        
        return "\n".join(content_parts)
    
    def _create_metrics_content(self, repo_analysis: RepositoryAnalysis) -> str:
        """코드 메트릭 내용 생성"""
        if not repo_analysis.code_metrics:
            return ""
        
        metrics = repo_analysis.code_metrics
        content_parts = []
        
        content_parts.append("Code Metrics:")
        content_parts.append(f"  Lines of code: {metrics.lines_of_code}")
        if hasattr(metrics, 'total_files'):
            content_parts.append(f"  Total files: {metrics.total_files}")
        if hasattr(metrics, 'average_file_size'):
            content_parts.append(f"  Average file size: {metrics.average_file_size:.2f} lines")
        if metrics.cyclomatic_complexity:
            content_parts.append(f"  Cyclomatic complexity: {metrics.cyclomatic_complexity:.2f}")
        if metrics.maintainability_index:
            content_parts.append(f"  Maintainability index: {metrics.maintainability_index:.2f}")
        if metrics.comment_ratio:
            content_parts.append(f"  Comment ratio: {metrics.comment_ratio:.2f}")
        
        if hasattr(metrics, 'language_distribution') and metrics.language_distribution:
            content_parts.append("  Language distribution:")
            for lang, count in metrics.language_distribution.items():
                content_parts.append(f"    {lang}: {count} files")
        
        return "\n".join(content_parts)
    
    def _create_correlation_content(self, correlation_analysis) -> str:
        """연관도 분석 내용 생성"""
        content_parts = []
        
        content_parts.append("Repository Correlation Analysis:")
        
        if correlation_analysis.common_dependencies:
            content_parts.append("Common Dependencies:")
            for dep in correlation_analysis.common_dependencies:
                content_parts.append(f"  - {dep}")
        
        if correlation_analysis.shared_technologies:
            content_parts.append("Shared Technologies:")
            for tech in correlation_analysis.shared_technologies:
                content_parts.append(f"  - {tech}")
        
        if correlation_analysis.architecture_similarity > 0:
            content_parts.append(f"Architecture Similarity Score: {correlation_analysis.architecture_similarity:.2f}")
        
        return "\n".join(content_parts)
    
    def search_similar_documents(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None, repository_url: Optional[str] = None) -> List[Dict]:
        """
        유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            filter_metadata: 메타데이터 필터
            repository_url: 특정 레포지토리 URL (최신 commit 분석 결과 우선 검색)
            
        Returns:
            유사한 문서들과 점수
        """
        try:
            # 특정 레포지토리의 최신 commit 분석 결과를 우선 검색
            if repository_url and not filter_metadata:
                latest_analysis_id = self._get_latest_analysis_for_repository(repository_url)
                if latest_analysis_id:
                    filter_metadata = {"analysis_id": latest_analysis_id}
                    logger.info(f"Searching with latest analysis for repository {repository_url}: {latest_analysis_id}")
            
            # 필터 적용하여 검색 (초기 후보 확장)
            from config.settings import settings as _settings
            rerank_multiplier = int(getattr(_settings, "RERANK_MULTIPLIER", 5))
            rerank_max_candidates = int(getattr(_settings, "RERANK_MAX_CANDIDATES", 30))
            initial_k = min(max(k * rerank_multiplier, k), rerank_max_candidates)
            if filter_metadata:
                initial_results = self.vectorstore.similarity_search_with_score(
                    query, k=initial_k, filter=filter_metadata
                )
            else:
                initial_results = self.vectorstore.similarity_search_with_score(query, k=initial_k)
            
            if not initial_results:
                return []

            # LLM 기반 리랭킹 (옵션)
            reranked_results = []
            documents_to_rerank = []
            # 트렁케이션 길이
            rerank_content_chars = int(getattr(_settings, "RERANK_CONTENT_CHARS", 1000))
            for i, (doc, original_score) in enumerate(initial_results):
                documents_to_rerank.append({
                    "index": i,
                    "content": (doc.page_content[:rerank_content_chars] if doc.page_content else ""),
                    "metadata": doc.metadata,
                    "original_score": original_score
                })
            
            # LLM 리랭킹 비활성화 시, 원본 점수로 정렬 반환
            if not getattr(_settings, "ENABLE_RERANKING", False) or not self.llm_client:
                reranked_results = [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "original_score": score,
                        "rerank_score": score
                    }
                    for doc, score in initial_results
                ]
                reranked_results.sort(key=lambda x: x["original_score"], reverse=True)
                return reranked_results[:k]

            # LLM에 리랭킹 요청 프롬프트 구성
            prompt_messages = [
                {"role": "system", "content": "You rerank documents by relevance to a query. Respond with a JSON array of objects, each with 'index' and 'rerank_score' (0-1)."},
                {"role": "user", "content": f"Query: {query}\n\nDocuments to rerank (JSON array of objects with 'index' and 'content'):\n{json.dumps(documents_to_rerank, ensure_ascii=False)}\n\nReturn only JSON array with 'index' and 'rerank_score'."}
            ]

            try:
                llm_model = getattr(_settings, "RERANK_MODEL", "gpt-4o-mini")
                llm_response = self.llm_client.chat.completions.create(
                    model=llm_model, # 리랭킹에 사용할 LLM 모델
                    messages=prompt_messages,
                    temperature=0.0, # 리랭킹은 창의성보다 정확성이 중요
                    max_tokens=1024 # 충분한 응답 길이
                )
                
                # LLM 응답 파싱
                rerank_output = llm_response.choices[0].message.content
                rerank_scores_list = json.loads(rerank_output)

                # 원본 문서와 리랭크 점수를 결합
                for item in rerank_scores_list:
                    original_doc_info = documents_to_rerank[item["index"]]
                    reranked_results.append({
                        "content": original_doc_info["content"],
                        "metadata": original_doc_info["metadata"],
                        "original_score": original_doc_info["original_score"],
                        "rerank_score": item["rerank_score"]
                    })
                
                # 리랭크 점수를 기준으로 내림차순 정렬하고 상위 k개 선택
                reranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)

            except Exception as llm_e:
                logger.error(f"LLM reranking failed, falling back to original scores: {llm_e}")
                # LLM 리랭킹 실패 시 원래 유사도 점수를 사용
                reranked_results = [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "original_score": score,
                        "rerank_score": score # 리랭크 실패 시 원래 점수를 리랭크 점수로 사용
                    }
                    for doc, score in initial_results
                ]
                reranked_results.sort(key=lambda x: x["original_score"], reverse=True)

            return reranked_results[:k]
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def search_source_summaries(
        self, 
        query: str, 
        analysis_id: Optional[str] = None,
        k: int = 5,
        language_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        소스코드 요약에서 검색
        
        Args:
            query: 검색 쿼리
            analysis_id: 특정 분석 ID로 필터링 (선택사항)
            k: 반환할 결과 수
            language_filter: 특정 언어로 필터링 (선택사항)
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 필터 조건 구성
            filter_dict = {"source_type": "source_summary"}
            
            if analysis_id:
                filter_dict["analysis_id"] = analysis_id
                
            if language_filter:
                filter_dict["language"] = language_filter
            
            # 검색 수행
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            # 결과 포맷팅
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score,
                    "file_path": doc.metadata.get("file_path", ""),
                    "language": doc.metadata.get("language", "Unknown"),
                    "file_name": doc.metadata.get("file_name", "")
                })
            
            logger.info(f"Found {len(formatted_results)} source summary results for query: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search source summaries: {str(e)}")
            return []
    
    def _get_latest_analysis_for_repository(self, repository_url: str) -> Optional[str]:
        """
        특정 레포지토리의 최신 commit 분석 ID를 가져옵니다.
        
        Args:
            repository_url: 레포지토리 URL
            
        Returns:
            최신 분석 ID 또는 None
        """
        try:
            from core.database import SessionLocal, RepositoryAnalysis, RepositoryStatus
            
            with SessionLocal() as db:
                # 해당 레포지토리의 완료된 분석 중 최신 것을 가져오기 (commit_date 기준)
                # MariaDB/MySQL에서는 NULLS LAST 대신 CASE WHEN을 사용
                from sqlalchemy import case
                latest_analysis = db.query(RepositoryAnalysis).filter(
                    RepositoryAnalysis.repository_url == repository_url,
                    RepositoryAnalysis.status == RepositoryStatus.COMPLETED
                ).order_by(
                    case(
                        (RepositoryAnalysis.commit_date.is_(None), 1),
                        else_=0
                    ),  # NULL 값을 마지막으로
                    RepositoryAnalysis.commit_date.desc(),  # commit_date가 있는 것을 우선
                    RepositoryAnalysis.updated_at.desc()  # 그 다음은 업데이트 시간 기준
                ).first()
                
                if latest_analysis:
                    logger.info(f"Found latest analysis for {repository_url}: {latest_analysis.analysis_id} (commit: {latest_analysis.commit_hash[:8] if latest_analysis.commit_hash else 'unknown'})")
                    return latest_analysis.analysis_id
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get latest analysis for repository {repository_url}: {e}")
            return None
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보 반환"""
        try:
            # Chroma 컬렉션 정보 가져오기
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                "total_documents": count
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

    def get_all_group_names(self) -> List[str]:
        """DB에 저장된 모든 유니크한 group_name을 반환합니다."""
        try:
            collection = self.vectorstore._collection
            # include=['metadatas'] 를 사용하여 메타데이터만 가져옵니다.
            results = collection.get(include=["metadatas"])
            
            group_names = set()
            for metadata in results.get('metadatas', []):
                if metadata and 'group_name' in metadata:
                    group_names.add(metadata['group_name'])
            
            logger.info(f"Found {len(group_names)} unique group names.")
            return sorted(list(group_names))
        except Exception as e:
            logger.error(f"Failed to get all group names: {e}")
            return []

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
