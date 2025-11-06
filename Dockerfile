FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl git nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Set npm prefix for global installs
RUN npm config set prefix /usr/local

WORKDIR /app

# CRITICAL FIX: Install dependencies in correct order
# 1. First install requirements.txt with pinned mcp==1.0.0
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. THEN install arxiv-mcp-server (it will use the already-installed mcp==1.0.0)
# Use --no-deps to prevent it from upgrading mcp to 1.20.0
#RUN pip install --no-cache-dir --no-deps arxiv-mcp-server
                              # ^^^^^^^^
                              # THIS IS THE KEY FIX!

# OR alternatively, if --no-deps breaks it, reinstall mcp==1.0.0 after:
RUN pip install --no-cache-dir arxiv-mcp-server && \
    pip install --no-cache-dir --force-reinstall mcp==1.0.0

# Install Node MCP servers globally
RUN npm install -g @modelcontextprotocol/server-filesystem@latest
RUN npm install -g @pinecone-database/mcp@latest
RUN npm install -g @notionhq/notion-mcp-server@latest

# Verify installations
RUN echo "=== Verifying MCP Server Installations ===" && \
    which mcp-server-filesystem && echo "✓ Filesystem MCP found" && \
    which arxiv-mcp-server && echo "✓ ArXiv MCP found" && \
    which pinecone-mcp && echo "✓ Pinecone MCP found" && \
    which notion-mcp-server && echo "✓ Notion MCP found" && \
    echo "=== All MCP servers installed successfully ===" && \
    echo "" && \
    echo "=== Verifying MCP SDK Version ===" && \
    pip show mcp | grep "Version:" && \
    echo "=== Should show: Version: 1.0.0 ==="
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # This verification is CRITICAL - must show 1.0.0!

# Create necessary directories
RUN mkdir -p /app/data/arxiv_papers /app/outputs /app/logs

# Copy application code
COPY . .

# Set Python to unbuffered mode for real-time logs
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]