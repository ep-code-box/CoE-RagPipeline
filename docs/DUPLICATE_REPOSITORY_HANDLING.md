# 스마트 레포지토리 분석 및 분석별 RAG 검색 가이드

## 📋 개요

CoE RAG Pipeline에서 commit 기준 변경사항을 감지하여 스마트한 레포지토리 분석을 수행하고, 특정 분석 결과를 기준으로 RAG 검색을 수행하는 기능에 대한 상세 가이드입니다.

## 🔄 스마트 레포지토리 분석 (Commit 기반)

### 기능 설명

시스템은 분석 요청 시 다음과 같이 commit 기준으로 변경사항을 감지하고 처리합니다:

1. **Commit 기반 변경 감지**: 레포지토리 URL, 브랜치, **commit hash**를 기준으로 변경사항 확인
2. **스마트 분석 결정**: commit이 변경된 경우에만 새로운 분석 수행, 동일 commit은 기존 결과 재사용
3. **효율성 향상**: 불필요한 중복 분석을 방지하면서도 코드 변경사항은 정확히 반영

### 동작 방식

```python
# Commit 기반 스마트 분석 로직
for repo in request.repositories:
    repo_url = repo.url
    branch = getattr(repo, 'branch', 'main')
    
    try:
        # 1. 최신 commit 정보 가져오기
        latest_commit_info = git_analyzer.get_latest_commit_info(repo_url, branch)
        latest_commit_hash = latest_commit_info.get('commit_hash')
        
        # 2. Commit 기준 분석 필요 여부 확인
        analysis_needed, existing_analysis_id = RagRepositoryAnalysisService.check_if_analysis_needed(
            db, repo_url, branch, latest_commit_hash
        )
        
        if analysis_needed:
            # Commit이 변경되었거나 기존 분석이 없는 경우 새로운 분석
            new_repositories.append(repo)
            logger.info(f"New analysis needed for {repo_url}:{branch} - commit: {latest_commit_hash[:8]}")
        else:
            # 동일한 commit인 경우 기존 분석 결과 재사용
            existing_analysis_ids.append(existing_analysis_id)
            logger.info(f"Reusing existing analysis for {repo_url}:{branch}: {existing_analysis_id}")
            
    except Exception as e:
        # 에러 발생 시 안전하게 새로운 분석 수행
        logger.error(f"Error checking commit for {repo_url}: {e}")
        new_repositories.append(repo)
```

### Commit 비교 상세 로직

```python
@staticmethod
def check_if_analysis_needed(
    db: Session,
    repository_url: str,
    branch: str = "main",
    latest_commit_hash: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Commit hash를 기준으로 분석이 필요한지 확인합니다.
    
    Returns:
        tuple[bool, Optional[str]]: (분석 필요 여부, 기존 분석 ID)
    """
    existing_analysis = find_existing_repository_analysis(db, repository_url, branch)
    
    if not existing_analysis:
        # 기존 분석이 없으면 새로운 분석 필요
        return True, None
    
    if not latest_commit_hash:
        # Commit hash를 확인할 수 없으면 기존 분석 재사용 (안전한 선택)
        return False, existing_analysis.analysis_id
    
    if not existing_analysis.commit_hash:
        # 기존 분석에 commit hash가 없으면 새로운 분석 필요
        return True, None
    
    if existing_analysis.commit_hash != latest_commit_hash:
        # Commit hash가 다르면 새로운 분석 필요
        logger.info(f"Commit hash changed for {repository_url}:{branch} - "
                  f"existing: {existing_analysis.commit_hash[:8]}, "
                  f"latest: {latest_commit_hash[:8]}")
        return True, None
    
    # Commit hash가 같으면 기존 분석 재사용
    return False, existing_analysis.analysis_id
```

### API 응답 예시

#### 새로운 분석이 필요한 경우 (Commit 변경 감지)
```json
{
  "analysis_id": "new-analysis-uuid",
  "status": "started",
  "message": "분석이 시작되었습니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요.",
  "existing_analyses": null,
  "commit_info": {
    "repository_url": "https://github.com/example/repo.git",
    "previous_commit": "abc123ef",
    "latest_commit": "def456gh",
    "reason": "commit_changed"
  }
}
```

