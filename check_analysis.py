#!/usr/bin/env python3
import requests
import json

def check_analysis_result(analysis_id):
    try:
        response = requests.get(f'http://localhost:8004/api/v1/results/{analysis_id}')
        if response.status_code == 200:
            data = response.json()
            print('Analysis ID:', data['analysis_id'])
            print('Status:', data['status'])
            print('Repository Count:', len(data['repositories']))
            if data['repositories']:
                repo = data['repositories'][0]
                print('Repository URL:', repo['url'])
                print('Files analyzed:', len(repo.get('files', [])))
                print('AST analysis available:', 'ast_analysis' in repo)
                print('Tech spec available:', 'tech_spec' in repo)
                
                # AST 분석 결과 확인
                if 'ast_analysis' in repo:
                    ast = repo['ast_analysis']
                    print('AST functions found:', len(ast.get('functions', [])))
                    print('AST classes found:', len(ast.get('classes', [])))
                
                # 기술 스펙 확인
                if 'tech_spec' in repo:
                    tech = repo['tech_spec']
                    print('Languages detected:', tech.get('languages', []))
                    print('Dependencies found:', len(tech.get('dependencies', [])))
            else:
                print('No repositories found in analysis result')
        else:
            print('Error:', response.status_code, response.text)
    except Exception as e:
        print('Error:', e)

if __name__ == "__main__":
    analysis_id = "41e77381-3b6a-4b67-8704-4a4408e33d10"
    check_analysis_result(analysis_id)