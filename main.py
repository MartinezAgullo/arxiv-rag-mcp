#!/usr/bin/env python3
"""
Main entry point for ArXiv RAG MCP Agent
"""
import asyncio
import sys
from pathlib import Path

from src.config import Config
from src.mcp_manager import MCPManager
from src.phase1_ingestion import IngestionPipeline
from src.phase2_query import QueryPipeline

async def main():
    """Main execution function"""
    config = Config.from_env()
    
    print("🚀 Starting ArXiv RAG MCP Agent")
    print(f"Phase: {config.phase}")
    print(f"Topic: {config.search_topic}")
    
    # Initialize MCP Manager
    mcp_manager = MCPManager(config)
    
    try:
        # Connect to all MCP servers
        await mcp_manager.connect_all()
        print("✅ All MCP servers connected")
        
        # Phase 1: Ingestion
        if config.phase in ["ingestion", "both"]:
            print("\n📥 Starting Phase 1: Ingestion Pipeline")
            ingestion = IngestionPipeline(mcp_manager, config)
            await ingestion.run()
            print("✅ Phase 1 Complete: Papers ingested into Pinecone")
        
        # Phase 2: Query
        if config.phase in ["query", "both"]:
            print("\n🔍 Starting Phase 2: Query Pipeline")
            query = QueryPipeline(mcp_manager, config)
            
            # Example query (can be modified or passed as argument)
            user_query = config.user_query or "What are the latest techniques in LLM reasoning?"
            
            answer = await query.run(user_query)
            print(f"\n✅ Phase 2 Complete")
            print(f"Answer saved to: /app/outputs/answer.md")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup
        await mcp_manager.disconnect_all()
        print("\n🔒 All connections closed")

if __name__ == "__main__":
    asyncio.run(main())