#### 모든 레포지토리의 Commit이 동일한 경우
```json
{
  "analysis_id": "existing-analysis-uuid",
  "status": "existing",
  "message": "모든 레포지토리의 commit이 동일합니다. 기존 분석 결과를 사용합니다: existing-analysis-uuid",
  "commit_info": {
    "repository_url": "https://github.com/example/repo.git",
    "commit_hash": "abc123ef",
    "reason": "same_commit"
  }
}
```

#### 일부 레포지토리만 Commit이 변경된 경우
```json
{
  "analysis_id": "new-analysis-uuid",
  "status": "started",
  "message": "분석이 시작되었습니다. 일부 레포지토리는 기존 분석 결과를 재사용합니다. /results/{analysis_id} 엔드포인트로 결과를 확인하세요.",
  "existing_analyses": ["existing-analysis-1", "existing-analysis-2"],
  "commit_changes": [
    {
      "repository_url": "https://github.com/example/repo1.git",
      "status": "changed",
      "previous_commit": "abc123",
      "latest_commit": "def456"
    },
    {
      "repository_url": "https://github.com/example/repo2.git", 
      "status": "unchanged",
      "commit_hash": "xyz789"
    }
  ]
}
```

## 🔍 분석별 RAG 검색

### 기능 설명

특정 분석 결과(analysis_id)를 기준으로 RAG 검색을 수행하여 더 정확하고 관련성 높은 결과를 제공합니다.

### 사용 방법

#### 1. 일반 검색 (모든 분석 결과에서 검색)
```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 함수 정의",
    "k": 5,
    "filter_metadata": {
      "language": "python"
    }
  }'
```

#### 2. 분석별 검색 (특정 분석 결과에서만 검색)
```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 함수 정의",
    "k": 5,
    "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c"
  }'
```

#### 3. 복합 필터링 (분석별 + 메타데이터 필터)
```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 함수 정의",
    "k": 5,
    "analysis_id": "3cbf3db0-fd9e-410c-bdaa-30cdeb9d7d6c",
    "filter_metadata": {
      "document_type": "ast_analysis",
      "language": "python"
    }
  }'
```

### 메타데이터 구조

임베딩된 문서들은 다음과 같은 메타데이터를 포함합니다:

```json
{
  "analysis_id": "분석 ID",
  "repository_url": "레포지토리 URL",
  "repository_name": "레포지토리 이름",
  "document_type": "문서 타입 (repository_summary, tech_spec, ast_analysis, code_metrics, correlation_analysis)",
  "language": "프로그래밍 언어",
  "file_path": "파일 경로",
  "created_at": "생성 시간"
}
```

## 🎯 Commit 기반 분석 시나리오

### 시나리오 1: 동일 레포지토리, 동일 Commit
```bash
# 첫 번째 분석 요청
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/example/my-project.git",
        "branch": "main"
      }
    ]
  }'

# 응답: 새로운 분석 시작
# {
#   "analysis_id": "analysis-001",
#   "status": "started",
#   "message": "분석이 시작되었습니다."
# }

# 동일한 레포지토리로 두 번째 분석 요청 (commit 변경 없음)
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/example/my-project.git",
        "branch": "main"
      }
    ]
  }'

# 응답: 기존 분석 결과 재사용
# {
#   "analysis_id": "analysis-001",
#   "status": "existing",
#   "message": "모든 레포지토리의 commit이 동일합니다. 기존 분석 결과를 사용합니다: analysis-001",
#   "commit_info": {
#     "repository_url": "https://github.com/example/my-project.git",
#     "commit_hash": "abc123ef456789",
#     "reason": "same_commit"
#   }
# }
```

### 시나리오 2: 동일 레포지토리, Commit 변경
```bash
# 개발자가 새로운 commit을 push한 후 분석 요청
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/example/my-project.git",
        "branch": "main"
      }
    ]
  }'

# 응답: Commit 변경 감지로 새로운 분석 시작
# {
#   "analysis_id": "analysis-002",
#   "status": "started",
#   "message": "레포지토리 commit이 변경되어 새로운 분석을 시작합니다.",
#   "commit_info": {
#     "repository_url": "https://github.com/example/my-project.git",
#     "previous_commit": "abc123ef456789",
#     "latest_commit": "def456gh789abc",
#     "reason": "commit_changed"
#   }
# }
```

