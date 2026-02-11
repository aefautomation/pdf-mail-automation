import os
import requests

print("Graph folder test gestart")

tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
mailbox_user = os.getenv("MAILBOX_USER")

# Token ophalen
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

# 👇 Headers MOET hier staan
headers = {
    "Authorization": f"Bearer {access_token}"
}

# Mailfolders ophalen
folders_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/mailFolders"
folders_response = requests.get(folders_url, headers=headers)

if folders_response.status_code != 200:
    print("Folder fout:", folders_response.text)
    exit()

folders = folders_response.json().get("value", [])

print("\nBeschikbare mappen:")
for folder in folders:
    print("Naam:", folder.get("displayName"))
    print("ID:", folder.get("id"))
    print("-----")

print("Folder test klaar")
