import os
import json


def _load_headers():
	"""Load YouTube Music auth headers for ytmusicapi from env.

	Supports either a JSON string in YTMUSIC_HEADERS_JSON or a path in YTMUSIC_HEADERS_FILE.
	The content should be what `ytmusicapi.setup` exports (headers.json).
	"""
	data = os.getenv("YTMUSIC_HEADERS_JSON")
	if data:
		try:
			return json.loads(data)
		except Exception:
			return None
	path = os.getenv("YTMUSIC_HEADERS_FILE", "headers_auth.json")
	if os.path.exists(path):
		try:
			with open(path, "r", encoding="utf-8") as f:
				return json.load(f)
		except Exception:
			return None
	return None


def _ytm():
	try:
		from ytmusicapi import YTMusic
		headers = _load_headers()
		if not headers:
			return None
		return YTMusic(headers)
	except Exception:
		return None


def _map_track(t):
	# Map ytmusicapi track to our schema
	title = (t.get("title") if isinstance(t, dict) else None) or ""
	artists = []
	try:
		artists = [a.get("name") for a in (t.get("artists") or []) if isinstance(a, dict)]
	except Exception:
		artists = []
	album = None
	try:
		album = (t.get("album") or {}).get("name")
	except Exception:
		album = None
	duration = t.get("duration") if isinstance(t, dict) else None
	id_ = None
	try:
		id_ = t.get("videoId")
	except Exception:
		id_ = None
	return {
		"title": title,
		"artist": ", ".join([a for a in artists if a]),
		"album": album,
		"duration": duration,
		"liked_date": None,
		"youtube_id": id_,
		"url": f"https://music.youtube.com/watch?v={id_}" if id_ else None
	}


def register(server):
	@server.tool("ytm_liked_songs_free")
	def ytm_liked_songs_free(limit: int = 50):
		"""Fetch liked songs using ytmusicapi (free, cookie-based).

		Requires YTMUSIC_HEADERS_FILE or YTMUSIC_HEADERS_JSON to be set.
		"""
		ytm = _ytm()
		if ytm is None:
			return {"error": "Missing YTMusic auth headers.", "how_to": "Export headers via ytmusicapi.setup and set YTMUSIC_HEADERS_FILE or YTMUSIC_HEADERS_JSON."}
		try:
			data = ytm.get_liked_songs(limit=limit)
			tracks = (data or {}).get("tracks", [])
			return [_map_track(t) for t in tracks[:limit]]
		except Exception as e:
			return {"error": str(e)}

	@server.tool("ytm_liked_songs_all")
	def ytm_liked_songs_all():
		"""Fetch the full liked songs list (no truncation best-effort)."""
		ytm = _ytm()
		if ytm is None:
			return {"error": "Missing YTMusic auth headers.", "how_to": "Export headers via ytmusicapi.setup and set YTMUSIC_HEADERS_FILE or YTMUSIC_HEADERS_JSON."}
		try:
			# Use a very high limit to traverse continuations (ytmusicapi handles paging)
			data = ytm.get_liked_songs(limit=10000)
			tracks = (data or {}).get("tracks", [])
			return [_map_track(t) for t in tracks]
		except Exception as e:
			return {"error": str(e)}

	@server.tool("ytm_takeout_parse")
	def ytm_takeout_parse(file_path: str):
		"""Parse Google Takeout JSON for YouTube/YouTube Music likes into model-friendly schema."""
		try:
			with open(file_path, "r", encoding="utf-8") as f:
				blob = json.load(f)
		except Exception as e:
			return {"error": f"Failed to read {file_path}: {e}"}
		items = []
		def push(item):
			if not isinstance(item, dict):
				return
			title = item.get("title") or item.get("titleUrl") or item.get("mediaTitle")
			artists = []
			for f in (item.get("subtitles") or []):
				name = f.get("name")
				if name:
					artists.append(name)
			video_id = None
			url = item.get("titleUrl") or item.get("url")
			if url and "watch?v=" in url:
				try:
					video_id = url.split("watch?v=", 1)[1].split("&", 1)[0]
				except Exception:
					video_id = None
			items.append({
				"title": title,
				"artist": ", ".join(artists) if artists else None,
				"album": None,
				"duration": None,
				"liked_date": item.get("time") or item.get("creationTime"),
				"youtube_id": video_id,
				"url": url
			})
		if isinstance(blob, list):
			for it in blob:
				push(it)
		elif isinstance(blob, dict):
			for key in ("items", "likes", "myActivity", "records"):
				arr = blob.get(key)
				if isinstance(arr, list):
					for it in arr:
						push(it)
		return {"liked_songs": items}


# Public helpers for direct app usage

def list_liked_songs_free(limit: int = 50):
	ytm = _ytm()
	if ytm is None:
		return {"error": "Missing YTMusic auth headers.", "how_to": "Export headers via ytmusicapi.setup and set YTMUSIC_HEADERS_FILE or YTMUSIC_HEADERS_JSON."}
	try:
		data = ytm.get_liked_songs(limit=limit)
		tracks = (data or {}).get("tracks", [])
		return [_map_track(t) for t in tracks[:limit]]
	except Exception as e:
		return {"error": str(e)}


def list_liked_songs_all():
	ytm = _ytm()
	if ytm is None:
		return {"error": "Missing YTMusic auth headers.", "how_to": "Export headers via ytmusicapi.setup and set YTMUSIC_HEADERS_FILE or YTMUSIC_HEADERS_JSON."}
	try:
		data = ytm.get_liked_songs(limit=10000)
		tracks = (data or {}).get("tracks", [])
		return [_map_track(t) for t in tracks]
	except Exception as e:
		return {"error": str(e)}