### 시나리오 3: 여러 레포지토리, 일부만 Commit 변경
```bash
# 여러 레포지토리 분석 요청
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/example/frontend.git",
        "branch": "main"
      },
      {
        "url": "https://github.com/example/backend.git", 
        "branch": "develop"
      },
      {
        "url": "https://github.com/example/shared-lib.git",
        "branch": "main"
      }
    ]
  }'

# 응답: 일부 레포지토리만 새로 분석
# {
#   "analysis_id": "analysis-003",
#   "status": "started",
#   "message": "분석이 시작되었습니다. 일부 레포지토리는 기존 분석 결과를 재사용합니다.",
#   "existing_analyses": ["analysis-001", "analysis-002"],
#   "commit_changes": [
#     {
#       "repository_url": "https://github.com/example/frontend.git",
#       "status": "changed",
#       "previous_commit": "111aaa",
#       "latest_commit": "222bbb"
#     },
#     {
#       "repository_url": "https://github.com/example/backend.git",
#       "status": "unchanged", 
#       "commit_hash": "333ccc"
#     },
#     {
#       "repository_url": "https://github.com/example/shared-lib.git",
#       "status": "changed",
#       "previous_commit": "444ddd",
#       "latest_commit": "555eee"
#     }
#   ]
# }
```

## 🎯 RAG 검색 활용 시나리오

### 시나리오 1: 프로젝트별 코드 검색
```bash
# 특정 프로젝트의 Python 함수만 검색
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "데이터베이스 연결 함수",
    "k": 10,
    "analysis_id": "project-a-analysis-id",
    "filter_metadata": {
      "language": "python",
      "document_type": "ast_analysis"
    }
  }'
```

### 시나리오 2: 기술스펙 비교
```bash
# 특정 분석의 기술스펙만 검색
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "FastAPI 의존성",
    "k": 5,
    "analysis_id": "web-project-analysis-id",
    "filter_metadata": {
      "document_type": "tech_spec"
    }
  }'
```

### 시나리오 3: 아키텍처 패턴 분석
```bash
# 특정 분석의 연관도 분석 결과 검색
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "마이크로서비스 아키텍처",
    "k": 3,
    "analysis_id": "multi-repo-analysis-id",
    "filter_metadata": {
      "document_type": "correlation_analysis"
    }
  }'
```

## 🔧 구현 세부사항

### 데이터베이스 스키마

```sql
-- 레포지토리 분석 테이블 (Commit 정보 포함)
CREATE TABLE repository_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    analysis_id VARCHAR(255) NOT NULL,
    repository_url VARCHAR(500) NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    commit_hash VARCHAR(40), -- Git commit SHA-1 hash
    commit_date DATETIME,    -- Commit 생성 시간
    commit_author VARCHAR(255), -- Commit 작성자
    commit_message TEXT,     -- Commit 메시지
    status ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_repo_url_branch (repository_url, branch),
    INDEX idx_commit_hash (commit_hash),
    INDEX idx_analysis_id (analysis_id),
    UNIQUE KEY unique_repo_commit (repository_url, branch, commit_hash)
);
```

### 서비스 메서드

