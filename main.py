import os
import imaplib
import email
from openai import OpenAI

print("Script gestart")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")

print("Environment geladen")

client = OpenAI(api_key=OPENAI_API_KEY)

# Test OpenAI connectie
try:
    response = client.responses.create(
        model="gpt-4.1",
        input="Test connectie"
    )
    print("OpenAI werkt")
except Exception as e:
    print("OpenAI fout:", e)

# Test mail connectie
try:
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(IMAP_USER, IMAP_PASS)
    print("Mail connectie werkt")
    mail.logout()
except Exception as e:
    print("Mail fout:", e)

print("Einde test")
