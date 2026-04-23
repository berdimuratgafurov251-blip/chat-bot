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

.stButton>button {
    background-color: #222;
    color: white;
    border-radius: 8px;
}

.stButton>button:hover {
    background-color: #444;
}
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None

if "auth_page" not in st.session_state:
    st.session_state.auth_page = None  # login / register

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

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login")

    # 🔥 FORM
    with st.form("login_form"):

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button("Login")

        if submitted:

            if not email and not password:
                st.error("Please fill out all fields")
            elif not email:
                st.error("Email is required")
            elif not password:
                st.error("Password is required")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    st.session_state.user = res.user
                    st.session_state.auth_page = None
                    st.rerun()

                except Exception:
                    st.error("Invalid email or password")

    # 🔥 FORM DAN TASHQARIDA (MUHIM)
    st.markdown("---")

    if st.button("Go to Register"):
        st.session_state.auth_page = "register"
        st.rerun()
# ================= REGISTER =================
def register_page():
    st.title("🆕 Register")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        st.success("Check your email!")

    if st.button("Back to Login"):
        st.session_state.auth_page = "login"
        st.rerun()

# ================= SIDEBAR AUTH =================
st.sidebar.title("👤 Account")

if st.session_state.user:
    st.sidebar.success(st.session_state.user.email)

    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
else:
    if st.sidebar.button("🔐 Login"):
        st.session_state.auth_page = "login"

    if st.sidebar.button("🆕 Register"):
        st.session_state.auth_page = "register"

# AUTH PAGE CONTROL
if st.session_state.auth_page == "login":
    login_page()
    st.stop()

if st.session_state.auth_page == "register":
    register_page()
    st.stop()

# ================= MODE =================
is_logged_in = st.session_state.user is not None
uid = st.session_state.user.id if is_logged_in else "guest"

# ================= SIDEBAR CHAT =================
st.sidebar.title("💬 Chats")

if st.sidebar.button("➕ New Chat"):
    st.session_state.chat_id = str(uuid.uuid4())

    if not is_logged_in:
        st.session_state.guest_chat = []

    st.rerun()

if st.sidebar.button("🧹 Clear Chat"):
    if is_logged_in:
        supabase.table("chat_history") \
            .delete() \
            .eq("user_id", uid) \
            .eq("chat_id", st.session_state.chat_id) \
            .execute()
    else:
        st.session_state.guest_chat = []

    st.rerun()

# ================= LOAD CHAT LIST =================
if is_logged_in:
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
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            st.markdown(f"<div class='user-msg'>{content}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{content}</div>", unsafe_allow_html=True)
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

    file_context = st.session_state.temp_file_context

    st.session_state.temp_file_context = None
    st.session_state.temp_file_name = None
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
            model="models/gemini-2.5-flash",  # 🔥 UPDATED MODEL
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
