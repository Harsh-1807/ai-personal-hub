import os


def list_local_text_files(notes_dir: str = "./notes"):
	if not os.path.isdir(notes_dir):
		return []
	return [f for f in os.listdir(notes_dir) if f.endswith(".txt")]


def read_local_text_file(name: str, notes_dir: str = "./notes"):
	path = os.path.join(notes_dir, name)
	# Try a few common encodings gracefully
	for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
		try:
			with open(path, "r", encoding=enc, errors="strict") as f:
				return f.read()
		except UnicodeDecodeError:
			continue
	# Last resort: read bytes and decode with replacement to avoid crashes
	with open(path, "rb") as f:
		return f.read().decode("utf-8", errors="replace")


def register(server):
	@server.tool("list_local_files")
	def list_files():
		return [{"name": f, "uri": f"file://{f}"} for f in list_local_text_files()]

	@server.tool("fetch_local_file")
	def fetch_file(name: str):
		return {"content": read_local_text_file(name)}