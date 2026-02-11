import os
import requests

print("Graph test gestart")

tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
mailbox_user = os.getenv("MAILBOX_USER")

# 1️⃣ OAuth token ophalen
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

token_data = {
    "client_id": client_id,
    "scope": "https://graph.microsoft.com/.default",
    "client_secret": client_secret,
    "grant_type": "client_credentials",
}

token_response = requests.post(token_url, data=token_data)
access_token = token_response.json().get("access_token")

if not access_token:
    print("Token fout:", token_response.json())
    exit()

print("Token ontvangen")

# Mailfolders ophalen
folders_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/mailFolders"
folders_response = requests.get(folders_url, headers=headers)

folders = folders_response.json().get("value", [])

print("\nBeschikbare mappen:")
for folder in folders:
    print("Naam:", folder.get("displayName"))
    print("ID:", folder.get("id"))
    print("-----")

# 2️⃣ Mails ophalen via Graph
headers = {
    "Authorization": f"Bearer {access_token}"
}

mail_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/messages?$top=5"

mail_response = requests.get(mail_url, headers=headers)

if mail_response.status_code != 200:
    print("Mail fout:", mail_response.text)
    exit()

emails = mail_response.json().get("value", [])

print(f"{len(emails)} mails gevonden")

for mail in emails:
    print("Onderwerp:", mail.get("subject"))

print("Graph test klaar")
