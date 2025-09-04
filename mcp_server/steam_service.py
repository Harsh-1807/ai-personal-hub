import os
import requests


STEAM_API_KEY = os.getenv("STEAM_API_KEY", "your_key")
STEAM_ID = os.getenv("STEAM_ID", "your_steam_id")


def register(server):
	@server.tool("steam_games")
	def steam_games():
		url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={STEAM_ID}&format=json&include_appinfo=1"
		res = requests.get(url).json()
		games = res.get("response", {}).get("games", [])
		return [{"name": g.get("name"), "playtime": g.get("playtime_forever")} for g in games[:5]]