# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN curl -fsSL https://astral.sh/uv/install.sh | bash
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install MCP servers via npx (cached for faster rebuilds)
RUN npx -y firecrawl-mcp --version || true
RUN npx -y @pinecone-database/mcp --version || true
RUN npx -y @notionhq/notion-mcp-server --version || true
RUN npx -y @modelcontextprotocol/server-filesystem --version || true
RUN uv tool install arxiv-mcp-server || true

# Create necessary directories
RUN mkdir -p /app/data/arxiv_papers /app/outputs /app/logs

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the agent
CMD ["python", "main.py"]