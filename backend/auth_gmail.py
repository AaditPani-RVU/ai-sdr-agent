"""
One-time Gmail OAuth setup. Run this once to create token.json.

Steps:
1. Go to console.cloud.google.com
2. Create a project → Enable "Gmail API"
3. OAuth consent screen → External → add your email as test user
4. Credentials → Create → OAuth 2.0 Client ID → Desktop app
5. Download the JSON → save as credentials.json in this directory
6. Run: python auth_gmail.py
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",   # needed to mark as read
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = os.getenv("GMAIL_TOKEN_PATH", "token.json")


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print("Download it from Google Cloud Console → Credentials → your OAuth 2.0 client.")
        return

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    print(f"Auth successful. Token saved to {TOKEN_FILE}")
    print("You can now start the backend and set DRY_RUN=false in .env")


if __name__ == "__main__":
    main()
