"""Phase 1: Ingestion Pipeline - Search ArXiv, download, and store in Pinecone"""
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
        print(f"   Found {len(papers)} papers\n")
        
        if not papers:
            print("⚠️  No papers found. Exiting ingestion phase.")
            return
        
        # Step 2: Download and process papers
        all_chunks = []
        papers_to_process = papers[:self.config.max_papers]
        
        for i, paper in enumerate(papers_to_process, 1):
            print(f"📄 Processing paper {i}/{len(papers_to_process)}")
            print(f"   Title: {paper.get('title', 'Unknown')[:60]}...")
            
            try:
                chunks = await self.process_paper(paper)
                all_chunks.extend(chunks)
                print(f"   ✅ Created {len(chunks)} chunks\n")
            except Exception as e:
                print(f"   ⚠️  Error processing paper: {e}\n")
                continue
        
        print(f"✂️  Total chunks created: {len(all_chunks)}\n")
        
        if not all_chunks:
            print("⚠️  No chunks created. Exiting ingestion phase.")
            return
        
        # Step 3: Create Pinecone index if needed
        print("🗄️  Checking Pinecone index...")
        await self.ensure_pinecone_index()
        
        # Step 4: Upsert chunks to Pinecone
        print(f"\n💾 Upserting {len(all_chunks)} chunks to Pinecone...")
        await self.upsert_to_pinecone(all_chunks)
        
        print("✅ Ingestion pipeline complete!\n")
    
    async def search_arxiv(self) -> List[Dict]:
        """Search ArXiv using MCP server"""
        # Build search arguments
        search_args = {
            "query": self.config.search_topic,
            "max_results": self.config.max_papers
        }
        
        # Only add categories if explicitly configured
        if self.config.arxiv_categories:
            search_args["categories"] = self.config.arxiv_categories
        
        result = await self.mcp.call_tool(
            "arxiv",
            "search_papers",
            search_args
        )
        
        # Parse the result (format depends on arxiv-mcp-server response)
        # The result might be in different formats, handle gracefully
        try:
            if hasattr(result, 'content') and result.content:
                # Try to parse as JSON
                content_text = result.content[0].text if isinstance(result.content, list) else str(result.content)
                papers = json.loads(content_text) if isinstance(content_text, str) else content_text
            else:
                papers = []
        except (json.JSONDecodeError, AttributeError, IndexError):
            papers = []
        
        return papers if isinstance(papers, list) else []
    
    async def process_paper(self, paper: Dict) -> List[Dict]:
        """Download paper and extract text using ArXiv MCP"""
        
        paper_id = paper.get("id") or paper.get("entry_id")
        if not paper_id:
            raise ValueError("Paper has no ID")
        
        # Download the paper using ArXiv MCP
        try:
            await self.mcp.call_tool(
                "arxiv",
                "download_paper",
                {"paper_id": paper_id}
            )
        except Exception as e:
            print(f"      Download warning: {e}")
        
        # Read the paper content using ArXiv MCP
        result = await self.mcp.call_tool(
            "arxiv",
            "read_paper",
            {"paper_id": paper_id}
        )
        
        # Extract text content
        paper_text = ""
        if hasattr(result, 'content') and result.content:
            paper_text = result.content[0].text if isinstance(result.content, list) else str(result.content)
        
        if not paper_text:
            raise ValueError("No text content extracted from paper")
        
        # Chunk the text (simple chunking - 1000 char chunks with 200 overlap)
        chunks = self._chunk_text(paper_text, chunk_size=1000, overlap=200)
        
        # Add metadata to each chunk
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            enriched_chunks.append({
                "text": chunk,
                "metadata": {
                    "paper_id": paper_id,
                    "title": paper.get("title", "Unknown"),
                    "authors": paper.get("authors", []),
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
            print(f"   ✅ Index '{self.config.pinecone_index_name}' already exists")
        
        except:
            # Create new index with integrated embedding
            print(f"   📝 Creating new index: {self.config.pinecone_index_name}")
            await self.mcp.call_tool(
                "pinecone",
                "create-index-for-model",
                {
                    "index_name": self.config.pinecone_index_name,
                    "model": "llama-text-embed-v2",  # Free NVIDIA-hosted model
                    "dimension": 1024,
                    "metric": "cosine"
                }
            )
            print(f"   ✅ Index created successfully")
    
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
        
        print(f"   ✅ Successfully upserted {len(records)} records")