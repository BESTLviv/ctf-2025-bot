from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_ID = [int(id) for id in os.getenv("ADMIN_ID").split(",") if id.strip()]
ADMIN_ENTRY_PHRASE = os.getenv("ADMIN_ENTRY_PHRASE")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
PARTICIPANTS_CHAT_LINK = os.getenv("PARTICIPANTS_CHAT_LINK")
ORGANIZER_CONTACT = os.getenv("ORGANIZER_CONTACT")
ASSETS_PATH = os.getenv("ASSETS_PATH", "assets")

print("BOT_TOKEN in config:", BOT_TOKEN)
print("MONGODB_URI in config:", MONGODB_URI)
