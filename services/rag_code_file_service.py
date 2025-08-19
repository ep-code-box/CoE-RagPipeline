import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from core.database import CodeFile

logger = logging.getLogger(__name__)

class RagCodeFileService:
    """RAG 코드 파일 관리 서비스"""
    
    @staticmethod
    def create_code_files_batch(
        db: Session,
        repository_analysis_id: int,
        files_data: List[Dict[str, Any]]
    ) -> List[CodeFile]:
        """코드 파일들을 배치로 생성합니다."""
        try:
            db_code_files = []
            for file_data in files_data:
                db_code_file = CodeFile(
                    repository_analysis_id=repository_analysis_id,
                    file_path=file_data.get('path', ''),
                    file_name=file_data.get('name', ''),
                    file_size=file_data.get('size', 0),
                    language=file_data.get('language'),
                    lines_of_code=file_data.get('lines_of_code', 0),
                    complexity_score=file_data.get('complexity_score'),
                    last_modified=file_data.get('last_modified'),
                    file_hash=file_data.get('file_hash')
                )
                db_code_files.append(db_code_file)
            
            db.add_all(db_code_files)
            db.commit()
            
            for db_code_file in db_code_files:
                db.refresh(db_code_file)
            
            return db_code_files
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create code files batch: {str(e)}")