```python
class RagRepositoryAnalysisService:
    @staticmethod
    def find_existing_repository_analysis(db: Session, repository_url: str, branch: str = "main"):
        """기존 레포지토리 분석 결과를 찾습니다 (commit hash 포함)."""
        return db.query(RepositoryAnalysis).filter(
            RepositoryAnalysis.repository_url == repository_url,
            RepositoryAnalysis.branch == branch,
            RepositoryAnalysis.status == RepositoryStatus.COMPLETED
        ).order_by(RepositoryAnalysis.updated_at.desc()).first()
    
    @staticmethod
    def check_if_analysis_needed(
        db: Session,
        repository_url: str,
        branch: str = "main",
        latest_commit_hash: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Commit hash를 기준으로 분석이 필요한지 확인합니다.
        
        Args:
            db: 데이터베이스 세션
            repository_url: 레포지토리 URL
            branch: 브랜치명
            latest_commit_hash: 최신 commit hash
            
        Returns:
            tuple[bool, Optional[str]]: (분석 필요 여부, 기존 분석 ID)
        """
        existing_analysis = RagRepositoryAnalysisService.find_existing_repository_analysis(
            db, repository_url, branch
        )
        
        if not existing_analysis:
            return True, None
        
        if not latest_commit_hash:
            return False, existing_analysis.analysis_id
        
        if not existing_analysis.commit_hash:
            return True, None
        
        if existing_analysis.commit_hash != latest_commit_hash:
            logger.info(f"Commit hash changed for {repository_url}:{branch} - "
                      f"existing: {existing_analysis.commit_hash[:8]}, "
                      f"latest: {latest_commit_hash[:8]}")
            return True, None
        
        return False, existing_analysis.analysis_id
    
    @staticmethod
    def create_repository_analysis_with_commit(
        db: Session,
        analysis_id: str,
        repository_url: str,
        repository_name: str,
        branch: str,
        commit_info: Dict[str, Any],
        clone_path: str
    ) -> RepositoryAnalysis:
        """Commit 정보를 포함하여 레포지토리 분석 레코드를 생성합니다."""
        repo_analysis = RepositoryAnalysis(
            analysis_id=analysis_id,
            repository_url=repository_url,
            repository_name=repository_name,
            branch=branch,
            commit_hash=commit_info.get('commit_hash'),
            commit_date=datetime.fromisoformat(commit_info.get('commit_date', '').replace('Z', '+00:00')) if commit_info.get('commit_date') else None,
            commit_author=commit_info.get('author'),
            commit_message=commit_info.get('message'),
            clone_path=clone_path,
            status=RepositoryStatus.COMPLETED
        )
        
        db.add(repo_analysis)
        db.commit()
        db.refresh(repo_analysis)
        
        return repo_analysis
```

## 📊 성능 최적화

### 인덱스 활용
- `repository_url`과 `branch` 복합 인덱스로 빠른 레포지토리 검색
- `commit_hash` 인덱스로 효율적인 commit 기반 중복 검색
- `analysis_id` 인덱스로 효율적인 분석별 검색
- `unique_repo_commit` 제약조건으로 동일 commit 중복 방지

### 캐싱 전략
- 메모리 캐시와 데이터베이스 조합으로 성능 향상
- 자주 검색되는 분석 결과는 메모리에 캐시
- Commit hash 기반 캐시 무효화로 정확성 보장

### 벡터 검색 최적화
- ChromaDB의 메타데이터 필터링 활용
- 분석별 검색으로 검색 범위 제한하여 정확도 향상
- Commit 정보를 메타데이터에 포함하여 시점별 검색 지원

### Git 작업 최적화
- Shallow clone (depth=1)으로 빠른 commit 정보 조회
- 임시 디렉토리 자동 정리로 디스크 공간 절약
- 병렬 commit 정보 조회로 다중 레포지토리 처리 속도 향상

## 🚀 향후 개선 계획

1. **Commit 히스토리 분석**: 특정 기간 동안의 commit 변경사항 추적
2. **증분 분석**: 이전 commit과 비교하여 변경된 파일만 재분석
3. **브랜치별 분석 관리**: 동일 레포지토리의 다른 브랜치 분석 결과 관리
4. **Commit 메시지 기반 분류**: Commit 메시지를 분석하여 변경 유형 자동 분류
5. **실시간 Webhook 연동**: GitHub/GitLab webhook으로 자동 분석 트리거
6. **분석 결과 diff**: 이전 commit과의 분석 결과 차이점 시각화

## 📝 참고사항

- **Commit 기반 중복 체크**: 레포지토리 URL, 브랜치, commit hash를 모두 고려
- **분석 상태 확인**: `COMPLETED` 상태인 결과만 재사용
- **Commit 정보 저장**: commit hash, 날짜, 작성자, 메시지 모두 저장
- **에러 처리**: Commit 정보 조회 실패 시 안전하게 새로운 분석 수행
- **메타데이터 활용**: `analysis_id`와 commit 정보를 메타데이터 필터로 활용 가능
- **검색 성능**: 적절한 `k` 값과 메타데이터 필터 조합으로 성능 최적화