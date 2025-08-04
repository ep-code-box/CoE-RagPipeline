# 🔍 AST 분석 기능 가이드

CoE-RagPipeline의 AST(Abstract Syntax Tree) 분석 기능에 대한 상세 가이드입니다.

## ✨ 개요

AST 분석 기능은 소스코드의 구조를 분석하여 함수, 클래스, 변수, 임포트 등의 정보를 추출합니다. 이 정보는 코드 품질 분석, 의존성 분석, 문서 생성 등에 활용됩니다.

## 🚀 주요 기능

### 1. 이중 분석 시스템
- **Enhanced Analyzer (우선)**: Tree-sitter 기반 고정밀 AST 분석
- **Basic Analyzer (Fallback)**: 패턴 매칭 기반 기본 AST 분석

### 2. 지원 언어
- **Python**: 완전 지원 (내장 ast 모듈 + Tree-sitter)
- **JavaScript**: 향상된 패턴 매칭 + Tree-sitter
- **TypeScript**: JavaScript와 동일한 방식으로 처리
- **Java**: 기본 패턴 매칭 + Tree-sitter

### 3. 분석 정보
- 함수/메서드 선언
- 클래스 선언
- 변수 선언
- Import/Export 문
- 코드 메트릭 (복잡도, 라인 수 등)

## 🔧 사용 방법

### API를 통한 분석

```bash
# 기본 분석 (AST 포함)
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }
    ],
    "include_ast": true,
    "include_tech_spec": true,
    "include_correlation": false
  }'
```

### Enhanced 분석 API

```bash
# Tree-sitter 기반 고급 분석
curl -X POST "http://localhost:8001/api/v1/enhanced/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/your-repo/project.git",
        "branch": "main"
      }
    ],
    "include_tree_sitter": true,
    "include_static_analysis": true,
    "include_dependency_analysis": true
  }'
```

## 📊 분석 결과 구조

### 기본 AST 노드 정보
```json
{
  "type": "FunctionDeclaration",
  "name": "hello_world",
  "line_start": 5,
  "line_end": 8,
  "metadata": {
    "language": "Python",
    "args": ["name", "age"],
    "returns": "str",
    "is_async": false
  },
  "children": []
}
```

### Enhanced 분석 결과
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "capabilities_used": {
    "tree_sitter": true,
    "static_analysis": true,
    "dependency_analysis": false
  },
  "tree_sitter_results": {
    "file.py": [/* AST nodes */]
  },
  "summary": {
    "tree_sitter": {
      "total_files": 10,
      "total_nodes": 150,
      "languages": {"Python": 8, "JavaScript": 2},
      "node_types": {"function": 25, "class": 8, "import": 12}
    }
  }
}
```

## 🛠️ 내부 구조

### 1. 분석 파이프라인
```
분석 요청 → Enhanced Analyzer 시도 → Tree-sitter 분석 → 성공?
                                                        ↓ 실패
                                    Basic Analyzer → 패턴 매칭 분석
```

### 2. 주요 컴포넌트

#### Enhanced Analyzer (`analyzers/enhanced/`)
- `TreeSitterAnalyzer`: Tree-sitter 기반 정확한 AST 분석
- `StaticAnalyzer`: 정적 분석 도구 통합
- `DependencyAnalyzer`: 의존성 분석
- `EnhancedAnalyzer`: 통합 분석기

#### Basic Analyzer (`analyzers/ast_analyzer.py`)
- Python: 내장 `ast` 모듈 사용
- JavaScript/TypeScript: 향상된 정규식 패턴 매칭
- Java: 기본 패턴 매칭

### 3. 통합 지점
- `services/analysis_service.py`의 `_perform_ast_analysis` 메서드
- Enhanced → Basic fallback 로직 구현

## 🔍 분석 예시

### Python 코드 분석
```python
# 입력 코드
def calculate_sum(a: int, b: int) -> int:
    """두 수의 합을 계산합니다."""
    return a + b

class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, x, y):
        result = x + y
        self.history.append(result)
        return result
```

```json
// 분석 결과
{
  "test.py": [
    {
      "type": "FunctionDef",
      "name": "calculate_sum",
      "line_start": 1,
      "line_end": 3,
      "metadata": {
        "args": ["a", "b"],
        "returns": "int",
        "is_async": false
      }
    },
    {
      "type": "ClassDef", 
      "name": "Calculator",
      "line_start": 5,
      "line_end": 12,
      "metadata": {
        "bases": [],
        "methods": ["__init__", "add"]
      }
    }
  ]
}
```

### JavaScript 코드 분석
```javascript
// 입력 코드
function greet(name) {
    return `Hello, ${name}!`;
}

