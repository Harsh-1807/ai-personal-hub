from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv, find_dotenv
import io
import os
import re
import requests
from mcp_server.file_service import list_local_text_files, read_local_text_file
from mcp_server.steam_service import list_owned_games, app_user_details, get_owned_count
try:
	from mcp_server.ytmusic_service import list_liked_songs_free, list_liked_songs_all
except Exception:
	list_liked_songs_free = None
	list_liked_songs_all = None
try:
	from mcp_server.steam_service import playtime_for_name
except Exception:
	playtime_for_name = None


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
	# Fallback: manually read and feed via stream with lenient encodings
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
app = Flask(__name__)


@app.route("/", methods=["GET"]) 
def index():
	return render_template("index.html")


@app.route("/ask", methods=["POST"]) 
def ask():
	user_query = request.form.get("query", "").strip()
	if not user_query:
		return jsonify({"error": "Query is required"}), 400

	# Simple intents for local notes without LM Studio tool calls
	lq = user_query.lower()
	if "list" in lq and ("note" in lq or "notes" in lq):
		files = list_local_text_files()
		return jsonify({"answer": files})

	match = re.search(r"(?:open|read|fetch)\s+([\w.-]+\.txt)", lq)
	if match:
		name = match.group(1)
		try:
			content = read_local_text_file(name)
			return jsonify({"answer": content})
		except Exception as e:
			return jsonify({"error": str(e)}), 400

	# Steam playtime intent by name
	m_play = re.search(r"how (?:many|much) (?:hours|time).*(?:for|in|on)\s+(.+)$", lq)
	if m_play and playtime_for_name is not None:
		qname = m_play.group(1).strip().strip('?!.')
		res = playtime_for_name(qname)
		if isinstance(res, dict) and res.get("best_match"):
			bm = res["best_match"]
			return jsonify({"answer": f"You played {bm['name']} for {bm['hours']} hours ({bm['minutes']} minutes).", "details": res})
		return jsonify(res)

	# YT Music liked songs intent (free path)
	limit_match = re.search(r"(?:first|top)\s+(\d+)", lq)
	limit = int(limit_match.group(1)) if limit_match else 5
	if (("liked" in lq and "song" in lq) or ("ytm" in lq and "liked" in lq and "song" in lq) or ("youtube music" in lq and "liked" in lq)):
		if list_liked_songs_all is not None and ("all" in lq or "everything" in lq):
			items = list_liked_songs_all()
			return jsonify({"answer": items})
		if list_liked_songs_free is not None:
			items = list_liked_songs_free(limit=limit)
			return jsonify({"answer": items})
		return jsonify({"error": "YT Music headers not configured. Set YTMUSIC_HEADERS_FILE or YTMUSIC_HEADERS_JSON."}), 400

	# Simple intents for Steam
	if "steam" in lq and ("games" in lq or "list" in lq):
		if "all" in lq or "everything" in lq:
			items = list_owned_games(limit=10000)
			return jsonify({"answer": items})
		limit_match2 = re.search(r"(first|top)\s+(\d+)", lq)
		limit2 = int(limit_match2.group(2)) if limit_match2 else 25
		items = list_owned_games(limit=limit2)
		return jsonify({"answer": items})
	if "user details" in lq and "appid" in lq:
		ids = re.findall(r"\b\d{3,7}\b", lq)
		if ids:
			data = app_user_details(appids=",".join(ids))
			return jsonify({"answer": data})

	# Steam: count owned games
	if ("how many" in lq and "game" in lq) or ("games do i own" in lq):
		data = get_owned_count()
		if isinstance(data, dict) and "count" in data:
			return jsonify({"answer": f"You own {data['count']} games on Steam."})
		return jsonify({"answer": data})

	# GitHub repos intent by username or profile URL
	m_gh_repos = re.search(r"github\s+(?:repos|repositories)\s+(?:for\s+)?(@?[\w-]+|https?://github\.com/([\w-]+))", lq)
	if m_gh_repos:
		u1 = m_gh_repos.group(1) if m_gh_repos.group(1) else ""
		u2 = m_gh_repos.group(2) if len(m_gh_repos.groups()) > 1 else ""
		username = (u2 or u1).lstrip('@')
		try:
			h = {"Accept": "application/vnd.github+json"}
			gh_token = os.getenv("GITHUB_TOKEN")
			if gh_token:
				h["Authorization"] = f"token {gh_token}"
			url = f"https://api.github.com/users/{username}/repos?per_page=100&page=1&sort=updated"
			res = requests.get(url, headers=h, timeout=20).json()
			items = res if isinstance(res, list) else []
			answer = [{"name": r.get("name"), "url": r.get("html_url"), "stars": r.get("stargazers_count", 0)} for r in items]
			return jsonify({"answer": answer})
		except Exception as e:
			return jsonify({"error": str(e)}), 400

	# Build automatic context for the model based on available integrations
	def gather_auto_context(prompt_text: str):
		ctx = {}
		# Steam context (if credentials present)
		try:
			steam_count = get_owned_count()
			if isinstance(steam_count, dict) and "count" in steam_count:
				owned = list_owned_games(limit=10000)
				if isinstance(owned, list) and owned:
					ordered = sorted(owned, key=lambda g: int(g.get("playtime_forever_min", 0) or 0), reverse=True)
					ctx["steam"] = {
						"owned_count": steam_count["count"],
						"top_games": [
							{"name": g.get("name"), "appid": g.get("appid"), "min": int(g.get("playtime_forever_min", 0) or 0)}
							for g in ordered[:25]
						]
					}
		except Exception:
			pass

		# YT Music context
		try:
			if list_liked_songs_free is not None:
				liked_songs = list_liked_songs_free(limit=10)
				if isinstance(liked_songs, list) and liked_songs:
					ctx["ytmusic"] = {"liked_songs": [{"title": s.get("title"), "artist": s.get("artist"), "url": s.get("url")} for s in liked_songs]}
		except Exception:
			pass

		# GitHub context (optional) - uses env GITHUB_USER and GITHUB_REPO if set
		try:
			gh_user = os.getenv("GITHUB_USER")
			gh_repo = os.getenv("GITHUB_REPO")
			gh_token = os.getenv("GITHUB_TOKEN")
			if gh_user and gh_repo:
				h = {"Accept": "application/vnd.github+json"}
				if gh_token:
					h["Authorization"] = f"token {gh_token}"
				url = f"https://api.github.com/repos/{gh_user}/{gh_repo}/commits?per_page=100&page=1"
				res = requests.get(url, headers=h, timeout=15).json()
				if isinstance(res, list):
					ctx["github"] = {
						"repo": f"{gh_user}/{gh_repo}",
						"recent_commits": [
							{"sha": c.get("sha"), "msg": (c.get("commit", {}) or {}).get("message")}
							for c in res[:10]
						]
					}
		except Exception:
			pass

		return ctx

	def context_to_system_prompt(ctx: dict) -> str:
		if not ctx:
			return ""
		parts = []
		steam = ctx.get("steam")
		if steam:
			parts.append(f"Steam: owned_count={steam.get('owned_count')} top_games=" + ", ".join([g.get("name") for g in steam.get("top_games", [])]))
		ytm = ctx.get("ytmusic")
		if ytm:
			parts.append("YT Music liked: " + ", ".join([v.get("title") for v in ytm.get("liked_songs", [])]))
		gh = ctx.get("github")
		if gh:
			parts.append(f"GitHub {gh.get('repo')} recent commits: " + "; ".join([(c.get("msg") or "").split("\n")[0][:80] for c in gh.get("recent_commits", [])]))
		return "Context: " + " | ".join(parts)

	auto_ctx = gather_auto_context(user_query)
	ctx_prompt = context_to_system_prompt(auto_ctx)

	# Call LM Studio (OpenAI-compatible API) if available
	base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234")
	api_key = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
	model = os.getenv("LM_STUDIO_MODEL", "local-model")

	try:
		resp = requests.post(
			f"{base_url}/v1/chat/completions",
			headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
			json={
				"model": model,
				"messages": [
					{"role": "system", "content": "You are a helpful personal assistant."},
					*([{ "role": "system", "content": ctx_prompt }] if ctx_prompt else []),
					{"role": "user", "content": user_query}
				],
				"temperature": 0.2
			}
		)
		resp.raise_for_status()
		data = resp.json()
		answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
		if not answer:
			answer = "(No content returned from LM Studio)"
		return jsonify({"answer": answer, "context": auto_ctx})
	except Exception as e:
		return jsonify({
			"answer": f"You asked: '{user_query}'.",
			"warning": "LM Studio not reachable; returning fallback response.",
			"error": str(e),
			"context": auto_ctx
		}), 200


# Public API proxy endpoints
@app.route("/api/steam/owned-games", methods=["GET"]) 
def api_steam_owned_games():
	limit = request.args.get("limit", default=50, type=int)
	items = list_owned_games(limit=limit)
	return jsonify(items)


@app.route("/api/steam/owned-count", methods=["GET"]) 
def api_steam_owned_count():
	data = get_owned_count()
	return jsonify(data)


@app.route("/api/ytmusic/liked-all", methods=["GET"]) 
def api_ytmusic_liked_all():
	if list_liked_songs_all is None:
		return jsonify({"error": "YT Music headers not configured."}), 400
	items = list_liked_songs_all()
	return jsonify(items)


@app.route("/api/context", methods=["GET"]) 
def api_context():
	q = request.args.get("q", default="", type=str)
	ctx = {} if q == "" else None
	if ctx is None:
		ctx = {}
	try:
		ctx = ctx or {}
		def gather_auto_context_for_api(prompt_text):
			return gather_auto_context(prompt_text)
		return jsonify(gather_auto_context_for_api(q))
	except Exception as e:
		return jsonify({"error": str(e)})


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True) 