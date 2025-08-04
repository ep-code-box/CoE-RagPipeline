#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('.')

from services.llm_service import LLMDocumentService, DocumentType
from models.schemas import ASTNode

async def test_all_document_types():
    """Test all document types to ensure they work with ASTNode objects"""
    
    # Create test data with ASTNode objects
    test_node = ASTNode(
        type='function',
        name='test_function',
        line_start=1,
        line_end=10,
        metadata={'complexity': 5}
    )
    
    analysis_data = {
        'analysis_id': 'test-123',
        'repositories': [{'url': 'https://github.com/test/repo.git', 'branch': 'main'}],
        'ast_analysis': {'test.py': [test_node]},
        'tech_specs': [{'name': 'Python', 'version': '3.9', 'framework': 'FastAPI'}],
        'code_metrics': {'lines_of_code': 100, 'cyclomatic_complexity': 2.5}
    }
    
    # Test all document types
    document_types = [
        DocumentType.DEVELOPMENT_GUIDE,
        DocumentType.API_DOCUMENTATION,
        DocumentType.ARCHITECTURE_OVERVIEW,
        DocumentType.CODE_REVIEW_SUMMARY,
        DocumentType.TECHNICAL_SPECIFICATION,
        DocumentType.DEPLOYMENT_GUIDE,
        DocumentType.TROUBLESHOOTING_GUIDE
    ]
    
    llm_service = LLMDocumentService()
    results = []
    
    for doc_type in document_types:
        try:
            print(f"Testing {doc_type}...")
            result = await llm_service.generate_document(
                analysis_data=analysis_data,
                document_type=doc_type,
                language='korean'
            )
            print(f"✅ SUCCESS: {doc_type} - Content length: {len(result['content'])} characters")
            results.append((doc_type, True, None))
        except Exception as e:
            print(f"❌ ERROR: {doc_type} - {str(e)}")
            results.append((doc_type, False, str(e)))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    
    success_count = 0
    for doc_type, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {doc_type}")
        if not success:
            print(f"    Error: {error}")
        else:
            success_count += 1
    
    print(f"\nResults: {success_count}/{len(document_types)} document types passed")
    return success_count == len(document_types)

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_all_document_types())
    print(f'\nOverall test result: {"PASSED" if success else "FAILED"}')
    sys.exit(0 if success else 1)