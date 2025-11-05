# ArXiv RAG MCP Agent

A containerized agentic pipeline using **Model Context Protocol (MCP)** servers for academic literature retrieval and question-answering.

## 🎯 Project Overview

**Phase 1 - Ingestion**: Search ArXiv papers → Scrape content → Chunk text → Embed & store in Pinecone  
**Phase 2 - Query**: Retrieve relevant context → Generate answer with GPT-4 → Log to Notion → Save locally

---

## 🔧 MCP Servers Used

### 1. **ArXiv MCP Server**
Search, download, and read academic papers from ArXiv.

```json
{
  "command": "uv",
  "args": ["tool", "run", "arxiv-mcp-server", "--storage-path", "/app/data/arxiv_papers"]
}
```

**Tools**: `search_papers`, `download_paper`, `read_paper`, `list_papers`

---

### 2. **Pinecone MCP**
Vector database for semantic search with integrated embeddings.

```json
{
  "command": "npx",
  "args": ["-y", "@pinecone-database/mcp"],
  "env": {
    "PINECONE_API_KEY": "${PINECONE_API_KEY}"
  }
}
```

**Index Configuration**:
- **Name**: `arxiv-papers`
- **Model**: `llama-text-embed-v2` (NVIDIA-hosted, free tier)
- **Dimension**: 1024
- **Metric**: cosine
- **Cloud**: AWS (us-east-1)

**Tools**: `create-index-for-model`, `upsert-records`, `query-index`, `describe-index-stats`

---

### 3. **Notion MCP**
Log query interactions to Notion database.

```json
{
  "command": "npx",
  "args": ["-y", "@notionhq/notion-mcp-server"],
  "env": {
    "NOTION_TOKEN": "${NOTION_TOKEN}"
  }
}
```

**Database Schema**:
- **Query** (Title) - The user's question
- **Timestamp** (Date) - When the query was made
- **Answer** (Rich Text) - GPT-4 generated answer
- **Sources** (Rich Text) - Top retrieved paper chunks

**Setup**: Create integration at https://www.notion.so/my-integrations and share database with it.

---

### 4. **Filesystem MCP**
Save final outputs locally.

```json
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/app/outputs"]
}
```

**Tools**: `read_file`, `write_file`, `list_directory`, `move_file`

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- API Keys:
  - OpenAI (GPT-4)
  - Pinecone
  - Notion integration token

### 2. Setup

```bash
# Clone repository
git clone <your-repo-url>
cd arxiv-rag-mcp

# Create .env file
touch .env
# Edit .env with your API keys

# Create Pinecone index (via web UI):
# - Name: arxiv-papers
# - Model: llama-text-embed-v2
# - Dimension: 1024, Metric: cosine

# Create Notion database with 4 columns:
# Query (Title), Timestamp (Date), Answer (Rich Text), Sources (Rich Text)
# Share it with your integration
```

### 3. Run

```bash
# Build and run both phases
docker-compose up

# Or run phases separately:

# Phase 1 only (ingestion)
docker-compose run --rm -e PHASE=ingestion arxiv-rag-agent

# Phase 2 only (query)
docker-compose run --rm -e PHASE=query -e USER_QUERY="Your question here" arxiv-rag-agent
```

### 4. View Results

```bash
# Check generated answer
cat outputs/answer.md

# View logs
docker-compose logs -f
```

---

## ⚙️ Configuration

Edit `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=arxiv-papers
NOTION_TOKEN=ntn_...
NOTION_DATABASE_ID=...

# Optional
SEARCH_TOPIC="Large Language Model Reasoning"
MAX_PAPERS=10
ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG  # Leave empty for all categories
PHASE=both  # ingestion, query, or both
```

**Category Examples**:
- AI/ML: `cs.AI,cs.CL,cs.LG`
- Physics: `hep-ph,hep-th,hep-ex`
- Biology: `q-bio.BM,q-bio.NC`
- Leave empty to search all ArXiv categories

---

## 📁 Project Structure

```
arxiv-rag-mcp/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── main.py
├── src/
│   ├── config.py
│   ├── mcp_manager.py
│   ├── phase1_ingestion.py
│   └── phase2_query.py
├── data/arxiv_papers/    # Downloaded papers
├── outputs/              # Generated answers
└── logs/                 # Application logs
```

---

## 📝 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) file for details.
