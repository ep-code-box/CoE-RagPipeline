import logging
import os
import json
from typing import List, Dict, Any

from services.llm_service import LLMDocumentService, DocumentType as LLMDocumentType
from services.source_summary_service import SourceSummaryService
from services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

class DocumentGenerationService:
    """분석 완료 후 문서 생성을 담당하는 서비스"""

    def __init__(self):
        pass

    async def generate_documents(self, analysis_id: str, analysis_result):
        """분석 완료 후 LLM을 사용하여 문서를 자동 생성합니다 (소스코드 요약 포함)."""
        try:
            logger.info(f"Starting document generation for analysis {analysis_id}")
            
            llm_service = LLMDocumentService()
            summary_service = SourceSummaryService()
            embedding_service = get_embedding_service()
            
            # --- 1. Gather Raw Analysis Data ---
            analysis_data = {
                "analysis_id": analysis_id,
                "repositories": [],
                "tech_specs": [],
                "ast_analysis": {},
                "code_metrics": {}
            }
            clone_paths = []
            if hasattr(analysis_result, 'repositories') and analysis_result.repositories:
                for repo in analysis_result.repositories:
                    analysis_data["repositories"].append({
                        "url": str(repo.repository.url) if hasattr(repo, 'repository') else "Unknown",
                        "branch": repo.repository.branch if hasattr(repo, 'repository') else "main",
                        "name": repo.repository.name if hasattr(repo, 'repository') else None
                    })
                    if hasattr(repo, 'clone_path') and repo.clone_path:
                        clone_paths.append(repo.clone_path)
                    if hasattr(repo, 'tech_specs') and repo.tech_specs:
                        analysis_data["tech_specs"].extend([spec.dict() for spec in repo.tech_specs])
                    if hasattr(repo, 'ast_analysis'):
                        analysis_data["ast_analysis"].update(repo.ast_analysis)
                    if hasattr(repo, 'code_metrics') and hasattr(repo.code_metrics, 'dict'):
                        analysis_data["code_metrics"].update(repo.code_metrics.dict())

            # --- 2. Get Source Summaries ---
            source_summaries = None
            if clone_paths:
                try:
                    logger.info(f"Starting source code summarization for analysis {analysis_id}")
                    from config.settings import settings as _settings
                    source_summaries = await summary_service.summarize_repository_sources(
                        clone_path=clone_paths[0],
                        analysis_id=analysis_id,
                        max_files=_settings.SUMMARY_MAX_FILES_DEFAULT,
                        batch_size=_settings.SUMMARY_BATCH_SIZE_DEFAULT
                    )
                    if source_summaries and source_summaries.get("summaries"):
                        embedding_service.embed_source_summaries(
                            summaries=source_summaries,
                            analysis_id=analysis_id,
                            group_name=getattr(analysis_result, 'group_name', None)
                        )
                        logger.info(f"Source summaries embedded for analysis {analysis_id}")
                except Exception as e:
                    logger.error(f"Failed to summarize source code for analysis {analysis_id}: {str(e)}")
                    source_summaries = None

            # --- 3. Generate Documents ---
            default_document_types = [
                LLMDocumentType.DEVELOPMENT_GUIDE,
                LLMDocumentType.TECHNICAL_SPECIFICATION,
                LLMDocumentType.ARCHITECTURE_OVERVIEW
            ]
            
            if source_summaries and source_summaries.get("summaries"):
                 generated_documents = await llm_service.generate_documents_with_source_summaries(
                     analysis_data=analysis_data,
                     analysis_id=analysis_id,
                     document_types=default_document_types,
                     language="korean"
                 )
            else:
                generated_documents = await llm_service.generate_multiple_documents(
                    analysis_data=analysis_data,
                    document_types=default_document_types,
                    language="korean"
                )

            # --- 4. Save Documents ---
            documents_dir = f"output/documents/{analysis_id}"
            os.makedirs(documents_dir, exist_ok=True)
            
            for doc in generated_documents:
                if "error" not in doc:
                    doc_filename = f"{doc.get('document_type', 'unknown')}_{doc.get('language', 'unknown')}.md"
                    doc_path = os.path.join(documents_dir, doc_filename)
                    with open(doc_path, 'w', encoding='utf-8') as f:
                        f.write(doc.get('content', ''))
                    logger.info(f"Document saved: {doc_path}")
                else:
                    logger.error(f"Failed to generate document {doc.get('document_type')}: {doc.get('error')}")

            analysis_result.generated_documents = generated_documents
            if hasattr(analysis_result, 'source_summaries_used'):
                analysis_result.source_summaries_used = source_summaries is not None
            
            logger.info(f"Document generation process completed for analysis {analysis_id}.")

        except Exception as e:
            logger.error(f"Document generation failed for analysis {analysis_id}: {e}", exc_info=True)
            raise
