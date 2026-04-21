import streamlit as st
from ingest import load_file
from vectorstore import search
from google import genai
import uuid

# ---------------- GEMINI ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="FAQ RAG Chatbot", layout="centered")

# ---------------- SESSION INIT ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if "history" not in st.session_state:
    st.session_state.history = {}

uid = st.session_state.user_id

if uid not in st.session_state.history:
    st.session_state.history[uid] = []

# ---------------- TEMP FILE ----------------
if "temp_file_name" not in st.session_state:
    st.session_state.temp_file_name = None

if "temp_file_context" not in st.session_state:
    st.session_state.temp_file_context = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ---------------- UI ----------------
st.title("🤖 Smart FAQ Chatbot (RAG)")

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Control Panel")

# LOGIN TOGGLE
label = "🔓 Logout" if st.session_state.is_logged_in else "🔐 Login"

if st.sidebar.button(label):
    st.session_state.is_logged_in = not st.session_state.is_logged_in
    st.rerun()

# CLEAR CHAT (only logged users)
if st.sidebar.button("🧹 Clear Chat"):
    if st.session_state.is_logged_in:
        st.session_state.history[uid] = []

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

# ---------------- CHAT HISTORY ----------------
if st.session_state.is_logged_in:
    chat_history = st.session_state.history[uid]
else:
    chat_history = []

for msg in chat_history:
    if msg["role"] == "user":
        st.markdown(f"<div style='background:#000;color:#fff;padding:8px;border-radius:10px;margin:5px'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background:#fff;color:#000;padding:8px;border-radius:10px;margin:5px;border:1px solid #ddd'>{msg['content']}</div>", unsafe_allow_html=True)

# ---------------- INPUT ----------------
query = st.chat_input("Savol yozing...")

if query:

    attached_file = st.session_state.temp_file_name
    attached_context = st.session_state.temp_file_context

    # reset file
    st.session_state.temp_file_name = None
    st.session_state.temp_file_context = None
    st.session_state.uploader_key += 1

    # RAG
    docs = search(query)
    rag_context = "\n\n".join(docs) if docs else ""

    prompt = f"""
You are a helpful assistant.

FILE CONTEXT:
{attached_context}

FAQ CONTEXT:
{rag_context}

Question:
{query}

Answer:
"""

    with st.spinner("Thinking..."):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt]
        )

    answer = response.text if response.text else "No response"

    # SAVE ONLY IF LOGGED IN
    if st.session_state.is_logged_in:
        st.session_state.history[uid].append({
            "role": "user",
            "content": query,
            "file": attached_file
        })

        st.session_state.history[uid].append({
            "role": "assistant",
            "content": answer
        })

    # SHOW ANSWER
    st.markdown(
        f"<div style='background:#eee;color:#000;padding:10px;border-radius:10px'>{answer}</div>",
        unsafe_allow_html=True
    )
