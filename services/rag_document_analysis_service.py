import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from core.database import DocumentAnalysis, DocumentType

logger = logging.getLogger(__name__)

class RagDocumentAnalysisService:
    """RAG 문서 분석 관리 서비스"""
    
    @staticmethod
    def create_document_analyses_batch(
        db: Session,
        repository_analysis_id: int,
        documents_data: List[Dict[str, Any]]
    ) -> List[DocumentAnalysis]:
        """문서 분석들을 배치로 생성합니다."""
        try:
            db_documents = []
            for doc_data in documents_data:
                db_document = DocumentAnalysis(
                    repository_analysis_id=repository_analysis_id,
                    document_path=doc_data.get('path', ''),
                    document_type=DocumentType(doc_data.get('type', 'other')),
                    title=doc_data.get('title'),
                    content=doc_data.get('content'),
                    extracted_sections=doc_data.get('extracted_sections', {}),
                    code_examples=doc_data.get('code_examples', {}),
                    api_endpoints=doc_data.get('api_endpoints', {})
                )
                db_documents.append(db_document)
            
            db.add_all(db_documents)
            db.commit()
            
            for db_document in db_documents:
                db.refresh(db_document)
            
            return db_documents
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create document analyses batch: {str(e)}")