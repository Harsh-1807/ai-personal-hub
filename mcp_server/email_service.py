from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def register(server):
	@server.tool("read_emails")
	def read_emails():
		creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/gmail.readonly"])
		service = build("gmail", "v1", credentials=creds)
		results = service.users().messages().list(userId="me", maxResults=5).execute()
		messages = results.get("messages", [])
		emails = []
		for msg in messages:
			m = service.users().messages().get(userId="me", id=msg["id"]).execute()
			snippet = m.get("snippet", "")
			emails.append({"id": msg["id"], "snippet": snippet})
		return emails