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
</style>
""", unsafe_allow_html=True)

# ================= SESSION INIT =================
defaults = {
    "user": None,
    "auth_page": None,
    "chat_id": str(uuid.uuid4()),
    "guest_chat": [],
    "temp_file_context": None,
    "temp_file_name": None,
    "uploader_key": 0
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================= AUTH PAGES =================
def login_page():
    st.title("🔐 Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if not email or not password:
                st.error("Fill all fields")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    st.session_state.user = res.user
                    st.session_state.auth_page = None
                    st.rerun()
                except:
                    st.error("Invalid credentials")

    if st.button("Go to Register"):
        st.session_state.auth_page = "register"
        st.rerun()


def register_page():
    st.title("📝 Register")

    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create")

        if submitted:
            if not email or not password or not confirm:
                st.error("Fill all fields")
            elif password != confirm:
                st.error("Passwords do not match")
            else:
                try:
                    supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    st.success("Account created")
                except:
                    st.error("Error")

    if st.button("Back to Login"):
        st.session_state.auth_page = "login"
        st.rerun()

# ================= MODE =================
is_logged_in = st.session_state.user is not None
uid = st.session_state.user.id if is_logged_in else "guest"

# ================= SIDEBAR (ALWAYS ACTIVE) =================
st.sidebar.title("⚙️ Control Panel")

# ---- CHAT ACTIONS ----
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

# ---- AUTH BUTTONS ----
st.sidebar.markdown("---")

if not is_logged_in:
    if st.sidebar.button("🔐 Login"):
        st.session_state.auth_page = "login"
        st.rerun()

    if st.sidebar.button("🆕 Register"):
        st.session_state.auth_page = "register"
        st.rerun()
else:
    st.sidebar.success(st.session_state.user.email)

    if st.sidebar.button("🚪 Logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# ================= AUTH ROUTER =================
if st.session_state.auth_page == "login":
    login_page()
    st.stop()

if st.session_state.auth_page == "register":
    register_page()
    st.stop()

# ================= CHAT LIST (USER ONLY) =================
st.sidebar.title("💬 Chats")

if is_logged_in:
    def load_chat_list():
        res = supabase.table("chat_history") \
            .select("chat_id, content, created_at") \
            .eq("user_id", uid) \
            .order("created_at", desc=True) \
            .execute()

        chats = {}
        for r in res.data:
            chats.setdefault(r["chat_id"], r["content"][:30])
        return chats

    for cid, title in load_chat_list().items():
        if st.sidebar.button(title, key=cid):
            st.session_state.chat_id = cid
            st.rerun()
else:
    st.sidebar.info("Guest mode (no history)")

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader(
    "📎 Upload file",
    type=["txt"],
    key=st.session_state.uploader_key
)

if uploaded_file:
    load_file(uploaded_file)
    docs = search(" ")
    st.session_state.temp_file_context = "\n\n".join(docs)
    st.session_state.temp_file_name = uploaded_file.name
    st.success("File loaded")

# ================= HISTORY =================
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
    for m in history:
        if m["role"] == "user":
            st.markdown(f"<div class='user-msg'>{m['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{m['content']}</div>", unsafe_allow_html=True)
else:
    for m in st.session_state.guest_chat:
        cls = "user-msg" if m["role"] == "user" else "bot-msg"
        st.markdown(f"<div class='{cls}'>{m['content']}</div>", unsafe_allow_html=True)

# ================= SAVE =================
def save(role, content):
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
    st.session_state.uploader_key += 1

    rag = search(query)
    rag_context = "\n\n".join(rag[:3]) if rag else ""

    prompt = f"""
FILE:
{(file_context or "")[:1500]}

FAQ:
{rag_context}

Q:
{query}

A:
"""

    with st.spinner("Thinking..."):
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt]
        )

    answer = response.text or "No response"

    if is_logged_in:
        save("user", query)
        save("assistant", answer)
    else:
        st.session_state.guest_chat.append({"role": "user", "content": query})
        st.session_state.guest_chat.append({"role": "assistant", "content": answer})

    st.rerun()
