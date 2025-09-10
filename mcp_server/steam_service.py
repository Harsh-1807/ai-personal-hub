import os
import requests


def _get(url: str, params: dict | None = None):
	try:
		return requests.get(url, params=params, timeout=20).json()
	except Exception as e:
		return {"error": str(e)}


def _env():
	"""Fetch Steam credentials from environment at call time."""
	return os.getenv("STEAM_API_KEY"), os.getenv("STEAM_ID")


def register(server):
	@server.tool("steam_games")
	def steam_games(limit: int = 10000):
		url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
		api_key, steam_id = _env()
		if not api_key or not steam_id:
			return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
		params = {
			"key": api_key,
			"steamid": steam_id,
			"format": "json",
			"include_appinfo": 1,
			"include_played_free_games": 1
		}
		res = _get(url, params)
		games = res.get("response", {}).get("games", [])
		items = []
		for g in games[:limit]:
			items.append({
				"appid": g.get("appid"),
				"name": g.get("name"),
				"playtime_forever_min": g.get("playtime_forever", 0),
				"playtime_2weeks_min": g.get("playtime_2weeks", 0),
				"img_icon_url": g.get("img_icon_url"),
				"img_logo_url": g.get("img_logo_url")
			})
		return items

	@server.tool("steam_all_games")
	def steam_all_games():
		"""Return the full list of owned games (no truncation)."""
		url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
		api_key, steam_id = _env()
		if not api_key or not steam_id:
			return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
		params = {
			"key": api_key,
			"steamid": steam_id,
			"format": "json",
			"include_appinfo": 1,
			"include_played_free_games": 1
		}
		res = _get(url, params)
		games = res.get("response", {}).get("games", [])
		return [{
			"appid": g.get("appid"),
			"name": g.get("name"),
			"playtime_forever_min": g.get("playtime_forever", 0),
			"playtime_2weeks_min": g.get("playtime_2weeks", 0),
			"img_icon_url": g.get("img_icon_url"),
			"img_logo_url": g.get("img_logo_url")
		} for g in games]

	@server.tool("steam_recent_games")
	def steam_recent_games(limit: int = 10):
		url = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
		api_key, steam_id = _env()
		if not api_key or not steam_id:
			return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
		params = {"key": api_key, "steamid": steam_id, "format": "json"}
		res = _get(url, params)
		games = res.get("response", {}).get("games", [])
		return [{
			"appid": g.get("appid"),
			"name": g.get("name"),
			"playtime_2weeks_min": g.get("playtime_2weeks", 0),
			"playtime_forever_min": g.get("playtime_forever", 0)
		} for g in games[:limit]]

	@server.tool("steam_app_details")
	def steam_app_details(appid: int):
		# Public store endpoint for basic app details
		url = "https://store.steampowered.com/api/appdetails"
		res = _get(url, {"appids": appid})
		data = res.get(str(appid), {}) if isinstance(res, dict) else {}
		if data.get("success"):
			info = data.get("data", {})
			return {
				"name": info.get("name"),
				"type": info.get("type"),
				"genres": [g.get("description") for g in info.get("genres", [])],
				"developers": info.get("developers"),
				"publishers": info.get("publishers"),
				"required_age": info.get("required_age"),
				"is_free": info.get("is_free"),
				"short_description": info.get("short_description"),
				"header_image": info.get("header_image")
			}
		return {"error": "Not found"}

	@server.tool("steam_player_achievements")
	def steam_player_achievements(appid: int, language: str = "en"):
		url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
		api_key, steam_id = _env()
		if not api_key or not steam_id:
			return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
		params = {"key": api_key, "steamid": steam_id, "appid": appid, "l": language}
		res = _get(url, params)
		game = res.get("playerstats", {})
		if not game or game.get("success") is False:
			return {"error": "No achievements or access denied for this app/user."}
		ach = game.get("achievements", [])
		return [{
			"apiname": a.get("apiname"),
			"achieved": a.get("achieved"),
			"unlocktime": a.get("unlocktime")
		} for a in ach]

	@server.tool("steam_game_stats")
	def steam_game_stats(appid: int):
		# Compose stats from owned games and app details
		owned = steam_games(limit=5000)
		match = next((g for g in owned if g.get("appid") == appid), None)
		details = steam_app_details(appid)
		return {"appid": appid, "owned_playtime": match, "details": details}

	@server.tool("steam_context_snapshot")
	def steam_context_snapshot(limit: int = 25):
		"""Return compact Steam context for the model: count and top games."""
		owned_full = list_owned_games(limit=5000)
		if isinstance(owned_full, dict) and owned_full.get("error"):
			return owned_full
		def safe_int(x):
			try:
				return int(x or 0)
			except Exception:
				return 0
		ordered = sorted(
			owned_full,
			key=lambda g: safe_int(g.get("playtime_forever_min")),
			reverse=True
		)
		top = []
		for g in ordered[:limit]:
			top.append({
				"appid": g.get("appid"),
				"name": g.get("name"),
				"minutes_lifetime": safe_int(g.get("playtime_forever_min")),
				"minutes_recent": safe_int(g.get("playtime_2weeks_min"))
			})
		total_minutes = sum(safe_int(g.get("playtime_forever_min")) for g in owned_full)
		count_info = get_owned_count()
		count_val = count_info.get("count") if isinstance(count_info, dict) else None
		return {
			"count": count_val,
			"total_playtime_min": total_minutes,
			"top_games": top
		}

	@server.tool("steam_app_user_details")
	def steam_app_user_details(appids: str, cookie: str | None = None):
		"""Fetch app user-context details from the Steam Store (requires logged-in session)."""
		headers = {}
		cookie_header = os.getenv("STEAM_STORE_COOKIE") if cookie is None else cookie
		if not cookie_header:
			return {"error": "Missing Steam Store cookie.", "how_to": "Provide cookie param or set STEAM_STORE_COOKIE env with your logged-in Steam cookies."}
		headers["Cookie"] = cookie_header
		url = "https://store.steampowered.com/api/appuserdetails"
		res = _get(url, {"appids": appids}) if not headers else requests.get(url, params={"appids": appids}, headers=headers, timeout=20).json()
		return res

	@server.tool("steam_owned_count")
	def steam_owned_count():
		url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
		api_key, steam_id = _env()
		if not api_key or not steam_id:
			return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
		params = {
			"key": api_key,
			"steamid": steam_id,
			"format": "json"
		}
		res = _get(url, params)
		return {"count": res.get("response", {}).get("game_count", 0)}

	@server.tool("steam_playtime_for")
	def steam_playtime_for(query: str):
		"""Find playtime for a game by fuzzy name match over owned games.

		Returns best_match plus candidates.
		"""
		if not query or not isinstance(query, str):
			return {"error": "Provide a non-empty query string"}
		owned = steam_all_games()
		if isinstance(owned, dict) and owned.get("error"):
			return owned
		ql = query.strip().lower()
		def score(name: str) -> int:
			n = (name or "").lower()
			if ql == n:
				return 100
			if ql in n:
				return 80
			# simple token overlap
			qset = set(ql.split())
			nset = set(n.split())
			return 50 + len(qset & nset)
		scored = sorted(owned, key=lambda g: score(g.get("name") or ""), reverse=True)
		best = scored[0] if scored else None
		def to_hours(mins: int) -> float:
			try:
				return round((mins or 0) / 60.0, 2)
			except Exception:
				return 0.0
		candidates = []
		for g in scored[:5]:
			m = int(g.get("playtime_forever_min") or 0)
			candidates.append({
				"appid": g.get("appid"),
				"name": g.get("name"),
				"minutes": m,
				"hours": to_hours(m)
			})
		if best:
			mins = int(best.get("playtime_forever_min") or 0)
			return {
				"query": query,
				"best_match": {
					"appid": best.get("appid"),
					"name": best.get("name"),
					"minutes": mins,
					"hours": to_hours(mins)
				},
				"candidates": candidates
			}
		return {"query": query, "error": "No owned games matched"}


