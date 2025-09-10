# AI Personal Hub

Unified personal assistant that connects Local Files, GitHub, YouTube, Gmail, Steam, and Summarization through Model Context Protocol (MCP), with a clean Flask UI and LM Studio integration.

<img width="1318" height="859" alt="image" src="https://github.com/user-attachments/assets/cd375f7f-0e8c-4121-b542-4d8ccec2f5f9" />
<img width="1663" height="852" alt="image" src="https://github.com/user-attachments/assets/c5256413-a17e-4e44-9cb6-33b51bb2d717" />


## Features

- Local notes: list and open `.txt` files from `notes/`
- GitHub: repos, commits, list files, fetch file content, issues
- YouTube: Liked Videos (LL), Liked Songs (LM) via OAuth
- Gmail: read last emails via OAuth
- Steam: recent owned games and playtime
- Summarizer: prompt exposed as an MCP tool
- Modern chat-style UI with quick actions and linkified results

## Architecture

- `Flask` serves the UI and a simple `/ask` endpoint
- `LM Studio` runs a local OpenAI-compatible server for LLM responses
- `MCP server` (`mcp_server/server.py`) exposes tools that LM Studio can call

```
Browser ↔ Flask UI ↔ LM Studio (LLM) ↔ MCP Tools (python -m mcp_server.server)
```

## Setup

1) Python env

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) LM Studio (recommended defaults)

- Start LM Studio local server (OpenAI-compatible) on `http://localhost:1234`
- Set environment variables (PowerShell):

```
setx LM_STUDIO_BASE_URL http://localhost:1234
setx LM_STUDIO_API_KEY lm-studio
setx LM_STUDIO_MODEL your-model-name
```

3) MCP server registration in LM Studio

Edit LM Studio `mcp.json` and add:

```json
{
  "mcpServers": {
    "personal-hub-server": {
      "command": "D:\\AI_MCP\\ai-personal-hub\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "D:\\AI_MCP\\ai-personal-hub"
    }
  }
}
```

Then start the server in LM Studio Tools (MCP), or run manually:

```
python -m mcp_server.server
```

4) Service credentials

- GitHub: set `GITHUB_TOKEN` (PAT, repo read scope recommended)
- Steam: set `STEAM_API_KEY` and `STEAM_ID`
- Notes: create `notes/` with `.txt` files

YouTube OAuth (`token.json`)

- In Google Cloud: enable "YouTube Data API v3"
- Create OAuth client (Desktop app) → download `client_secret.json` to project root
- Generate `token.json` (one-time):

```
python -c "from google_auth_oauthlib.flow import InstalledAppFlow; import json; flow=InstalledAppFlow.from_client_secrets_file('client_secret.json',['https://www.googleapis.com/auth/youtube.readonly']); creds=flow.run_local_server(port=0); open('token.json','w',encoding='utf-8').write(creds.to_json())"
```

Gmail OAuth (`token.json`)

- Similar flow; ensure scope `https://www.googleapis.com/auth/gmail.readonly`

## Run

Flask UI:

```
python app.py
```

Open `http://127.0.0.1:5000/`

MCP server (separate terminal):

```
python -m mcp_server.server
```

## Available MCP tools

- Files: `list_local_files`, `fetch_local_file`
- GitHub: `github_repos`, `github_commits`, `github_list_files`, `github_file_content`, `github_issues`, `github_issue`
- YouTube: `yt_liked_videos`, `ytm_liked_songs`, `yt_playlist`
- Gmail: `read_emails`
- Steam: `steam_games`
- Summarize: `summarize` prompt

## Example prompts

- “List my local notes.”
- “Open a.txt.”
- “List repos for Harsh-1807.”
- “List files in Harsh-1807/weather.”
- “Open README.md from Harsh-1807/weather.”
- “Show open issues for Harsh-1807/weather.”
- “List 5 of my liked YouTube videos.”
- “List 5 of my liked songs on YouTube Music.”
- “Summarize my last 5 emails.”
- “Which Steam games do I play most?”

## Troubleshooting

- LLM answers without calling tools: lower temperature; add a system prompt telling it to prefer MCP tools; ensure the tool server is running and registered in LM Studio.
- YouTube `LM` liked songs not returning results: some accounts do not expose LM over the API; try `yt_liked_videos` (LL) or `yt_playlist("LL")`.
- Permission errors: re-create `token.json` for the correct Google account; verify scopes.

## License

MIT
