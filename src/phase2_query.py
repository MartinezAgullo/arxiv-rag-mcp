"""Phase 2: Query Pipeline - Retrieve from Pinecone, generate answer, log to Notion"""
import json
from datetime import datetime
from typing import List, Dict
import openai

class QueryPipeline:
    """Handles querying the vector database and generating answers"""
    
    def __init__(self, mcp_manager, config):
        self.mcp = mcp_manager
        self.config = config
        
        # Initialize OpenAI client for GPT-4
        openai.api_key = config.openai_api_key
        self.client = openai.OpenAI()
    
    async def run(self, user_query: str) -> str:
        """Execute the query pipeline"""
        
        print(f"💭 User Query: {user_query}\n")
        
        # Step 1: Retrieve relevant chunks from Pinecone
        print("🔍 Retrieving relevant context from Pinecone...")
        context_chunks = await self.retrieve_context(user_query)
        print(f"   ✅ Retrieved {len(context_chunks)} relevant chunks\n")
        
        # Step 2: Generate answer using GPT-4
        print("🤖 Generating answer with GPT-4...")
        answer = await self.generate_answer(user_query, context_chunks)
        print(f"   ✅ Answer generated ({len(answer)} chars)\n")
        
        # Step 3: Log to Notion
        print("📝 Logging interaction to Notion...")
        try:
            await self.log_to_notion(user_query, context_chunks, answer)
            print("   ✅ Logged to Notion\n")
        except Exception as e:
            print(f"   ⚠️  Notion logging failed: {e}\n")
        
        # Step 4: Save answer locally
        print("💾 Saving answer to file...")
        await self.save_answer(answer)
        print("   ✅ Saved to /app/outputs/answer.md\n")
        
        return answer
    
    async def retrieve_context(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant chunks from Pinecone"""
        
        result = await self.mcp.call_tool(
            "pinecone",
            "query-index",
            {
                "index_name": self.config.pinecone_index_name,
                "query": query,  # Pinecone will auto-embed this
                "top_k": top_k,
                "include_metadata": True
            }
        )
        
        # Parse results
        matches = []
        if hasattr(result, 'content') and result.content:
            try:
                content_text = result.content[0].text if isinstance(result.content, list) else str(result.content)
                matches = json.loads(content_text) if isinstance(content_text, str) else []
            except (json.JSONDecodeError, AttributeError):
                matches = []
        
        return matches if isinstance(matches, list) else []
    
    async def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate answer using GPT-4 with retrieved context"""
        
        # Format context
        context_text = "\n\n".join([
            f"[Source: {c.get('metadata', {}).get('title', 'Unknown')}]\n{c.get('text', '')}"
            for c in context_chunks
            if c.get('text')
        ])
        
        if not context_text:
            return "I couldn't find relevant information in the database to answer your question."
        
        # Create prompt
        prompt = f"""You are a helpful AI assistant that answers questions based on academic papers about {self.config.search_topic}.

Use ONLY the context provided below to answer the question. If the context doesn't contain enough information, say so.

CONTEXT:
{context_text}

QUESTION: {query}

Provide a concise, well-cited answer. Include paper titles when referencing information."""
        
        # Call GPT-4
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            return answer
        
        except Exception as e:
            return f"Error generating answer: {e}"
    
    async def log_to_notion(self, query: str, context: List[Dict], answer: str):
        """Log the interaction to Notion database"""
        
        # Format context for Notion
        context_summary = "\n".join([
            f"- {c.get('metadata', {}).get('title', 'Unknown')} (Chunk {c.get('metadata', {}).get('chunk_index', 0)})"
            for c in context[:3]  # Top 3 sources
        ])
        
        # Create page in Notion database
        await self.mcp.call_tool(
            "notion",
            "notion_create_page",
            {
                "parent": {"database_id": self.config.notion_database_id},
                "properties": {
                    "Query": {"title": [{"text": {"content": query}}]},
                    "Timestamp": {"date": {"start": datetime.utcnow().isoformat()}},
                    "Answer": {"rich_text": [{"text": {"content": answer[:2000]}}]},  # Notion limit
                    "Sources": {"rich_text": [{"text": {"content": context_summary}}]}
                }
            }
        )
    
    async def save_answer(self, answer: str):
        """Save answer to local file using filesystem MCP"""
        
        markdown_content = f"""# Query Results
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Topic**: {self.config.search_topic}

## Answer

{answer}

---
*Generated by ArXiv RAG MCP Agent*
"""
        
        await self.mcp.call_tool(
            "filesystem",
            "write_file",
            {
                "path": "answer.md",  # Relative to allowed directory
                "content": markdown_content
            }
        )