import streamlit as st
from google import genai
from ingest import load_file
from vectorstore import search
from supabase import create_client
import uuid

# ---------------- SUPABASE ----------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ---------------- GEMINI ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- PAGE ----------------
st.set_page_config(page_title="FAQ RAG Chatbot", layout="centered")

# ================= CSS =================
st.markdown("""
<style>
.user-msg {
    background-color: #000;
    color: #fff;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 2px 0;
    width: fit-content;
    max-width: 75%;
    margin-left: auto;
}

.bot-msg {
    background-color: #fff;
    color: #000;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 2px 0;
    width: fit-content;
    max-width: 75%;
    margin-right: auto;
    border: 1px solid #ddd;
}

.file-chip {
    display: block;
    background: #eee;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    margin-bottom: 4px;
    width: fit-content;
}
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

if "show_login" not in st.session_state:
    st.session_state.show_login = False

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())

if "guest_chat" not in st.session_state:
    st.session_state.guest_chat = []

if "temp_file_name" not in st.session_state:
    st.session_state.temp_file_name = None

if "temp_file_context" not in st.session_state:
    st.session_state.temp_file_context = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


# ================= LOGIN PAGE =================
def login_page():
    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        st.session_state.user = res.user
        st.session_state.show_login = False   # 🔥 FIX
        st.rerun()

    if st.button("Register"):
        supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        st.success("Check your email!")


# ================= SIDEBAR AUTH =================
st.sidebar.title("👤 Account")

if st.session_state.user:
    st.sidebar.success(st.session_state.user.email)

    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
else:
    if st.sidebar.button("🔐 Login / Register"):
        st.session_state.show_login = True

# 🔥 LOGIN PAGE CONTROL
if st.session_state.show_login:
    login_page()
    st.stop()

# USER MODE
is_logged_in = st.session_state.user is not None
uid = st.session_state.user.id if is_logged_in else "guest"

# ================= SIDEBAR CHAT =================
if is_logged_in:
    st.sidebar.title("💬 Chats")

    if st.sidebar.button("➕ New Chat"):
        st.session_state.chat_id = str(uuid.uuid4())
        st.rerun()

    def load_chat_list():
        res = supabase.table("chat_history") \
            .select("chat_id, content, created_at") \
            .eq("user_id", uid) \
            .order("created_at", desc=True) \
            .execute()

        chats = {}
        for row in res.data:
            cid = row["chat_id"]
            if cid not in chats:
                chats[cid] = row["content"][:30]

        return chats

    chat_list = load_chat_list()

    for cid, title in chat_list.items():
        if st.sidebar.button(title, key=cid):
            st.session_state.chat_id = cid
            st.rerun()

else:
    st.sidebar.info("Guest mode (history saqlanmaydi)")

# ================= FILE =================
uploaded_file = st.file_uploader(
    "📎 Attach file",
    type=["txt"],
    key=st.session_state.uploader_key
)

if uploaded_file:
    load_file(uploaded_file)
    docs = search(" ")

    st.session_state.temp_file_context = "\n\n".join(docs)
    st.session_state.temp_file_name = uploaded_file.name

    st.success("File ready")

# ================= LOAD HISTORY =================
def load_history():
    return supabase.table("chat_history") \
        .select("*") \
        .eq("user_id", uid) \
        .eq("chat_id", st.session_state.chat_id) \
        .order("created_at") \
        .execute().data

# ================= DISPLAY =================
if is_logged_in:
    history = load_history()

    for msg in history:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{msg['content']}</div>", unsafe_allow_html=True)
else:
    for msg in st.session_state.guest_chat:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{msg['content']}</div>", unsafe_allow_html=True)

# ================= SAVE =================
def save_message(role, content):
    supabase.table("chat_history").insert({
        "user_id": uid,
        "chat_id": st.session_state.chat_id,
        "role": role,
        "content": content
    }).execute()

# ================= CHAT =================
query = st.chat_input("Savol yozing...")

if query:

    file_name = st.session_state.temp_file_name
    file_context = st.session_state.temp_file_context

    # RESET FILE
    st.session_state.temp_file_name = None
    st.session_state.temp_file_context = None
    st.session_state.uploader_key += 1

    docs = search(query)
    rag_context = "\n\n".join(docs[:3]) if docs else ""

    prompt = f"""
You are a helpful assistant.

FILE CONTEXT:
{(file_context or "")[:1500]}

FAQ CONTEXT:
{rag_context}

Question:
{query}

Answer:
"""

    with st.spinner("Thinking..."):
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt]
        )

    answer = response.text if response.text else "No response"

    if is_logged_in:
        save_message("user", query)
        save_message("assistant", answer)
    else:
        st.session_state.guest_chat.append({"role": "user", "content": query})
        st.session_state.guest_chat.append({"role": "assistant", "content": answer})

    st.rerun()
