# ArXiv RAG MCP Agent

## Project Overview
A containerized agentic pipeline using Model Context Protocol (MCP) servers for:

Phase 1: Ingesting ArXiv papers into Pinecone vector database
Phase 2: Querying with RAG and logging to Notion


- Notion database with:
Query (Title)
Timestamp (Date)
Answer (Rich Text)
Sources (Rich Text)
- Pinnecone index named arxiv-paper created with llama-text-embed-v2 using cosine as metric and dimension 1024.