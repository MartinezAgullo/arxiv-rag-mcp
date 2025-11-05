"""MCP Server Connection Manager"""
import asyncio
from typing import Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPManager:
    """Manages connections to multiple MCP servers"""
    
    def __init__(self, config):
        self.config = config
        self.sessions: Dict[str, ClientSession] = {}
        self.stdio_contexts: Dict[str, Any] = {}  # Store context managers
        
        # Define MCP server configurations
        self.server_configs = {
            "arxiv": {
                "command": "uv",
                "args": ["tool", "run", "arxiv-mcp-server", "--storage-path", str(config.data_dir / "arxiv_papers")],
                "env": {"ARXIV_STORAGE_PATH": str(config.data_dir / "arxiv_papers")}
            },
            "pinecone": {
                "command": "npx",
                "args": ["-y", "@pinecone-database/mcp"],
                "env": {"PINECONE_API_KEY": config.pinecone_api_key}
            },
            "notion": {
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {"NOTION_TOKEN": config.notion_token}
            },
            "filesystem": {
                "command": "mcp-server-filesystem",  # Use installed binary directly
                "args": [str(config.outputs_dir)],
                "env": {}
            }
        }
    
    async def connect_server(self, server_name: str):
        """Connect to a specific MCP server"""
        server_config = self.server_configs[server_name]
        
        print(f"  📡 Connecting to {server_name}...", end=" ", flush=True)
        
        try:
            # Create server parameters
            server = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env", {})
            )
            
            # Create and enter the stdio context
            stdio_context = stdio_client(server)
            read_stream, write_stream = await stdio_context.__aenter__()
            
            # Store the context for later cleanup
            self.stdio_contexts[server_name] = stdio_context
            
            # Create session
            session = ClientSession(read_stream, write_stream)
            
            # Initialize with timeout
            await asyncio.wait_for(session.initialize(), timeout=30)
            
            # Store session
            self.sessions[server_name] = session
            
            print("✅")
            
        except asyncio.TimeoutError:
            print(f"❌ (timeout)")
            raise TimeoutError(f"Connection to {server_name} timed out after 30 seconds")
        except Exception as e:
            print(f"❌ ({str(e)[:50]})")
            raise RuntimeError(f"Failed to connect to {server_name}: {e}")
    
    async def connect_all(self):
        """Connect to all MCP servers"""
        print("🔌 Initializing MCP servers:\n")
        
        # Connect sequentially to avoid overwhelming the system
        for server_name in self.server_configs.keys():
            await self.connect_server(server_name)
        
        print("\n✅ All MCP servers connected successfully!\n")
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None):
        """Call a tool on a specific MCP server"""
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
        
        try:
            result = await session.call_tool(tool_name, arguments=arguments or {})
            return result
        except Exception as e:
            raise RuntimeError(f"Error calling {tool_name} on {server_name}: {e}")
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        print("🔌 Disconnecting from MCP servers:\n")
        
        for server_name, stdio_context in self.stdio_contexts.items():
            try:
                print(f"  📡 Disconnecting from {server_name}...", end=" ", flush=True)
                await stdio_context.__aexit__(None, None, None)
                print("✅")
            except Exception as e:
                print(f"⚠️ (error: {str(e)[:30]})")
        
        self.sessions.clear()
        self.stdio_contexts.clear()
        print()