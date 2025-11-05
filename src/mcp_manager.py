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
        self.clients = {}
        
        # Define MCP server configurations
        self.server_configs = {
            "arxiv": {
                "command": "uv",
                "args": ["tool", "run", "arxiv-mcp-server", "--storage-path", str(config.data_dir / "arxiv_papers")],
                "env": {"ARXIV_STORAGE_PATH": str(config.data_dir / "arxiv_papers")}
            },
            "firecrawl": {
                "command": "npx",
                "args": ["-y", "firecrawl-mcp"],
                "env": {"FIRECRAWL_API_KEY": config.firecrawl_api_key}
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
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", str(config.outputs_dir)],
                "env": {}
            }
        }
    
    async def connect_server(self, server_name: str):
        """Connect to a specific MCP server"""
        server_config = self.server_configs[server_name]
        
        # Create server parameters
        server = StdioServerParameters(
            command=server_config["command"],
            args=server_config["args"],
            env=server_config.get("env", {})
        )
        
        # Connect using stdio client
        stdio = stdio_client(server)
        client, session = await stdio.__aenter__()
        
        self.clients[server_name] = (stdio, client)
        self.sessions[server_name] = session
        
        # Initialize the session
        await session.initialize()
        
        print(f"✓ Connected to {server_name} MCP server")
    
    async def connect_all(self):
        """Connect to all MCP servers"""
        tasks = [self.connect_server(name) for name in self.server_configs.keys()]
        await asyncio.gather(*tasks)
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]):
        """Call a tool on a specific MCP server"""
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
        
        result = await session.call_tool(tool_name, arguments=arguments)
        return result
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for server_name, (stdio, _) in self.clients.items():
            await stdio.__aexit__(None, None, None)
            print(f"✓ Disconnected from {server_name}")