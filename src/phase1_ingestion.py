"""Phase 1: Ingestion Pipeline - Search ArXiv, scrape, and store in Pinecone"""
import json
from typing import List, Dict

class IngestionPipeline:
    """Handles the ingestion of ArXiv papers into Pinecone"""
    
    def __init__(self, mcp_manager, config):
        self.mcp = mcp_manager
        self.config = config
    
    async def run(self):
        """Execute the full ingestion pipeline"""
        
        # Step 1: Search ArXiv papers
        print(f"🔍 Searching ArXiv for: {self.config.search_topic}")
        papers = await self.search_arxiv()
        print(f"Found {len(papers)} papers")
        
        # Step 2: Download and scrape paper content
        all_chunks = []
        for i, paper in enumerate(papers[:self.config.max_papers], 1):
            print(f"📄 Processing paper {i}/{min(len(papers), self.config.max_papers)}: {paper['title']}")
            chunks = await self.process_paper(paper)
            all_chunks.extend(chunks)
        
        print(f"✂️ Created {len(all_chunks)} text chunks")
        
        # Step 3: Create Pinecone index if needed
        await self.ensure_pinecone_index()
        
        # Step 4: Upsert chunks to Pinecone
        print(f"💾 Upserting {len(all_chunks)} chunks to Pinecone...")
        await self.upsert_to_pinecone(all_chunks)
        
        print("✅ Ingestion pipeline complete!")
    
    async def search_arxiv(self) -> List[Dict]:
        """Search ArXiv using MCP server"""
        result = await self.mcp.call_tool(
            "arxiv",
            "search_papers",
            {
                "query": self.config.search_topic,
                "max_results": self.config.max_papers,
                "categories": ["cs.AI", "cs.CL", "cs.LG"]
            }
        )
        
        # Parse the result (format depends on arxiv-mcp-server response)
        papers = json.loads(result.content[0].text) if result.content else []
        return papers
    
    async def process_paper(self, paper: Dict) -> List[Dict]:
        """Download paper and extract clean text"""
        
        # Get paper URL
        paper_url = paper.get("pdf_url") or paper.get("url")
        
        # Use Firecrawl to scrape and clean the content
        result = await self.mcp.call_tool(
            "firecrawl",
            "scrape_url",
            {
                "url": paper_url,
                "formats": ["markdown"],
                "onlyMainContent": True
            }
        )
        
        # Extract clean text
        clean_text = result.content[0].text if result.content else ""
        
        # Chunk the text (simple chunking - 1000 char chunks with 200 overlap)
        chunks = self._chunk_text(clean_text, chunk_size=1000, overlap=200)
        
        # Add metadata to each chunk
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            enriched_chunks.append({
                "text": chunk,
                "metadata": {
                    "paper_id": paper.get("id"),
                    "title": paper.get("title"),
                    "authors": paper.get("authors"),
                    "url": paper_url,
                    "chunk_index": i
                }
            })
        
        return enriched_chunks
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Simple text chunking with overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks
    
    async def ensure_pinecone_index(self):
        """Create Pinecone index if it doesn't exist"""
        try:
            # Try to get index stats
            await self.mcp.call_tool(
                "pinecone",
                "describe-index-stats",
                {"index_name": self.config.pinecone_index_name}
            )
            print(f"✓ Index '{self.config.pinecone_index_name}' already exists")
        
        except:
            # Create new index with integrated embedding
            print(f"Creating new index: {self.config.pinecone_index_name}")
            await self.mcp.call_tool(
                "pinecone",
                "create-index-for-model",
                {
                    "index_name": self.config.pinecone_index_name,
                    "model": "multilingual-e5-large",  # Pinecone's integrated model
                    "dimension": 1024,
                    "metric": "cosine"
                }
            )
    
    async def upsert_to_pinecone(self, chunks: List[Dict]):
        """Upsert text chunks to Pinecone with automatic embedding"""
        
        # Prepare records for upserting
        records = []
        for i, chunk in enumerate(chunks):
            records.append({
                "id": f"chunk_{i}",
                "text": chunk["text"],  # Pinecone will auto-embed this
                "metadata": chunk["metadata"]
            })
        
        # Batch upsert (Pinecone handles batching internally)
        await self.mcp.call_tool(
            "pinecone",
            "upsert-records",
            {
                "index_name": self.config.pinecone_index_name,
                "records": records
            }
        )