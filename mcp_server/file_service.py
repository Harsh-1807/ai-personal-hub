import os


def list_local_text_files(notes_dir: str = "./notes"):
	if not os.path.isdir(notes_dir):
		return []
	return [f for f in os.listdir(notes_dir) if f.endswith(".txt")]


def read_local_text_file(name: str, notes_dir: str = "./notes"):
	path = os.path.join(notes_dir, name)
	with open(path, "r", encoding="utf-8") as f:
		return f.read()


def register(server):
	@server.tool("list_local_files")
	def list_files():
		return [{"name": f, "uri": f"file://{f}"} for f in list_local_text_files()]

	@server.tool("fetch_local_file")
	def fetch_file(name: str):
		return {"content": read_local_text_file(name)}