import json
import os

CHAT_FILE = "chat_history.json"

def save_chat(history):
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_chat():
    if not os.path.exists(CHAT_FILE):
        return []

    with open(CHAT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)