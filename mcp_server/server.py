from mcp.server.fastmcp import FastMCP
from . import file_service, github_service, youtube_service, email_service, steam_service, summarize_service

server = FastMCP("personal-hub-server")

# Register all services
for svc in [file_service, github_service, youtube_service, email_service, steam_service, summarize_service]:
	svc.register(server)
	print(f"Registered service: {svc.__name__}")


if __name__ == "__main__":
	server.run()