import streamlit as st
from ingest import load_file
from vectorstore import search
from google import genai
import uuid

# ---------------- GEMINI ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="FAQ RAG Chatbot", layout="centered")

# ---------------- USER ID (MULTI-USER FIX) ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

uid = st.session_state.user_id

# ---------------- SESSION STATE ----------------
if "history" not in st.session_state:
    st.session_state.history = {}

if uid not in st.session_state.history:
    st.session_state.history[uid] = []

if "temp_file_name" not in st.session_state:
    st.session_state.temp_file_name = None

if "temp_file_context" not in st.session_state:
    st.session_state.temp_file_context = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ---------------- CSS ----------------
st.markdown("""
<style>
.user-msg {
    background-color: #000;
    color: #fff;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 5px 0;
    max-width: 75%;
    margin-left: auto;
}

.bot-msg {
    background-color: #fff;
    color: #000;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 5px 0;
    max-width: 75%;
    margin-right: auto;
    border: 1px solid #ddd;
}

.file-chip {
    background-color: #e6e6e6;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    margin-bottom: 4px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 Smart FAQ Chatbot (RAG)")

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Control Panel")

if st.sidebar.button("🧹 Clear Chat"):
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

# ---------------- CHAT DISPLAY ----------------
for msg in st.session_state.history[uid]:

    if msg["role"] == "user":
        st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='bot-msg'>{msg['content']}</div>", unsafe_allow_html=True)

# ---------------- INPUT ----------------
query = st.chat_input("Savol yozing...")

if query:

    attached_file = st.session_state.temp_file_name
    attached_context = st.session_state.temp_file_context

    # RESET FILE AFTER USE
    st.session_state.temp_file_name = None
    st.session_state.temp_file_context = None
    st.session_state.uploader_key += 1

    # SAVE USER MESSAGE
    st.session_state.history[uid].append({
        "role": "user",
        "content": query,
        "file": attached_file
    })

    # RAG SEARCH
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

    # SAVE BOT MESSAGE
    st.session_state.history[uid].append({
        "role": "assistant",
        "content": answer
    })

    # SHOW ANSWER
    st.markdown(f"<div class='bot-msg'>{answer}</div>", unsafe_allow_html=True)
