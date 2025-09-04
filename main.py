from dotenv import load_dotenv
import os

load_dotenv(override=True)  # force reload

print("DEBUG:", os.getenv("STEAM_API_KEY"), os.getenv("STEAM_ID"))
