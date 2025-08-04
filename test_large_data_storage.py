#!/usr/bin/env python3
"""
Test storing large JSON data in the database to verify the fix
"""

import json
from datetime import datetime
from config.database import SessionLocal, RagAnalysisResult
from models.schemas import AnalysisStatus

def test_large_data_storage():
    """Test storing large JSON data similar to the original error"""
    print("🧪 Testing large JSON data storage...")
    
    # Create a large JSON string similar to the original error (3+ MB)
    large_repositories_data = []
    
    # Create a large repository data structure
    for i in range(100):  # Create 100 repository entries
        repo_data = {
            "repository": {
                "url": f"https://github.com/test-repo-{i}/workApi",
                "branch": "main",
                "name": f"test-repo-{i}"
            },
            "clone_path": f"cache/repositories/test-repo-{i}_17543",
            "files": []
        }
        
        # Add many files to make it large
        for j in range(50):  # 50 files per repo
            file_data = {
                "path": f"src/main/java/com/example/file{j}.java",
                "name": f"file{j}.java",
                "size": 1024 + j,
                "language": "java",
                "content": f"// This is a test file {j}\n" + "// " + "x" * 1000,  # Large content
                "ast_analysis": {
                    "functions": [f"function{k}" for k in range(10)],
                    "classes": [f"class{k}" for k in range(5)],
                    "imports": [f"import{k}" for k in range(20)]
                }
            }
            repo_data["files"].append(file_data)
        
        large_repositories_data.append(repo_data)
    
    # Convert to JSON string
    repositories_json = json.dumps(large_repositories_data, ensure_ascii=False)
    
    print(f"📏 Generated JSON data size: {len(repositories_json):,} characters")
    print(f"📏 Size in MB: {len(repositories_json) / (1024*1024):.2f} MB")
    
    if len(repositories_json) < 1000000:  # Less than 1MB
        print("⚠️ Generated data is smaller than expected, adding more content...")
        # Add more content to make it larger
        for repo in large_repositories_data:
            for file_data in repo["files"]:
                file_data["large_content"] = "x" * 50000  # Add 50KB per file
        
        repositories_json = json.dumps(large_repositories_data, ensure_ascii=False)
        print(f"📏 Updated JSON data size: {len(repositories_json):,} characters")
        print(f"📏 Updated size in MB: {len(repositories_json) / (1024*1024):.2f} MB")
    
    try:
        db = SessionLocal()
        
        # Create a test record with large data
        test_record = RagAnalysisResult(
            analysis_id="test-large-data-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
            git_url="https://github.com/test/large-data-test",
            analysis_date=datetime.utcnow(),
            status=AnalysisStatus.COMPLETED,
            repository_count=len(large_repositories_data),
            total_files=sum(len(repo["files"]) for repo in large_repositories_data),
            total_lines_of_code=50000,
            repositories_data=repositories_json,  # This is the large data
            correlation_data='{"test": "correlation data"}',
            tech_specs_summary='{"test": "tech specs summary"}',
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        print("💾 Attempting to save large data to database...")
        db.add(test_record)
        db.commit()
        
        print("✅ Large data saved successfully!")
        print(f"📝 Record ID: {test_record.analysis_id}")
        
        # Verify by reading it back
        print("🔍 Verifying data by reading it back...")
        retrieved = db.query(RagAnalysisResult).filter(
            RagAnalysisResult.analysis_id == test_record.analysis_id
        ).first()
        
        if retrieved and retrieved.repositories_data:
            retrieved_size = len(retrieved.repositories_data)
            print(f"📏 Retrieved data size: {retrieved_size:,} characters")
            print(f"📏 Retrieved size in MB: {retrieved_size / (1024*1024):.2f} MB")
            
            # Parse JSON to verify integrity
            parsed_data = json.loads(retrieved.repositories_data)
            print(f"📊 Parsed data contains {len(parsed_data)} repositories")
            print("✅ Data integrity verified!")
            
            # Clean up test data
            db.delete(retrieved)
            db.commit()
            print("🧹 Test data cleaned up")
            
            return True
        else:
            print("❌ Failed to retrieve saved data")
            return False
            
    except Exception as e:
        print(f"❌ Error during large data storage test: {e}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Large JSON Data Storage Test")
    print("📝 Testing the fix for DataError 1406 'Data too long for column'")
    print("=" * 60)
    
    success = test_large_data_storage()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Large data storage test PASSED!")
        print("🎉 The database can now handle large JSON data")
        print("💡 The original error should be resolved")
    else:
        print("❌ Large data storage test FAILED!")
        print("🔧 The issue may not be fully resolved")
    print("=" * 60)
    
    exit(0 if success else 1)