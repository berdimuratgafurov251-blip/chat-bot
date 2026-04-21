import json
import os

CHAT_FILE = "chat_history.json"

# ---------------- LOAD ALL DATA ----------------
def load_all():
    if not os.path.exists(CHAT_FILE):
        return {}

    with open(CHAT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- SAVE ALL DATA ----------------
def save_all(data):
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------- GET USER CHAT ----------------
def load_user_chat(user_id):
    data = load_all()
    return data.get(user_id, [])

# ---------------- SAVE USER CHAT ----------------
def save_user_chat(user_id, chat):
    data = load_all()
    data[user_id] = chat
    save_all(data)
