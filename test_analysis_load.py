#!/usr/bin/env python3

import sys
sys.path.append('.')
from services.analysis_service import AnalysisService

# 테스트: 기존 분석 결과 로드
analysis_service = AnalysisService()
analysis_id = '075a8fc7-a562-4d3f-9ab1-e7c3f3de36ea'

result = analysis_service.load_analysis_result(analysis_id)
if result:
    print(f'Analysis loaded successfully: {analysis_id}')
    print(f'Status: {result.status}')
    print(f'Number of repositories: {len(result.repositories)}')
    
    if result.repositories:
        for i, repo in enumerate(result.repositories):
            print(f'Repository {i+1}: {type(repo)}')
            if isinstance(repo, dict):
                print(f'  Keys: {list(repo.keys())}')
            else:
                print(f'  Object type: {type(repo)}')
                if hasattr(repo, 'repository'):
                    print(f'  Repository URL: {repo.repository.url}')
                if hasattr(repo, 'files'):
                    print(f'  Files count: {len(repo.files)}')
    else:
        print('No repositories found in analysis result')
else:
    print(f'Failed to load analysis result for {analysis_id}')