#!/usr/bin/env python3

import json
from core.database import SessionLocal, RagAnalysisResult

try:
    with SessionLocal() as db:
        # 특정 분석 ID의 상세 데이터 확인
        analysis_id = "075a8fc7-a562-4d3f-9ab1-e7c3f3de36ea"
        result = db.query(RagAnalysisResult).filter(
            RagAnalysisResult.analysis_id == analysis_id
        ).first()
        
        if result:
            print(f'Analysis ID: {result.analysis_id}')
            print(f'Status: {result.status}')
            print(f'Git URL: {result.git_url}')
            print(f'Repository count: {result.repository_count}')
            
            if result.repositories_data:
                try:
                    repos_data = json.loads(result.repositories_data)
                    print(f'Repositories data type: {type(repos_data)}')
                    print(f'Number of repositories: {len(repos_data)}')
                    
                    for i, repo in enumerate(repos_data):
                        print(f'\nRepository {i+1}:')
                        print(f'  Type: {type(repo)}')
                        if isinstance(repo, dict):
                            print(f'  Keys: {list(repo.keys())}')
                            if 'repository' in repo:
                                print(f'  Repository info: {repo["repository"]}')
                            if 'files' in repo:
                                print(f'  Files count: {len(repo["files"])}')
                            if 'tech_specs' in repo:
                                print(f'  Tech specs count: {len(repo["tech_specs"])}')
                            if 'code_metrics' in repo:
                                print(f'  Code metrics: {repo["code_metrics"]}')
                        else:
                            print(f'  Data: {repo}')
                            
                except json.JSONDecodeError as e:
                    print(f'Failed to parse repositories_data: {e}')
                    print(f'Raw data: {result.repositories_data[:500]}...')
            else:
                print('No repositories_data found')
                
        else:
            print(f'No analysis found for ID: {analysis_id}')
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()