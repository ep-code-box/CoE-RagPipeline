import os
import logging
import mysql.connector
from typing import List, Dict, Any, Optional

try:
    from langchain_core.documents import Document
except ImportError:  # Fallback for older langchain releases
    from langchain.schema import Document
from services.embedding_service import get_embedding_service
from config.settings import settings

logger = logging.getLogger(__name__)

class RDBEmbeddingService:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.db_config = {
            "host": os.getenv("DB_HOST", "mariadb"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "coe_user"),
            "password": os.getenv("DB_PASSWORD", "coe_password"),
            "database": os.getenv("DB_NAME", "coe_db")
        }

    def _get_db_connection(self):
        return mysql.connector.connect(**self.db_config)

    def extract_and_embed_schema(self) -> Dict[str, Any]:
        """
        MariaDB 스키마 정보를 추출하고 임베딩하여 ChromaDB에 저장합니다.
        """
        documents = []
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # 1. 테이블 정보 추출
            cursor.execute("SHOW TABLES")
            tables = [row['Tables_in_coe_db'] for row in cursor.fetchall()]

            for table_name in tables:
                # 테이블 설명 문서
                table_description = f"데이터베이스 테이블: {table_name}. 이 테이블은 {table_name}에 대한 정보를 저장합니다."
                documents.append(Document(
                    page_content=table_description,
                    metadata={
                        "source_type": "rdb_schema",
                        "schema_type": "table_description",
                        "table_name": table_name,
                        "group_name": "default" # 기본 group_name 설정
                    }
                ))

                # 컬럼 정보 추출
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                columns = cursor.fetchall()
                column_descriptions = []
                for col in columns:
                    col_desc = f"컬럼: {col['Field']}, 타입: {col['Type']}, Nullable: {col['Null']}, Key: {col['Key']}"
                    column_descriptions.append(col_desc)
                
                columns_content = f"테이블 {table_name}의 컬럼 정보:\n" + "\n".join(column_descriptions)
                documents.append(Document(
                    page_content=columns_content,
                    metadata={
                        "source_type": "rdb_schema",
                        "schema_type": "column_details",
                        "table_name": table_name,
                        "group_name": "default" # 기본 group_name 설정
                    }
                ))
            
            # 2. 임베딩 서비스로 문서 추가
            if documents:
                doc_ids = self.embedding_service.vectorstore.add_documents(documents)
                logger.info(f"Successfully embedded {len(documents)} RDB schema documents.")
                return {"status": "success", "embedded_count": len(documents), "document_ids": doc_ids}
            else:
                logger.info("No RDB schema documents to embed.")
                return {"status": "no_documents", "embedded_count": 0}

        except mysql.connector.Error as err:
            logger.error(f"MariaDB 연결 또는 쿼리 오류: {err}")
            return {"status": "error", "message": str(err)}
        except Exception as e:
            logger.error(f"RDB 스키마 임베딩 중 오류 발생: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
