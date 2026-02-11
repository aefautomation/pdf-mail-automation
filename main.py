import os
import requests
import base64
from openai import OpenAI

print("=== PDF Mail Processor gestart ===")

# =============================
# ENVIRONMENT VARS
# =============================

tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
mailbox_user = os.getenv("MAILBOX_USER")
openai_api_key = os.getenv("OPENAI_API_KEY")

FOLDER_ID = "AAMkADhhNzQzNzRkLWY5ZTItNDIyYy1iOTQ0LWEzNmYzMTRiZjE3NwAuAAAAAABLhGXob5x2QpwA-4ma2Ql8AQD2LEUvAE7rSrY1l1xqTe-AAADioOdwAAA="

# =============================
# 1️⃣ OAUTH TOKEN OPHALEN
# =============================

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
    print("❌ Token fout:", token_response.json())
    exit()

print("✅ Token ontvangen")

headers = {
    "Authorization": f"Bearer {access_token}"
}

# =============================
# 2️⃣ MAILS UIT SPECIFIEKE MAP
# =============================

mail_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/mailFolders/{FOLDER_ID}/messages?$filter=isRead eq false&$top=20"

mail_response = requests.get(mail_url, headers=headers)

if mail_response.status_code != 200:
    print("❌ Mail fout:", mail_response.text)
    exit()

emails = mail_response.json().get("value", [])

print(f"📬 {len(emails)} ongelezen mails gevonden in gekozen map")

# =============================
# 3️⃣ OPENAI CLIENT
# =============================

client = OpenAI(api_key=openai_api_key)

PROMPT = """
Je krijgt een warehouse document met titel "Uitslagbon".
Het document kan uit meerdere pagina's bestaan.
Gebruik ALLE pagina's.

Extraheer per artikel exact:
- Uw referentie
- Klant artnr.
- CU partijnr.
- Aantal eenheden

Negeer:
- Totaal regels
- Netto gewicht
- Bruto gewicht
- Aantal pallets
- Diensten / Emballage

Geef uitsluitend geldige JSON terug.
"""

# =============================
# 4️⃣ MAILS VERWERKEN
# =============================

for mail in emails:
    subject = mail.get("subject")
    message_id = mail.get("id")

    print(f"\n📧 Mail: {subject}")

    attachments_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/messages/{message_id}/attachments"
    attachments_response = requests.get(attachments_url, headers=headers)

    if attachments_response.status_code != 200:
        print("❌ Bijlage fout:", attachments_response.text)
        continue

    attachments = attachments_response.json().get("value", [])

    for att in attachments:
        if att.get("@odata.type") == "#microsoft.graph.fileAttachment":

            filename = att.get("name", "").lower()

            if filename.startswith("warehouse - shipment -americold-") and filename.endswith(".pdf"):

                print(f"📄 Geldige PDF gevonden: {filename}")

                file_content_base64 = att.get("contentBytes")
                pdf_bytes = base64.b64decode(file_content_base64)

                try:
                    # Upload PDF
                    file = client.files.create(
                        file=(filename, pdf_bytes, "application/pdf"),
                        purpose="user_data"
                    )

                    # Schema enforced JSON
                    response = client.responses.create(
                        model="gpt-4.1",
                        temperature=0,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "shipment_rows",
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "rows": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "uwref": {"type": ["string", "null"]},
                                                    "klantart": {"type": ["string", "null"]},
                                                    "cupart": {"type": ["string", "null"]},
                                                    "aantal": {"type": ["integer", "null"]}
                                                },
                                                "required": ["uwref", "klantart", "cupart", "aantal"],
                                                "additionalProperties": False
                                            }
                                        }
                                    },
                                    "required": ["rows"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        input=[{
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": PROMPT},
                                {"type": "input_file", "file_id": file.id}
                            ]
                        }]
                    )

                    # JSON veilig uitlezen
                    try:
                        data = response.output[0].content[0].json
                        rows = data.get("rows", [])
                    except Exception as parse_error:
                        print("❌ JSON parse fout:", parse_error)
                        continue

                    print(f"🧠 {len(rows)} regels gevonden")

                    for row in rows:
                        print("➡", row)

                    # Mail markeren als gelezen
                    mark_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/messages/{message_id}"
                    requests.patch(
                        mark_url,
                        headers={**headers, "Content-Type": "application/json"},
                        json={"isRead": True}
                    )

                    print("✅ Mail gemarkeerd als gelezen")

                except Exception as e:
                    print("❌ OpenAI fout:", e)

print("\n=== Script klaar ===")
