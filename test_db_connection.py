#!/usr/bin/env python3
"""
Test database connection and verify schema changes
"""

from config.database import test_connection, engine
from sqlalchemy import text

def test_schema():
    """Test the database schema changes"""
    print("🔍 Testing database connection and schema...")
    
    # Test connection
    if not test_connection():
        print("❌ Database connection failed")
        return False
    
    try:
        with engine.connect() as connection:
            # Check column types
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'rag_analysis_results'
                AND COLUMN_NAME IN ('repositories_data', 'correlation_data', 'tech_specs_summary')
                ORDER BY COLUMN_NAME
            """))
            
            columns = result.fetchall()
            print("\n📊 Current column information:")
            all_longtext = True
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (max_length: {col[2]})")
                if col[1].upper() != 'LONGTEXT':
                    all_longtext = False
            
            if all_longtext:
                print("\n✅ All columns are LONGTEXT - ready for large JSON data!")
                return True
            else:
                print("\n❌ Some columns are not LONGTEXT")
                return False
                
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_schema()
    exit(0 if success else 1)