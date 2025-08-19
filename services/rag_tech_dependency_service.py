import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from core.database import TechDependency, DependencyType

logger = logging.getLogger(__name__)

class RagTechDependencyService:
    """RAG 기술 의존성 관리 서비스"""
    
    @staticmethod
    def create_tech_dependencies_batch(
        db: Session,
        repository_analysis_id: int,
        dependencies_data: List[Dict[str, Any]]
    ) -> List[TechDependency]:
        """기술 의존성들을 배치로 생성합니다."""
        try:
            db_dependencies = []
            for dep_data in dependencies_data:
                db_dependency = TechDependency(
                    repository_analysis_id=repository_analysis_id,
                    dependency_type=DependencyType(dep_data.get('type', 'library')),
                    name=dep_data.get('name', ''),
                    version=dep_data.get('version'),
                    package_manager=dep_data.get('package_manager'),
                    is_dev_dependency=dep_data.get('is_dev_dependency', False),
                    license=dep_data.get('license'),
                    vulnerability_count=dep_data.get('vulnerability_count', 0)
                )
                db_dependencies.append(db_dependency)
            
            db.add_all(db_dependencies)
            db.commit()
            
            for db_dependency in db_dependencies:
                db.refresh(db_dependency)
            
            return db_dependencies
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create tech dependencies batch: {str(e)}")