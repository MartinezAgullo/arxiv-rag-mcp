"""Configuration management"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class Config:
    """Application configuration"""
    
    # API Keys
    openai_api_key: str
    pinecone_api_key: str
    notion_token: str
    
    # Pinecone Settings
    pinecone_index_name: str
    pinecone_environment: str
    
    # Notion Settings
    notion_database_id: str
    
    # Application Settings
    search_topic: str
    max_papers: int
    phase: str  # "ingestion", "query", or "both"
    user_query: Optional[str] = None
    arxiv_categories: Optional[list] = None  # Leave None for auto-search all categories
    
    # Paths
    data_dir: Path = Path("/app/data")
    outputs_dir: Path = Path("/app/outputs")
    logs_dir: Path = Path("/app/logs")
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        # Parse categories from comma-separated string if provided
        categories_str = os.getenv("ARXIV_CATEGORIES")
        categories = categories_str.split(",") if categories_str else None
        
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
            notion_token=os.getenv("NOTION_TOKEN"),
            pinecone_index_name=os.getenv("PINECONE_INDEX_NAME", "arxiv-papers"),
            pinecone_environment=os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws"),
            notion_database_id=os.getenv("NOTION_DATABASE_ID"),
            search_topic=os.getenv("SEARCH_TOPIC", "Higgs Boson production in association with a single top quark"),
            max_papers=int(os.getenv("MAX_PAPERS", "10")),
            phase=os.getenv("PHASE", "both"),
            user_query=os.getenv("USER_QUERY"),
            arxiv_categories=categories
        )