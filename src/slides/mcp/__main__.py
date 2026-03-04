from .server import create_server

mcp = create_server()
mcp.run(transport="streamable-http")