const multiply = (a, b) => a * b;

class Person {
    constructor(name) {
        this.name = name;
    }
    
    getName() {
        return this.name;
    }
}

export { greet, Person };
```

```json
// 분석 결과
{
  "test.js": [
    {
      "type": "FunctionDeclaration",
      "name": "greet",
      "line_start": 1,
      "metadata": {
        "language": "JavaScript",
        "is_arrow_function": false
      }
    },
    {
      "type": "FunctionDeclaration", 
      "name": "multiply",
      "line_start": 5,
      "metadata": {
        "language": "JavaScript",
        "is_arrow_function": true,
        "is_const": true
      }
    },
    {
      "type": "ClassDeclaration",
      "name": "Person", 
      "line_start": 7,
      "metadata": {
        "language": "JavaScript",
        "has_extends": false
      }
    },
    {
      "type": "ExportDeclaration",
      "name": "export { greet, Person };",
      "line_start": 16,
      "metadata": {
        "language": "JavaScript"
      }
    }
  ]
}
```

## 📈 코드 메트릭

분석 결과에는 다음과 같은 코드 메트릭이 포함됩니다:

```json
{
  "code_metrics": {
    "cyclomatic_complexity": 2.5,
    "ast_metrics": {
      "total_functions": 15,
      "total_classes": 3,
      "total_imports": 8,
      "files_analyzed": 12,
      "analysis_method": "enhanced"
    }
  }
}
```

## 🚨 문제 해결

### 1. Tree-sitter 사용 불가
```
⚠️ Tree-sitter not available, falling back to basic AST analyzer
```
**해결책**: Tree-sitter 라이브러리가 설치되지 않았거나 초기화에 실패했습니다. 기본 분석기로 자동 fallback됩니다.

### 2. 분석 결과 없음
```
⚠️ Enhanced AST analysis returned no results
```
**해결책**: 지원되지 않는 파일 형식이거나 파일이 비어있을 수 있습니다. 로그를 확인하세요.

### 3. 부분적 분석 실패
```
❌ Basic AST analysis also failed for repository
```
**해결책**: 파일 인코딩 문제나 구문 오류가 있을 수 있습니다. 개별 파일 로그를 확인하세요.

## 🔧 개발자 가이드

### 새로운 언어 지원 추가

1. **Tree-sitter 언어 추가**:
```python
# analyzers/enhanced/tree_sitter_analyzer.py
import tree_sitter_newlang

language_capsules = {
    # 기존 언어들...
    'NewLang': tree_sitter_newlang.language(),
}
```

2. **Basic Analyzer 패턴 추가**:
```python
# analyzers/ast_analyzer.py
def _analyze_newlang_ast(self, file_path: str) -> List[ASTNode]:
    # 새로운 언어의 패턴 매칭 로직 구현
    pass
```

### 커스텀 메트릭 추가

```python
# services/analysis_service.py의 _perform_ast_analysis에서
repo.code_metrics.custom_metric = calculate_custom_metric(ast_results)
```

## 📝 로그 및 디버깅

### 로그 레벨 설정
```bash
# 상세 로그 확인
export LOG_LEVEL=DEBUG
python main.py
```

### 주요 로그 메시지
- `Enhanced AST analysis successful`: Tree-sitter 분석 성공
- `Using basic AST analyzer as fallback`: 기본 분석기 사용
- `AST analysis completed`: 전체 분석 완료

## 🎯 성능 최적화

### 1. 파일 필터링
큰 레포지토리의 경우 불필요한 파일을 제외하여 성능을 향상시킬 수 있습니다.

### 2. 병렬 처리
Enhanced Analyzer는 파일별 병렬 처리를 지원합니다.

### 3. 캐싱
분석 결과는 자동으로 캐싱되어 동일한 파일의 재분석을 방지합니다.

## 📚 참고 자료

- [Tree-sitter 공식 문서](https://tree-sitter.github.io/tree-sitter/)
- [Python AST 모듈](https://docs.python.org/3/library/ast.html)
- [CoE-RagPipeline Enhanced Analysis Guide](./ENHANCED_ANALYSIS_GUIDE.md)

---

**업데이트**: 2024-01-01 - AST 분석 기능 개선 및 이중 분석 시스템 도입