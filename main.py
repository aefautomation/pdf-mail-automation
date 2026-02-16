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

# Jouw specifieke map ID
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

mail_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/mailFolders/{FOLDER_ID}/messages?$filter=not(categories/any(c:c eq 'Processed'))&$top=10"

mail_response = requests.get(mail_url, headers=headers)

if mail_response.status_code != 200:
    print("❌ Mail fout:", mail_response.text)
    exit()

emails = mail_response.json().get("value", [])

print(f"📬 {len(emails)} mails gevonden in gekozen map")

# =============================
# 3️⃣ OPENAI CLIENT
# =============================

client = OpenAI(api_key=openai_api_key)

PROMPT = """
Je krijgt een warehouse document met titel "Uitslagbon".
Het document kan uit meerdere pagina's bestaan.
Gebruik ALLE pagina's.

Doel:
Extraheer per artikel exact vier velden uit de hoofdtabel.

Gebruik uitsluitend deze velden:

1. Uw referentie
   - Staat onderaan bij sectie "Algemeen"
   - Label: "Uw referentie"
   - Deze waarde is gelijk voor alle artikelen in het document

2. Klant artnr.
   - Kolomkop: "Klant artnr."

3. CU partijnr.
   - Kolomkop: "CU partijnr."

4. Aantal eenheden
   - Kolomkop: "Aantal eenheden"
   - Dit is een geheel getal
   - Gebruik NIET netto gewicht
   - Gebruik NIET bruto gewicht
   - Gebruik NIET aantal pallets

Negeer volledig:
- De rij "Totaal"
- Sectie "Diensten / Emballage"
- Netto gewicht
- Bruto gewicht
- Opslag
- Aantal pallets
- Eventuele andere tabellen

BELANGRIJK:
- 1 object per artikelregel
- Geen dubbele regels
- Geen extra velden
- Geen uitleg
- Geen tekst buiten JSON
- Alleen geldige JSON

Geef output uitsluitend in dit exacte formaat:

Uw referentie|Klant artnr.|CU partijnr.|Aantal eenheden

Voorbeeld:
80567092|DV0518-1|2601200035|22
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
                    # Upload naar OpenAI
                    file = client.files.create(
                        file=(filename, pdf_bytes, "application/pdf"),
                        purpose="user_data"
                    )
                
                    response = client.responses.create(
                        model="gpt-4.1",
                        temperature=0,
                        input=[{
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": PROMPT},
                                {"type": "input_file", "file_id": file.id}
                            ]
                        }]
                    )
                
                    print("🧠 Extractie resultaat (raw):")
                    print(response.output_text)
                
                    # =============================
                    # PARSE AI OUTPUT
                    # =============================
                
                    print("\n🔍 Parsing regels...")
                
                    lines = response.output_text.strip().split("\n")
                    parsed_rows = []
                
                    for line in lines:
                        line = line.strip()
                
                        if not line:
                            continue
                
                        parts = line.split("|")
                
                        if len(parts) != 4:
                            print("❌ Ongeldige regel (verkeerd aantal kolommen):", line)
                            continue
                
                        uwref = parts[0].strip()
                        klantart = parts[1].strip()
                        cupart = parts[2].strip()
                
                        try:
                            aantal = int(parts[3].strip())
                        except:
                            print("❌ Aantal geen integer:", line)
                            continue
                
                        row = {
                            "uwref": uwref,
                            "klantart": klantart,
                            "cupart": cupart,
                            "aantal": aantal
                        }
                
                        parsed_rows.append(row)
                        print("✅ Geparsed:", row)
                
                    print(f"\n📊 Totaal geldige regels: {len(parsed_rows)}")
                
                    # =============================
                    # CATEGORIE TOEVOEGEN
                    # =============================
                
                    if len(parsed_rows) > 0:
                        mark_url = f"https://graph.microsoft.com/v1.0/users/{mailbox_user}/messages/{message_id}"
                
                        patch_response = requests.patch(
                            mark_url,
                            headers={**headers, "Content-Type": "application/json"},
                            json={"categories": ["Processed"]}
                        )
                
                        if patch_response.status_code == 200:
                            print("✅ Mail gemarkeerd als Processed")
                        else:
                            print("❌ Categorie fout:", patch_response.status_code, patch_response.text)
                
                    else:
                        print("⚠ Geen geldige regels — mail niet gemarkeerd")
                
                except Exception as e:
                    print("❌ OpenAI fout:", e)

print("\n=== Script klaar ===")
