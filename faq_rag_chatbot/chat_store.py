import json
import os

CHAT_FILE = "chat_history.json"


# ---------------- LOAD ALL DATA ----------------
def load_all():
    if not os.path.exists(CHAT_FILE):
        return {}

    try:
        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # agar file buzilgan bo‘lsa
        return {}


# ---------------- SAVE ALL DATA ----------------
def save_all(data):
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------- GET USER CHAT ----------------
def load_user_chat(user_id: str):
    data = load_all()
    return data.get(user_id, [])


# ---------------- SAVE USER CHAT ----------------
def save_user_chat(user_id: str, chat_list: list):
    data = load_all()

    # safety: agar chat_list None bo‘lsa
    if chat_list is None:
        chat_list = []

    data[user_id] = chat_list
    save_all(data)


# ---------------- CLEAR USER CHAT ----------------
def clear_user_chat(user_id: str):
    data = load_all()

    if user_id in data:
        data[user_id] = []

    save_all(data)
