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
    print(f"Max Papers: {config.max_papers}\n")
    
    # Initialize MCP Manager
    mcp_manager = MCPManager(config)
    
    try:
        # Connect to all MCP servers with overall timeout
        print("⏳ Connecting to MCP servers (this may take up to 2 minutes)...\n")
        await asyncio.wait_for(
            mcp_manager.connect_all(),
            timeout=120  # 2 minute total timeout
        )
        
        # Phase 1: Ingestion
        if config.phase in ["ingestion", "both"]:
            print("\n" + "="*60)
            print("📥 PHASE 1: INGESTION PIPELINE")
            print("="*60 + "\n")
            
            ingestion = IngestionPipeline(mcp_manager, config)
            await ingestion.run()
            
            print("\n" + "="*60)
            print("✅ Phase 1 Complete: Papers ingested into Pinecone")
            print("="*60 + "\n")
        
        # Phase 2: Query
        if config.phase in ["query", "both"]:
            print("\n" + "="*60)
            print("🔍 PHASE 2: QUERY PIPELINE")
            print("="*60 + "\n")
            
            query = QueryPipeline(mcp_manager, config)
            
            # Example query (can be modified or passed as argument)
            user_query = config.user_query or "What is special about the interaction between the Higgs boson and the top quark?"
            
            print(f"Query: {user_query}\n")
            answer = await query.run(user_query)
            
            print("\n" + "="*60)
            print("✅ Phase 2 Complete")
            print(f"📄 Answer saved to: /app/outputs/answer.md")
            print("="*60 + "\n")
    
    except asyncio.TimeoutError:
        print("\n❌ Timeout Error: MCP server connection took too long")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user (Ctrl+C)")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        try:
            await asyncio.wait_for(
                mcp_manager.disconnect_all(),
                timeout=10
            )
        except asyncio.TimeoutError:
            print("⚠️  Cleanup timeout - forcing exit")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
        
        print("\n🔒 All connections closed")
        print("👋 Goodbye!\n")

if __name__ == "__main__":
    asyncio.run(main())