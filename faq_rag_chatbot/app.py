import streamlit as st
from ingest import load_file
from vectorstore import search
from google import genai
import os
from chat_store import save_chat, load_chat

# ---------------- GEMINI ----------------
import google.generativeai as genai
import streamlit as st

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="FAQ RAG Chatbot", layout="centered")
st.write("API TEST START")

try:
    response = client.models.generate_content(
        model="gemini-1.0-pro",
        contents=["hello"]
    )
    st.write(response.text)

except Exception as e:
    st.error(str(e))
# ================= CSS =================
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
    display: block; /* 🔥 MUHIM: yangi qatordan boshlaydi */
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

st.title("🤖 Smart FAQ Chatbot (RAG)")

# ================= SESSION STATE =================
if "history" not in st.session_state:
    st.session_state.history = load_chat()

if "chat" not in st.session_state:
    st.session_state.chat = []

if "current_chat" not in st.session_state:
    st.session_state.current_chat = []

if "temp_file_name" not in st.session_state:
    st.session_state.temp_file_name = None

if "temp_file_context" not in st.session_state:
    st.session_state.temp_file_context = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ================= SIDEBAR =================
st.sidebar.title("⚙️ Control Panel")

if st.sidebar.button("➕ New Chat"):
    if st.session_state.current_chat:
        st.session_state.history.append(st.session_state.current_chat)
        save_chat(st.session_state.history)

    st.session_state.chat = []
    st.session_state.current_chat = []
    st.rerun()

st.sidebar.subheader("📜 History")

for i, chat in enumerate(st.session_state.history):
    if st.sidebar.button(f"Chat {i+1}"):
        st.session_state.chat = chat
        st.session_state.current_chat = chat
        st.rerun()

if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.chat = []
    st.session_state.current_chat = []

# ================= FILE UPLOADER =================
uploaded_file = st.file_uploader(
    "📎 Attach file (only for next message)",
    type=["txt", "pdf", "png", "jpg", "jpeg"],
    key=st.session_state.uploader_key
)

if uploaded_file:
    with st.spinner("Processing file..."):
        count = load_file(uploaded_file)

        docs = search(" ")
        st.session_state.temp_file_context = "\n\n".join(docs) if docs else ""
        st.session_state.temp_file_name = uploaded_file.name

    st.success(f"{uploaded_file.name} ready for next message")

# ================= CHAT DISPLAY =================
for msg in st.session_state.chat:

    if msg["role"] == "user":
        if msg.get("file"):
            st.markdown(
                f"<div class='user-msg'><div class='file-chip'>📎 {msg['file']}</div>{msg['content']}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='user-msg'>{msg['content']}</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            f"<div class='bot-msg'>{msg['content']}</div>",
            unsafe_allow_html=True
        )

# ================= USER INPUT =================
query = st.chat_input("Savol yozing...")

if query:

    attached_file = st.session_state.temp_file_name
    attached_context = st.session_state.temp_file_context

    # SAVE USER MESSAGE
    st.session_state.chat.append({
        "role": "user",
        "content": query,
        "file": attached_file
    })

    st.session_state.current_chat.append({
        "role": "user",
        "content": query,
        "file": attached_file
    })

    # DISPLAY USER MESSAGE
    if attached_file:
        st.markdown(
            f"<div class='user-msg'><div class='file-chip'>📎 {attached_file}</div>{query}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='user-msg'>{query}</div>",
            unsafe_allow_html=True
        )

    # 🔥 RESET FILE (only one message)
    st.session_state.temp_file_name = None
    st.session_state.temp_file_context = None
    st.session_state.uploader_key += 1

    # ---------------- RAG ----------------
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
            model="gemini-1.0-pro",
            contents=["hello"]
        )

    answer = response.text if response.text else "No response"

    # SAVE BOT MESSAGE
    st.session_state.chat.append({
        "role": "assistant",
        "content": answer
    })

    st.session_state.current_chat.append({
        "role": "assistant",
        "content": answer
    })

    # DISPLAY BOT MESSAGE
    st.markdown(
        f"<div class='bot-msg'>{answer}</div>",
        unsafe_allow_html=True
    )

    save_chat(st.session_state.history)
