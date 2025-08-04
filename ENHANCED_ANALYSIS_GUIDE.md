# Enhanced Analysis Guide

## Overview

The CoE-RagPipeline project now includes comprehensive enhanced analysis capabilities that integrate:

- **AST Analysis**: Tree-sitter based parsing for Python, JavaScript, Java, TypeScript, and TSX
- **Static Analysis**: Security and code quality analysis using bandit, pylint, flake8, mypy, and radon
- **Dependency Analysis**: Package dependency and vulnerability scanning using pipdeptree and pip-audit

## ✅ Current Status

All enhanced analysis libraries are **ACTIVE** and **WORKING**:

### AST Analysis Libraries
- ✅ `ast-decompiler` - AST decompilation utilities
- ✅ `tree-sitter` - Core tree-sitter library
- ✅ `tree-sitter-python` - Python language support
- ✅ `tree-sitter-javascript` - JavaScript language support  
- ✅ `tree-sitter-java` - Java language support
- ✅ `tree-sitter-typescript` - TypeScript/TSX language support

### Static Analysis Tools
- ✅ `bandit` - Security vulnerability scanner
- ✅ `pylint` - Code quality and style checker
- ✅ `flake8` - Style guide enforcement
- ✅ `mypy` - Static type checker
- ✅ `radon` - Code complexity analyzer

### Dependency Analysis Tools
- ✅ `pipdeptree` - Dependency tree visualization
- ✅ `pip-audit` - Security vulnerability scanner

## API Endpoints

The enhanced analysis functionality is exposed through the following REST API endpoints:

### 1. Check Capabilities
```http
GET /api/v1/enhanced/capabilities
```
Returns available analysis tools and their status.

### 2. Start Analysis
```http
POST /api/v1/enhanced/analyze
```
**Request Body:**
```json
{
  "repositories": [
    {
      "url": "https://github.com/user/repo.git",
      "branch": "main"
    }
  ],
  "include_tree_sitter": true,
  "include_static_analysis": true,
  "include_dependency_analysis": true,
  "generate_report": true
}
```

### 3. Check Analysis Status
```http
GET /api/v1/enhanced/status/{analysis_id}
```

### 4. Get Analysis Results
```http
GET /api/v1/enhanced/results/{analysis_id}
```

### 5. Get Analysis Report
```http
GET /api/v1/enhanced/report/{analysis_id}
```

### 6. List All Analyses
```http
GET /api/v1/enhanced/list
```

### 7. Delete Analysis Results
```http
DELETE /api/v1/enhanced/results/{analysis_id}
```

## Programming Interface

### Using the Enhanced Analyzer Directly

```python
from analyzers.enhanced.enhanced_analyzer import EnhancedAnalyzer
from models.schemas import FileInfo

# Initialize analyzer
analyzer = EnhancedAnalyzer()

# Check capabilities
print(f"Capabilities: {analyzer.capabilities}")

# Create file info objects
files = [
    FileInfo(
        path="sample.py",
        name="sample.py",
        extension=".py",
        size=1000,
        language="Python"
    )
]

# Run analysis
results = analyzer.analyze_repository(
    clone_path="/path/to/repository",
    files=files,
    include_tree_sitter=True,
    include_static_analysis=True,
    include_dependency_analysis=True
)

# Generate report
report = analyzer.generate_comprehensive_report(results)
```

### Individual Analyzer Usage

#### Tree-sitter AST Analysis
```python
from analyzers.enhanced.tree_sitter_analyzer import TreeSitterAnalyzer

analyzer = TreeSitterAnalyzer()
ast_results = analyzer.analyze_files("/path/to/repo", files)
```

#### Static Analysis
```python
from analyzers.enhanced.static_analyzer import StaticAnalyzer

analyzer = StaticAnalyzer()
static_results = analyzer.analyze_files("/path/to/repo", files)
```

#### Dependency Analysis
```python
from analyzers.enhanced.dependency_analyzer import DependencyAnalyzer

analyzer = DependencyAnalyzer()
dep_results = analyzer.analyze_project("/path/to/repo", files)
```

## Test Results

### ✅ Component Tests Passed
- **Tree-sitter Analyzer**: Successfully analyzes Python, JavaScript, Java, TypeScript, TSX files
- **Static Analyzer**: All 5 tools (bandit, pylint, flake8, mypy, radon) working correctly
- **Dependency Analyzer**: Both tools (pipdeptree, pip-audit) working correctly
- **Enhanced Analyzer**: Integrated analysis working with all capabilities

### ✅ API Tests Passed
- All 7 enhanced analysis endpoints properly registered
- FastAPI application starts successfully
- Routes accessible under `/api/v1/enhanced/` prefix

### ✅ End-to-End Tests Passed
- Complete analysis pipeline working
- Tree-sitter analysis: 2 files analyzed with AST nodes extracted
- Static analysis: 9 issues found across 5 tools
- Dependency analysis: 39 dependencies scanned, no vulnerabilities
- Report generation: 876-character comprehensive report generated

## Analysis Capabilities

### Tree-sitter AST Analysis
- **Languages**: Python, JavaScript, Java, TypeScript, TSX
- **Output**: Structured AST nodes with metadata
- **Features**: Function/class detection, syntax tree parsing

### Static Analysis
- **Security**: Bandit scans for security vulnerabilities
- **Code Quality**: Pylint checks code quality and style
- **Style**: Flake8 enforces PEP 8 style guidelines
- **Types**: MyPy performs static type checking
- **Complexity**: Radon measures code complexity metrics

### Dependency Analysis
- **Dependencies**: Pipdeptree visualizes dependency trees
- **Security**: Pip-audit scans for known vulnerabilities
- **Output**: Dependency lists with version information and security reports

## Usage Examples

### Example 1: Analyze a Python Project
```bash
curl -X POST "http://localhost:8001/api/v1/enhanced/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [{"url": "https://github.com/user/python-project.git"}],
    "include_tree_sitter": true,
    "include_static_analysis": true,
    "include_dependency_analysis": true
  }'
```

### Example 2: Check Analysis Capabilities
```bash
curl "http://localhost:8001/api/v1/enhanced/capabilities"
```

### Example 3: Get Analysis Results
```bash
curl "http://localhost:8001/api/v1/enhanced/results/{analysis_id}"
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed via `pip install -r requirements.txt`
2. **Tree-sitter Language Issues**: Language bindings are automatically initialized
3. **Static Analysis Tool Missing**: Check tool availability with capabilities endpoint
4. **Permission Issues**: Ensure write permissions for temporary directories

### Verification Commands

```bash
# Test individual components
python3 test_enhanced_analyzers.py

# Test API routes
python3 test_api_routes.py

# Test end-to-end pipeline
python3 test_end_to_end.py
```

## Performance Notes

- **Tree-sitter**: Fast AST parsing, suitable for large codebases
- **Static Analysis**: May be slower on large files, runs in parallel where possible
- **Dependency Analysis**: Quick for most projects, may be slower for projects with many dependencies
- **Background Processing**: All analysis runs asynchronously via FastAPI background tasks

## Future Enhancements

Potential areas for expansion:
- Additional language support for tree-sitter
- More static analysis tools integration
- Custom rule configuration for static analyzers
- Performance optimizations for large repositories
- Caching mechanisms for repeated analyses