# Public helpers for direct app usage

def list_owned_games(limit: int = 50):
	url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
	api_key, steam_id = _env()
	if not api_key or not steam_id:
		return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
	params = {
		"key": api_key,
		"steamid": steam_id,
		"format": "json",
		"include_appinfo": 1,
		"include_played_free_games": 1
	}
	res = _get(url, params)
	games = res.get("response", {}).get("games", [])
	items = []
	for g in games[:limit]:
		items.append({
			"appid": g.get("appid"),
			"name": g.get("name"),
			"playtime_forever_min": g.get("playtime_forever", 0),
			"playtime_2weeks_min": g.get("playtime_2weeks", 0)
		})
	return items


def app_user_details(appids: str, cookie: str | None = None):
	headers = {}
	cookie_header = cookie or os.getenv("STEAM_STORE_COOKIE")
	if not cookie_header:
		return {"error": "Missing Steam Store cookie.", "how_to": "Provide cookie param or set STEAM_STORE_COOKIE env with your logged-in Steam cookies."}
	headers["Cookie"] = cookie_header
	url = "https://store.steampowered.com/api/appuserdetails"
	try:
		return requests.get(url, params={"appids": appids}, headers=headers, timeout=20).json()
	except Exception as e:
		return {"error": str(e)}


def get_owned_count():
	"""Return dict with owned game count for direct app usage."""
	url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
	api_key, steam_id = _env()
	if not api_key or not steam_id:
		return {"error": "STEAM_API_KEY or STEAM_ID not set in process env."}
	params = {
		"key": api_key,
		"steamid": steam_id,
		"format": "json"
	}
	res = _get(url, params)
	resp = res.get("response", {}) if isinstance(res, dict) else {}
	if "game_count" not in resp:
		return {"error": "Steam API returned no game_count. Check profile privacy and account linkage.", "raw": resp}
	return {"count": resp.get("game_count", 0)}


def playtime_for_name(query: str):
	"""Return best-match playtime for a given game name using owned games (fuzzy).

	Returns {query, best_match: {name, appid, minutes, hours}, candidates: [...]} or error.
	"""
	if not query or not isinstance(query, str):
		return {"error": "Provide a non-empty query string"}
	owned = list_owned_games(limit=10000)
	if isinstance(owned, dict) and owned.get("error"):
		return owned
	ql = query.strip().lower()
	def score(name: str) -> int:
		n = (name or "").lower()
		if ql == n:
			return 100
		if ql in n:
			return 80
		qset = set(ql.split())
		nset = set(n.split())
		return 50 + len(qset & nset)
	scored = sorted(owned, key=lambda g: score(g.get("name") or ""), reverse=True)
	best = scored[0] if scored else None
	def to_hours(mins: int) -> float:
		try:
			return round((mins or 0) / 60.0, 2)
		except Exception:
			return 0.0
	candidates = []
	for g in scored[:5]:
		m = int(g.get("playtime_forever_min") or 0)
		candidates.append({
			"appid": g.get("appid"),
			"name": g.get("name"),
			"minutes": m,
			"hours": to_hours(m)
		})
	if best:
		mins = int(best.get("playtime_forever_min") or 0)
		return {
			"query": query,
			"best_match": {
				"appid": best.get("appid"),
				"name": best.get("name"),
				"minutes": mins,
				"hours": to_hours(mins)
			},
			"candidates": candidates
		}
	return {"query": query, "error": "No owned games matched"}