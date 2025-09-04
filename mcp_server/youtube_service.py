from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def _yt_service():
	# Requires token.json with scope: https://www.googleapis.com/auth/youtube.readonly
	try:
		creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.readonly"])
		youtube = build("youtube", "v3", credentials=creds)
		return youtube
	except FileNotFoundError:
		return None
	except Exception:
		return None


def _fetch_playlist_items(youtube, playlist_id: str, limit: int = 5):
	items = []
	next_page = None
	while len(items) < limit:
		resp = youtube.playlistItems().list(
			part="snippet,contentDetails",
			playlistId=playlist_id,
			maxResults=min(50, limit - len(items)),
			pageToken=next_page
		).execute()
		for it in resp.get("items", []):
			vid = it.get("contentDetails", {}).get("videoId")
			sn = it.get("snippet", {})
			items.append({
				"title": sn.get("title"),
				"videoId": vid,
				"url": f"https://www.youtube.com/watch?v={vid}"
			})
		next_page = resp.get("nextPageToken")
		if not next_page:
			break
	return items[:limit]


def register(server):
	@server.tool("yt_liked_videos")
	def yt_liked_videos(limit: int = 5):
		# LL = Liked Videos
		yt = _yt_service()
		if yt is None:
			return {"error": "Missing or invalid token.json for YouTube OAuth.", "how_to": "Place token.json in project root with scope https://www.googleapis.com/auth/youtube.readonly."}
		return _fetch_playlist_items(yt, playlist_id="LL", limit=limit)

	@server.tool("ytm_liked_songs")
	def ytm_liked_songs(limit: int = 5):
		# LM = YouTube Music Liked Songs (may require proper account access)
		yt = _yt_service()
		if yt is None:
			return {"error": "Missing or invalid token.json for YouTube OAuth.", "how_to": "Place token.json in project root with scope https://www.googleapis.com/auth/youtube.readonly."}
		try:
			return _fetch_playlist_items(yt, playlist_id="LM", limit=limit)
		except Exception as e:
			return {"error": str(e), "hint": "Ensure token.json has youtube.readonly and the account has access to the LM playlist."}

	@server.tool("yt_playlist")
	def yt_playlist(playlist_id: str, limit: int = 5):
		yt = _yt_service()
		if yt is None:
			return {"error": "Missing or invalid token.json for YouTube OAuth.", "how_to": "Place token.json in project root with scope https://www.googleapis.com/auth/youtube.readonly."}
		return _fetch_playlist_items(yt, playlist_id=playlist_id, limit=limit)


# Public helpers for direct app usage
def list_liked_videos(limit: int = 5):
	yt = _yt_service()
	if yt is None:
		return {"error": "Missing or invalid token.json for YouTube OAuth.", "how_to": "Place token.json in project root with scope https://www.googleapis.com/auth/youtube.readonly."}
	return _fetch_playlist_items(yt, playlist_id="LL", limit=limit)


def list_liked_songs(limit: int = 5):
	yt = _yt_service()
	if yt is None:
		return {"error": "Missing or invalid token.json for YouTube OAuth.", "how_to": "Place token.json in project root with scope https://www.googleapis.com/auth/youtube.readonly."}
	try:
		return _fetch_playlist_items(yt, playlist_id="LM", limit=limit)
	except Exception as e:
		return {"error": str(e), "hint": "Ensure token.json has youtube.readonly and the account has access to the LM playlist."}