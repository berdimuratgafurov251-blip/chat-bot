import streamlit as st
from google import genai
from ingest import load_file
from vectorstore import search
from supabase import create_client
import uuid
import tempfile

# ---------------- SUPABASE ----------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ---------------- GEMINI ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- PAGE ----------------
st.set_page_config(
    page_title="Smart FAQ Chatbot RAG",
    layout="centered"
)

st.title("🤖 Smart FAQ Chatbot RAG")

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

# ================= SESSION =================
defaults = {
    "user": None,
    "auth_page": None,
    "chat_id": str(uuid.uuid4()),
    "guest_chat": [],
    "temp_file_context": None,
    "uploader_key": 0
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================= AUTH =================
def login_page():
    st.title("🔐 Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            try:
                res = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                # 🔥 DEBUG (MUHIM)
                st.write(res)

                if hasattr(res, "session") and res.session:
                    st.session_state.user = res.user
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Login failed: no session returned")

            except Exception as e:
                st.error(f"Login error: {e}")
    st.write("SESSION:", getattr(res, "session", None))
    st.write("USER:", getattr(res, "user", None))
    if st.button("Go Register"):
        st.session_state.auth_page = "register"
        st.rerun()

def register_page():
    st.title("📝 Register")

    with st.form("reg"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm", type="password")
        submitted = st.form_submit_button("Create")

        if submitted:
            if password != confirm:
                st.error("Passwords mismatch")
            else:
                try:
                    res = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })

                    st.success("Registered! Now login.")
                    st.session_state.auth_page = "login"
                    st.rerun()

                except Exception as e:
                    st.error(f"Register error: {e}")

    if st.button("Back"):
        st.session_state.auth_page = "login"
        st.rerun()

    if st.button("Back"):
        st.session_state.auth_page = "login"
        st.rerun()

    if st.button("Back"):
        st.session_state.auth_page = "login"
        st.rerun()

# ================= MODE =================
is_logged_in = st.session_state.user is not None
uid = st.session_state.user.id if is_logged_in else "guest"

# ================= SIDEBAR =================
st.sidebar.title("👤 Account")

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

# ---------------- CONTROL PANEL ----------------
st.sidebar.markdown("---")
st.sidebar.title("⚙️ Control Panel")

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

# ---------------- CHATS ----------------
st.sidebar.markdown("---")
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
    st.sidebar.info("Guest mode")

# ================= FILE UPLOAD =================
def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name

uploaded_file = st.file_uploader(
    "📎 Upload file",
    type=["txt"],
    key=st.session_state.uploader_key
)

if uploaded_file:
    text = uploaded_file.read().decode("utf-8", errors="ignore")

    from ingest import load_file
    count = load_file(text)

    st.session_state.temp_file_context = text


    st.success("Uploaded")

    

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
        cls = "user-msg" if m["role"] == "user" else "bot-msg"
        st.markdown(f"<div class='{cls}'>{m['content']}</div>", unsafe_allow_html=True)
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

# ================= 🔥 FIXED RAG =================
query = st.chat_input("Savol yozing...")

if query:

    file_context = st.session_state.get("temp_file_context", "")

    docs = search(query)
    rag_context = "\n\n".join(docs[:3]) if docs else ""

    prompt = f"""
You are a helpful AI assistant.

INSTRUCTIONS:
- Use FILE and FAQ context if they are relevant
- If context is empty or not useful, answer using your general knowledge
- Do NOT say "I don't know" for greetings or simple questions
- Be natural and helpful

FILE:
{(file_context or "")[:1500]}

FAQ CONTEXT:
{rag_context}

QUESTION:
{query}

ANSWER:
"""

    with st.spinner("Thinking..."):
        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=[prompt[:6000]]
        )

    answer = response.text or "No response"

    if is_logged_in:
        save("user", query)
        save("assistant", answer)
    else:
        st.session_state.guest_chat.append({"role": "user", "content": query})
        st.session_state.guest_chat.append({"role": "assistant", "content": answer})

    st.rerun()
