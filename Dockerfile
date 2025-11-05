# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Configure npm for global installations  
RUN npm config set prefix /usr/local

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Install MCP servers GLOBALLY using npm and uv (no npx)
RUN npm install -g @modelcontextprotocol/server-filesystem@latest
RUN npm install -g @pinecone-database/mcp@latest
RUN npm install -g @notionhq/notion-mcp-server@latest
RUN uv tool install arxiv-mcp-server

# Create directories
RUN mkdir -p /app/data/arxiv_papers /app/outputs /app/logs

# Copy application code
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.cargo/bin:/usr/local/bin:$PATH"

CMD ["python", "main.py"]