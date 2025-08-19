import logging
import os
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from services.embedding_service import EmbeddingService
from models.schemas import EmbedContentRequest

logger = logging.getLogger(__name__)

class ContentEmbeddingService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    async def embed_content(self, request: EmbedContentRequest) -> Dict[str, Any]:
        content = ""
        source_identifier = ""
        metadata = request.metadata if request.metadata else {}

        if request.source_type == "file":
            file_path = request.source_data
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            source_identifier = file_path
            metadata["source_type"] = "file"
            metadata["file_path"] = file_path
            if request.title:
                metadata["title"] = request.title
            else:
                metadata["title"] = os.path.basename(file_path)

        elif request.source_type == "url":
            url = request.source_data
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                content = response.text
                source_identifier = url
                metadata["source_type"] = "url"
                metadata["url"] = url
                if request.title:
                    metadata["title"] = request.title
                else:
                    metadata["title"] = urlparse(url).netloc # Use domain as title if not provided
            except requests.exceptions.RequestException as e:
                raise ConnectionError(f"Failed to fetch URL {url}: {e}")

        elif request.source_type == "text":
            content = request.source_data
            source_identifier = "user_provided_text"
            metadata["source_type"] = "text"
            if request.title:
                metadata["title"] = request.title
            else:
                metadata["title"] = "User Provided Text"

        else:
            raise ValueError(f"Unsupported source_type: {request.source_type}")

        if not content:
            raise ValueError("Content to embed cannot be empty.")

        # Add group_name to metadata
        if request.group_name:
            metadata["group_name"] = request.group_name

        # Split content into chunks
        chunks = self.text_splitter.split_text(content)
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy()
            doc_metadata["chunk_index"] = i
            doc_metadata["total_chunks"] = len(chunks)
            doc_metadata["source_identifier"] = source_identifier # Unique identifier for the original source
            documents.append(Document(page_content=chunk, metadata=doc_metadata))

        if not documents:
            return {"status": "failed", "message": "No documents generated from content."}

        # Add documents to ChromaDB
        try:
            doc_ids = self.embedding_service.vectorstore.add_documents(documents)
            logger.info(f"Successfully embedded {len(documents)} documents from {source_identifier}")
            return {
                "status": "success",
                "count": len(documents),
                "document_ids": doc_ids,
                "source_identifier": source_identifier,
                "group_name": request.group_name
            }
        except Exception as e:
            logger.error(f"Failed to add documents to vectorstore for {source_identifier}: {e}")
            raise
