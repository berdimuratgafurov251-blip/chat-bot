import streamlit as st
from google import genai
from ingest import load_file
from vectorstore import search
from supabase import create_client
import uuid


def load_chat_list():
    res = supabase.table("chat_history") \
        .select("chat_id, content, created_at") \
        .eq("user_id", uid) \
        .order("created_at", desc=True) \
        .execute()

    data = res.data

    chats = {}
    for row in data:
        cid = row["chat_id"]
        if cid and cid not in chats:
            chats[cid] = row["content"][:30]  # title

    return chats
# ---------------- SUPABASE ----------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ---------------- GEMINI ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="FAQ RAG Chatbot", layout="centered")

# ================= CSS (UNCHANGED) =================
st.markdown("""
<style>
.user-msg {
    background-color: #000000;
    color: #ffffff;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 2px 0;
    width: fit-content;
    max-width: 75%;
    margin-left: auto;
    text-align: right;
    line-height: 1.3;
}

.bot-msg {
    background-color: #ffffff;
    color: #000000;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 2px 0;
    width: fit-content;
    max-width: 75%;
    margin-right: auto;
    border: 1px solid #e0e0e0;
    line-height: 1.3;
}

.file-chip {
    display: block;
    background-color: #e6e6e6;
    color: #333;
    padding: 2px 8px;
    border-radius: 16px;
    font-size: 11px;
    margin-bottom: 4px;
    width: fit-content;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "user" not in st.session_state:
    st.session_state.user = None

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())

if "temp_file_name" not in st.session_state:
    st.session_state.temp_file_name = None

if "temp_file_context" not in st.session_state:
    st.session_state.temp_file_context = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login")

    tab1, tab2 = st.tabs(["Email", "Google"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            st.session_state.user = res.user
            st.rerun()

        if st.button("Register"):
            supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            st.success("Check email!")

    with tab2:
        if st.button("Login with Google"):
            supabase.auth.sign_in_with_oauth({"provider": "google"})
# ---------------- LOGOUT ----------------
if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# ---------------- AUTH CHECK ----------------
if st.session_state.user is None:
    login_page()
    st.stop()

user = st.session_state.user
uid = user.id

st.title("🤖 Smart FAQ Chatbot (RAG)")

st.sidebar.success(f"Logged in: {user.email}")
st.stop()

# ---------------- NEW CHAT ----------------
st.sidebar.title("💬 Chats")

# NEW CHAT BUTTON
if st.sidebar.button("➕ New Chat"):
    import uuid
    st.session_state.chat_id = str(uuid.uuid4())
    st.rerun()

# CHAT LIST
chat_list = load_chat_list()

for cid, title in chat_list.items():
    if st.sidebar.button(title):
        st.session_state.chat_id = cid
        st.rerun()


# ---------------- CLEAR CHAT ----------------
if st.sidebar.button("🧹 Clear Chat"):
    supabase.table("chat_history") \
        .delete() \
        .eq("user_id", uid) \
        .eq("chat_id", st.session_state.chat_id) \
        .execute()

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader(
    "📎 Upload file",
    type=["txt"],
    key=st.session_state.uploader_key
)

if uploaded_file:
    with st.spinner("Processing file..."):
        load_file(uploaded_file)
        docs = search(" ")

        st.session_state.temp_file_context = "\n\n".join(docs) if docs else ""
        st.session_state.temp_file_name = uploaded_file.name

    st.success("File uploaded")

# ---------------- HISTORY ----------------
def load_history():
    return supabase.table("chat_history") \
        .select("*") \
        .eq("user_id", uid) \
        .eq("chat_id", st.session_state.chat_id) \
        .order("created_at") \
        .execute().data

chat_history = load_history()

for msg in chat_history:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='user-msg'>{msg['content']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='bot-msg'>{msg['content']}</div>",
            unsafe_allow_html=True
        )

# ---------------- SAVE MESSAGE ----------------
def save_message(role, content):
    supabase.table("chat_history").insert({
        "user_id": uid,
        "chat_id": st.session_state.chat_id,
        "role": role,
        "content": content
    }).execute()

# ---------------- LIMIT (FIFO 10) ----------------
def enforce_limit():
    data = supabase.table("chat_history") \
        .select("id") \
        .eq("user_id", uid) \
        .eq("chat_id", st.session_state.chat_id) \
        .order("id") \
        .execute().data

    if len(data) > 10:
        oldest = data[0]["id"]

        supabase.table("chat_history") \
            .delete() \
            .eq("id", oldest) \
            .execute()

# ---------------- CHAT ----------------
query = st.chat_input("Savol yozing...")

if query:

    attached_file = st.session_state.temp_file_name
    attached_context = st.session_state.temp_file_context

    st.session_state.temp_file_name = None
    st.session_state.temp_file_context = None
    st.session_state.uploader_key += 1

    docs = search(query)
    rag_context = "\n\n".join(docs[:3]) if docs else ""

    prompt = f"""
You are a helpful assistant.

FILE CONTEXT:
{(attached_context or "")[:1500]}

FAQ CONTEXT:
{rag_context}

Question:
{query}

Answer:
"""

    with st.spinner("Thinking..."):
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=[prompt]
        )

    answer = response.text if response.text else "No response"

    save_message("user", query)
    save_message("assistant", answer)

    enforce_limit()

    st.markdown(
        f"<div class='bot-msg'>{answer}</div>",
        unsafe_allow_html=True
    )
