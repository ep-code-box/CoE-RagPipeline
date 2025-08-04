#!/usr/bin/env python3

from core.database import SessionLocal, RagAnalysisResult
from sqlalchemy import text

try:
    with SessionLocal() as db:
        # 테이블 존재 확인
        result = db.execute(text('SHOW TABLES LIKE "rag_analysis_results"'))
        tables = result.fetchall()
        print(f'Tables found: {tables}')
        
        if tables:
            # 데이터 확인
            results = db.query(RagAnalysisResult).all()
            print(f'Total analysis results in database: {len(results)}')
            
            for result in results:
                print(f'Analysis ID: {result.analysis_id}')
                print(f'Status: {result.status}')
                print(f'Git URL: {result.git_url}')
                print(f'Repository count: {result.repository_count}')
                print(f'Has repositories_data: {bool(result.repositories_data)}')
                if result.repositories_data:
                    print(f'Repositories data length: {len(result.repositories_data)}')
                print('---')
        else:
            print('rag_analysis_results table does not exist')
            
except Exception as e:
    print(f'Error: {e}')