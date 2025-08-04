#!/usr/bin/env python3
import requests
import json

def test_analyze_api():
    data = {
        'repositories': [
            {
                'url': 'https://github.com/octocat/Hello-World.git',
                'branch': 'master'
            }
        ],
        'include_ast': True,
        'include_tech_spec': True,
        'include_correlation': False
    }

    try:
        response = requests.post('http://localhost:8004/api/v1/analyze', json=data)
        print('Status:', response.status_code)
        print('Response:', response.text)
        print('Headers:', dict(response.headers))
    except Exception as e:
        print('Error:', e)

if __name__ == "__main__":
    test_analyze_api()