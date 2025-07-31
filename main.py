import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import (
    AnalysisRequest, 
    AnalysisResult, 
    AnalysisStatus, 
    HealthResponse,
    RepositoryAnalysis,
    CorrelationAnalysis,
    CodeMetrics,
    TechSpec
)
from analyzers.git_analyzer import GitAnalyzer
from analyzers.ast_analyzer import ASTAnalyzer
from services.embedding_service import EmbeddingService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="CoE RAG Pipeline",
    description="Git 레포지토리들을 분석하여 레포지토리간 연관도, AST 분석, 기술스펙 정적 분석을 수행하는 RAG 파이프라인",
    version="1.0.0"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 분석 결과 저장소 및 영구 저장 설정
RESULTS_DIR = "output/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

analysis_results: Dict[str, AnalysisResult] = {}

def save_analysis_result(analysis_id: str, result: AnalysisResult):
    """분석 결과를 JSON 파일로 저장"""
    try:
        file_path = os.path.join(RESULTS_DIR, f"{analysis_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            # Pydantic 모델을 dict로 변환하여 저장
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Analysis result saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save analysis result {analysis_id}: {e}")

def load_analysis_result(analysis_id: str) -> AnalysisResult:
    """JSON 파일에서 분석 결과를 로드"""
    try:
        file_path = os.path.join(RESULTS_DIR, f"{analysis_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return AnalysisResult(**data)
    except Exception as e:
        logger.error(f"Failed to load analysis result {analysis_id}: {e}")
    return None

def load_all_analysis_results():
    """모든 저장된 분석 결과를 메모리로 로드"""
    global analysis_results
    try:
        for filename in os.listdir(RESULTS_DIR):
            if filename.endswith('.json'):
                analysis_id = filename[:-5]  # .json 제거
                result = load_analysis_result(analysis_id)
                if result:
                    analysis_results[analysis_id] = result
        logger.info(f"Loaded {len(analysis_results)} analysis results from disk")
    except Exception as e:
        logger.error(f"Failed to load analysis results: {e}")

# 서버 시작 시 기존 결과 로드
load_all_analysis_results()

# 데이터베이스 초기화
try:
    from database import init_database
    init_database()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    logger.warning("Continuing without database support")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    return HealthResponse(status="healthy", timestamp=datetime.now())


@app.post("/analyze", response_model=dict)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Git 주소 목록을 받아 전체 분석 수행"""
    # 분석 ID 생성
    analysis_id = request.analysis_id or str(uuid.uuid4())
    
    # 분석 결과 초기화
    analysis_result = AnalysisResult(
        analysis_id=analysis_id,
        status=AnalysisStatus.PENDING,
        created_at=datetime.now(),
        repositories=[],
        correlation_analysis=None
    )
    
    analysis_results[analysis_id] = analysis_result
    
    # 백그라운드에서 분석 실행
    background_tasks.add_task(perform_analysis, analysis_id, request)
    
    return {
        "analysis_id": analysis_id,
        "status": "started",
        "message": "분석이 시작되었습니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요."
    }


@app.get("/results/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_result(analysis_id: str):
    """분석 결과 조회"""
    # 먼저 메모리에서 확인
    if analysis_id in analysis_results:
        return analysis_results[analysis_id]
    
    # 메모리에 없으면 디스크에서 로드 시도
    result = load_analysis_result(analysis_id)
    if result:
        analysis_results[analysis_id] = result  # 메모리에 캐시
        return result
    
    # 둘 다 없으면 404 에러
    available_ids = list(analysis_results.keys())
    error_detail = {
        "message": "분석 결과를 찾을 수 없습니다.",
        "analysis_id": analysis_id,
        "available_analysis_ids": available_ids[:5],  # 최대 5개만 표시
        "total_available": len(available_ids),
        "suggestions": [
            "1. 올바른 analysis_id를 사용하고 있는지 확인하세요.",
            "2. /results 엔드포인트로 사용 가능한 분석 결과 목록을 확인하세요.",
            "3. 분석이 아직 진행 중이거나 실패했을 수 있습니다.",
            "4. 분석 ID 형식이 올바른지 확인하세요 (UUID 형식)."
        ]
    }
    raise HTTPException(status_code=404, detail=error_detail)


@app.get("/results", response_model=List[dict])
async def list_analysis_results():
    """모든 분석 결과 목록 조회"""
    return [
        {
            "analysis_id": result.analysis_id,
            "status": result.status,
            "created_at": result.created_at,
            "completed_at": result.completed_at,
            "repository_count": len(result.repositories)
        }
        for result in analysis_results.values()
    ]


@app.post("/search", response_model=List[dict])
async def search_embeddings(query: str, k: int = 5, filter_metadata: Optional[Dict] = None):
    """Chroma 벡터 데이터베이스에서 유사한 문서 검색"""
    try:
        chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        embedding_service = EmbeddingService(chroma_persist_directory=chroma_persist_dir)
        results = embedding_service.search_similar_documents(query, k=k, filter_metadata=filter_metadata)
        return results
    except Exception as e:
        logger.error(f"Failed to search embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@app.get("/embeddings/stats", response_model=dict)
async def get_embedding_stats():
    """Chroma 벡터 데이터베이스 통계 정보 조회"""
    try:
        chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        embedding_service = EmbeddingService(chroma_persist_directory=chroma_persist_dir)
        stats = embedding_service.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")


async def perform_analysis(analysis_id: str, request: AnalysisRequest):
    """실제 분석 수행 (백그라운드 태스크)"""
    try:
        # 분석 상태 업데이트
        analysis_results[analysis_id].status = AnalysisStatus.RUNNING
        logger.info(f"Starting analysis {analysis_id} for {len(request.repositories)} repositories")
        
        # Git 분석기 초기화
        git_analyzer = GitAnalyzer()
        ast_analyzer = ASTAnalyzer()
        
        repository_analyses = []
        
        # 각 레포지토리 분석
        for repo in request.repositories:
            try:
                logger.info(f"Analyzing repository: {repo.url}")
                
                # 1. Git 클론
                clone_path = git_analyzer.clone_repository(repo)
                
                # 2. 파일 구조 분석
                files = git_analyzer.analyze_repository_structure(clone_path)
                
                # 3. AST 분석 (옵션)
                ast_analysis = {}
                if request.include_ast:
                    ast_analysis = ast_analyzer.analyze_files(clone_path, files)
                
                # 4. 기술스펙 분석 (옵션)
                tech_specs = []
                if request.include_tech_spec:
                    tech_specs = analyze_tech_specs(clone_path, files)
                
                # 5. 코드 메트릭 계산
                code_metrics = calculate_code_metrics(files)
                
                # 6. 문서 파일 찾기
                doc_files = find_documentation_files(files)
                config_files = find_config_files(files)
                
                # 레포지토리 분석 결과 생성
                repo_analysis = RepositoryAnalysis(
                    repository=repo,
                    clone_path=clone_path,
                    files=files,
                    ast_analysis=ast_analysis,
                    tech_specs=tech_specs,
                    code_metrics=code_metrics,
                    documentation_files=doc_files,
                    config_files=config_files
                )
                
                repository_analyses.append(repo_analysis)
                logger.info(f"Completed analysis for repository: {repo.url}")
                
            except Exception as e:
                logger.error(f"Failed to analyze repository {repo.url}: {e}")
                # 실패한 레포지토리도 기록 (에러 정보와 함께)
                repo_analysis = RepositoryAnalysis(
                    repository=repo,
                    clone_path="",
                    files=[],
                    code_metrics=CodeMetrics()
                )
                repository_analyses.append(repo_analysis)
        
        # 7. 레포지토리간 연관도 분석 (옵션)
        correlation_analysis = None
        if request.include_correlation and len(repository_analyses) > 1:
            correlation_analysis = analyze_correlations(repository_analyses)
        
        # 분석 결과 업데이트
        analysis_results[analysis_id].repositories = repository_analyses
        analysis_results[analysis_id].correlation_analysis = correlation_analysis
        analysis_results[analysis_id].status = AnalysisStatus.COMPLETED
        analysis_results[analysis_id].completed_at = datetime.now()
        
        # 분석 결과를 디스크에 저장
        save_analysis_result(analysis_id, analysis_results[analysis_id])
        
        # 분석 결과를 데이터베이스에 저장
        try:
            from database import save_analysis_to_db
            save_analysis_to_db(analysis_results[analysis_id])
        except Exception as db_error:
            logger.error(f"Failed to save analysis {analysis_id} to database: {db_error}")
        
        # 분석 결과를 embedding하여 Chroma에 저장
        try:
            chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
            embedding_service = EmbeddingService(chroma_persist_directory=chroma_persist_dir)
            embedding_result = embedding_service.process_analysis_result(analysis_results[analysis_id])
            logger.info(f"Embedding result for analysis {analysis_id}: {embedding_result}")
        except Exception as embedding_error:
            logger.error(f"Failed to embed analysis {analysis_id}: {embedding_error}")
        
        # 정리
        git_analyzer.cleanup()
        
        logger.info(f"Analysis {analysis_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {e}")
        analysis_results[analysis_id].status = AnalysisStatus.FAILED
        analysis_results[analysis_id].error_message = str(e)
        analysis_results[analysis_id].completed_at = datetime.now()
        
        # 실패한 분석 결과도 저장
        save_analysis_result(analysis_id, analysis_results[analysis_id])
        
        # 실패한 분석 결과도 데이터베이스에 저장
        try:
            from database import save_analysis_to_db
            save_analysis_to_db(analysis_results[analysis_id])
        except Exception as db_error:
            logger.error(f"Failed to save failed analysis {analysis_id} to database: {db_error}")


def analyze_tech_specs(clone_path: str, files: List) -> List[TechSpec]:
    """기술스펙 분석"""
    tech_specs = []
    
    # 언어별 의존성 파일 찾기
    dependency_files = {
        'requirements.txt': 'Python',
        'package.json': 'JavaScript/Node.js',
        'pom.xml': 'Java/Maven',
        'build.gradle': 'Java/Gradle',
        'Cargo.toml': 'Rust',
        'go.mod': 'Go'
    }
    
    for file_info in files:
        filename = file_info.path.split('/')[-1]
        if filename in dependency_files:
            language = dependency_files[filename]
            dependencies = extract_dependencies(clone_path, file_info.path, language)
            
            tech_spec = TechSpec(
                language=language,
                dependencies=dependencies,
                package_manager=get_package_manager(filename)
            )
            tech_specs.append(tech_spec)
    
    return tech_specs


def extract_dependencies(clone_path: str, file_path: str, language: str) -> List[str]:
    """의존성 추출"""
    dependencies = []
    full_path = f"{clone_path}/{file_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if language == 'Python':
            # requirements.txt 파싱
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 버전 정보 제거
                    dep = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
                    dependencies.append(dep.strip())
                    
        elif language == 'JavaScript/Node.js':
            # package.json 파싱 (간단한 버전)
            import json
            try:
                data = json.loads(content)
                if 'dependencies' in data:
                    dependencies.extend(data['dependencies'].keys())
                if 'devDependencies' in data:
                    dependencies.extend(data['devDependencies'].keys())
            except json.JSONDecodeError:
                pass
                
    except Exception as e:
        logger.warning(f"Failed to extract dependencies from {file_path}: {e}")
    
    return dependencies


def get_package_manager(filename: str) -> str:
    """패키지 매니저 식별"""
    manager_map = {
        'requirements.txt': 'pip',
        'package.json': 'npm',
        'pom.xml': 'maven',
        'build.gradle': 'gradle',
        'Cargo.toml': 'cargo',
        'go.mod': 'go mod'
    }
    return manager_map.get(filename, 'unknown')


def calculate_code_metrics(files: List) -> CodeMetrics:
    """코드 메트릭 계산"""
    total_lines = sum(f.lines_of_code or 0 for f in files if f.lines_of_code)
    
    return CodeMetrics(
        lines_of_code=total_lines,
        cyclomatic_complexity=None,  # 추후 구현
        maintainability_index=None,  # 추후 구현
        comment_ratio=None  # 추후 구현
    )


def find_documentation_files(files: List) -> List[str]:
    """문서 파일 찾기"""
    doc_patterns = ['readme', 'doc', 'docs', '.md', '.rst', '.txt']
    doc_files = []
    
    for file_info in files:
        path_lower = file_info.path.lower()
        if any(pattern in path_lower for pattern in doc_patterns):
            doc_files.append(file_info.path)
    
    return doc_files


def find_config_files(files: List) -> List[str]:
    """설정 파일 찾기"""
    config_patterns = ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']
    config_files = []
    
    for file_info in files:
        path_lower = file_info.path.lower()
        if any(path_lower.endswith(pattern) for pattern in config_patterns):
            config_files.append(file_info.path)
    
    return config_files


def analyze_correlations(repository_analyses: List[RepositoryAnalysis]) -> CorrelationAnalysis:
    """레포지토리간 연관도 분석"""
    # 공통 의존성 찾기
    all_dependencies = []
    for repo_analysis in repository_analyses:
        for tech_spec in repo_analysis.tech_specs:
            all_dependencies.extend(tech_spec.dependencies)
    
    # 의존성 빈도 계산
    dependency_count = {}
    for dep in all_dependencies:
        dependency_count[dep] = dependency_count.get(dep, 0) + 1
    
    # 2개 이상의 레포지토리에서 사용되는 의존성
    common_dependencies = [dep for dep, count in dependency_count.items() if count > 1]
    
    # 공통 기술 스택
    all_languages = set()
    for repo_analysis in repository_analyses:
        for tech_spec in repo_analysis.tech_specs:
            all_languages.add(tech_spec.language)
    
    return CorrelationAnalysis(
        common_dependencies=common_dependencies,
        similar_patterns=[],  # 추후 구현
        architecture_similarity=0.0,  # 추후 구현
        shared_technologies=list(all_languages)
    )


def find_available_port(start_port: int = 8001, max_attempts: int = 10) -> int:
    """
    주어진 시작 포트부터 사용 가능한 포트를 찾아 반환합니다.
    
    Args:
        start_port: 검색을 시작할 포트 번호
        max_attempts: 최대 시도 횟수
        
    Returns:
        사용 가능한 포트 번호
        
    Raises:
        RuntimeError: 사용 가능한 포트를 찾지 못한 경우
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('127.0.0.1', port))
                logger.info(f"Found available port: {port}")
                return port
        except OSError:
            logger.debug(f"Port {port} is already in use, trying next port...")
            continue
    
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")


if __name__ == "__main__":
    try:
        # 사용 가능한 포트 찾기
        available_port = find_available_port(start_port=8001)
        logger.info(f"Starting server on port {available_port}")
        
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=available_port,
            reload=True,
            log_level="info"
        )
    except RuntimeError as e:
        logger.error(f"Failed to start server: {e}")
        logger.info("Please check if other processes are using ports in the range 8001-8010")
        exit(1)