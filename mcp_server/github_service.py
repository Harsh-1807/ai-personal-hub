import os
import requests


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_token_here")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def register(server):
	@server.tool("github_repos")
	def github_repos(user: str):
		url = f"https://api.github.com/users/{user}/repos"
		res = requests.get(url, headers=HEADERS).json()
		return [{"name": r.get("name"), "url": r.get("html_url")} for r in res if isinstance(res, list)]

	@server.tool("github_commits")
	def github_commits(user: str, repo: str):
		url = f"https://api.github.com/repos/{user}/{repo}/commits"
		res = requests.get(url, headers=HEADERS).json()
		items = res if isinstance(res, list) else []
		return [{"sha": c.get("sha"), "msg": c.get("commit", {}).get("message")} for c in items[:5]]

	@server.tool("github_commits_paginated")
	def github_commits_paginated(user: str, repo: str, page: int = 1, per_page: int = 100):
		"""Fetch commits with pagination to allow full history retrieval."""
		if per_page > 100:
			per_page = 100
		url = f"https://api.github.com/repos/{user}/{repo}/commits?page={page}&per_page={per_page}"
		res = requests.get(url, headers=HEADERS).json()
		items = res if isinstance(res, list) else []
		return [{
			"sha": c.get("sha"),
			"msg": (c.get("commit", {}) or {}).get("message"),
			"author": ((c.get("commit", {}) or {}).get("author", {}) or {}).get("name"),
			"date": ((c.get("commit", {}) or {}).get("author", {}) or {}).get("date"),
			"url": c.get("html_url")
		} for c in items]

	@server.tool("github_list_files")
	def github_list_files(user: str, repo: str, path: str = ""):
		# Uses Contents API
		url = f"https://api.github.com/repos/{user}/{repo}/contents/{path}"
		res = requests.get(url, headers=HEADERS).json()
		items = res if isinstance(res, list) else []
		return [
			{"name": i.get("name"), "path": i.get("path"), "type": i.get("type")}
			for i in items
		]

	@server.tool("github_file_content")
	def github_file_content(user: str, repo: str, path: str):
		url = f"https://api.github.com/repos/{user}/{repo}/contents/{path}"
		res = requests.get(url, headers=HEADERS).json()
		if isinstance(res, dict) and res.get("encoding") == "base64":
			import base64
			content = base64.b64decode(res.get("content", "")).decode("utf-8", errors="ignore")
			return {"path": path, "content": content}
		return {"path": path, "error": "Not a file or content unavailable"}

	@server.tool("github_issues")
	def github_issues(user: str, repo: str, state: str = "open", limit: int = 10):
		url = f"https://api.github.com/repos/{user}/{repo}/issues?state={state}&per_page={limit}"
		res = requests.get(url, headers=HEADERS).json()
		items = res if isinstance(res, list) else []
		return [
			{"number": i.get("number"), "title": i.get("title"), "state": i.get("state"), "url": i.get("html_url")}
			for i in items if "pull_request" not in i
		]

	@server.tool("github_issue")
	def github_issue(user: str, repo: str, number: int):
		url = f"https://api.github.com/repos/{user}/{repo}/issues/{number}"
		res = requests.get(url, headers=HEADERS).json()
		if isinstance(res, dict):
			return {
				"number": res.get("number"),
				"title": res.get("title"),
				"state": res.get("state"),
				"body": res.get("body"),
				"url": res.get("html_url")
			}
		return {"error": "Issue not found"}