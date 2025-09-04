from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, find_dotenv
import io
from . import file_service, github_service, youtube_service, email_service, steam_service, summarize_service

def _load_env_robust():
	try:
		path = find_dotenv()
		if path:
			load_dotenv(dotenv_path=path, encoding="utf-8")
		else:
			load_dotenv(encoding="utf-8")
		return
	except UnicodeDecodeError:
		pass
	for enc in ("utf-8-sig", "utf-16", "latin-1"):
		try:
			from pathlib import Path
			cand = find_dotenv() or ".env"
			with open(cand, "rb") as f:
				text = f.read().decode(enc)
			load_dotenv(stream=io.StringIO(text))
			return
		except Exception:
			continue

_load_env_robust()
server = FastMCP("personal-hub-server")

# Register all services
for svc in [file_service, github_service, youtube_service, email_service, steam_service, summarize_service]:
	svc.register(server)
	print(f"Registered service: {svc.__name__}")


if __name__ == "__main__":
	server.run()