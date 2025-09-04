from flask import Flask, render_template, request, jsonify
import os
import re
import requests
from mcp_server.file_service import list_local_text_files, read_local_text_file
from mcp_server.youtube_service import list_liked_videos, list_liked_songs

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

	# Simple intents for YouTube liked content
	# Extract a requested limit if present (e.g., "first 5", "top 10")
	limit_match = re.search(r"(?:first|top)\s+(\d+)", lq)
	limit = int(limit_match.group(1)) if limit_match else 5

	if (("liked" in lq and "video" in lq) or ("yt" in lq and "liked" in lq and "video" in lq) or ("youtube" in lq and "liked" in lq and "video" in lq)):
		items = list_liked_videos(limit=limit)
		return jsonify({"answer": items})
	if (("liked" in lq and "song" in lq) or ("ytm" in lq and "liked" in lq and "song" in lq) or ("youtube music" in lq and "liked" in lq)):
		items = list_liked_songs(limit=limit)
		return jsonify({"answer": items})

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
		return jsonify({"answer": answer})
	except Exception as e:
		# Fallback: echo the query with error info
		return jsonify({
			"answer": f"You asked: '{user_query}'.",
			"warning": "LM Studio not reachable; returning fallback response.",
			"error": str(e)
		}), 200


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True) 