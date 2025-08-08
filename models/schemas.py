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
    include_ast: bool = True
    include_tech_spec: bool = True
    include_correlation: bool = True
    group_name: Optional[str] = None # <-- 이 줄 추가


class FileInfo(BaseModel):
    path: str
    size: int
    language: Optional[str] = None
    lines_of_code: Optional[int] = None
    framework: Optional[str] = None  # 프레임워크 정보 추가


class ASTNode(BaseModel):
    """AST 노드 정보를 담는 모델"""
    type: str
    name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    children: List['ASTNode'] = []
    metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """ASTNode를 딕셔너리로 변환"""
        return {
            "type": self.type,
            "name": self.name,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }


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
    ast_metrics: Dict[str, Any] = {}


class RepositoryAnalysis(BaseModel):
    repository: GitRepository
    clone_path: str
    files: List[FileInfo] = []
    ast_analysis: Dict[str, List[ASTNode]] = {}
    tech_specs: List[TechSpec] = []
    code_metrics: CodeMetrics = CodeMetrics()
    documentation_files: List[str] = []
    config_files: List[str] = []
    commit_info: Dict[str, Any] = {}
    enhanced_analysis: Optional[Dict[str, Any]] = {}


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
    group_name: Optional[str] = None # <-- 이 줄 추가
    repositories: List[RepositoryAnalysis] = []
    correlation_analysis: Optional[CorrelationAnalysis] = None
    error_message: Optional[str] = None
    generated_documents: List['GeneratedDocument'] = []
    source_summaries_used: Optional[bool] = False


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)


# Document Generation Schemas
class DocumentGenerationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentGenerationRequest(BaseModel):
    analysis_id: str = Field(..., description="분석 ID")
    document_types: List[str] = Field(..., description="생성할 문서 타입 목록")
    language: str = Field(default="korean", description="문서 언어 (korean/english)")
    custom_prompt: Optional[str] = Field(None, description="사용자 정의 프롬프트")


class GeneratedDocument(BaseModel):
    document_type: str = Field(..., description="문서 타입")
    language: str = Field(..., description="문서 언어")
    file_path: str = Field(..., description="저장된 파일 경로")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    created_at: datetime = Field(..., description="생성 시간")
    analysis_id: str = Field(..., description="분석 ID")
    tokens_used: Optional[int] = Field(None, description="사용된 토큰 수")


class DocumentGenerationResponse(BaseModel):
    task_id: str = Field(..., description="작업 ID")
    status: DocumentGenerationStatus = Field(..., description="작업 상태")
    message: str = Field(..., description="상태 메시지")
    analysis_id: str = Field(..., description="분석 ID")
    document_types: List[str] = Field(..., description="요청된 문서 타입 목록")
    language: str = Field(..., description="문서 언어")
    created_at: Optional[datetime] = Field(None, description="작업 생성 시간")
    completed_at: Optional[datetime] = Field(None, description="작업 완료 시간")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    generated_documents: List[GeneratedDocument] = Field(default=[], description="생성된 문서 목록")


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    filter_metadata: Optional[Dict[str, Any]] = None
    analysis_id: Optional[str] = None
    repository_url: Optional[str] = None
    group_name: Optional[str] = None


# Update forward references
ASTNode.model_rebuild()