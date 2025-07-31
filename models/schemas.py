from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GitRepository(BaseModel):
    url: HttpUrl
    branch: Optional[str] = "main"
    name: Optional[str] = None


class AnalysisRequest(BaseModel):
    repositories: List[GitRepository]
    analysis_id: Optional[str] = None
    include_ast: bool = True
    include_tech_spec: bool = True
    include_correlation: bool = True


class FileInfo(BaseModel):
    path: str
    size: int
    language: Optional[str] = None
    lines_of_code: Optional[int] = None


class ASTNode(BaseModel):
    type: str
    name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    children: List['ASTNode'] = []
    metadata: Dict[str, Any] = {}


class TechSpec(BaseModel):
    language: str
    framework: Optional[str] = None
    dependencies: List[str] = []
    version: Optional[str] = None
    package_manager: Optional[str] = None


class CodeMetrics(BaseModel):
    cyclomatic_complexity: Optional[float] = None
    maintainability_index: Optional[float] = None
    lines_of_code: int = 0
    comment_ratio: Optional[float] = None


class RepositoryAnalysis(BaseModel):
    repository: GitRepository
    clone_path: str
    files: List[FileInfo] = []
    ast_analysis: Dict[str, List[ASTNode]] = {}
    tech_specs: List[TechSpec] = []
    code_metrics: CodeMetrics = CodeMetrics()
    documentation_files: List[str] = []
    config_files: List[str] = []


class CorrelationAnalysis(BaseModel):
    common_dependencies: List[str] = []
    similar_patterns: List[Dict[str, Any]] = []
    architecture_similarity: float = 0.0
    shared_technologies: List[str] = []


class AnalysisResult(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    repositories: List[RepositoryAnalysis] = []
    correlation_analysis: Optional[CorrelationAnalysis] = None
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)


# Update forward references
ASTNode.model_rebuild()