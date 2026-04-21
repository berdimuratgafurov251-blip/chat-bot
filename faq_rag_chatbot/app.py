import streamlit as st
from google import genai
from ingest import load_file
from vectorstore import search
from supabase import create_client

# ---------------- SUPABASE ----------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ---------------- GEMINI ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- PAGE ----------------
st.set_page_config(page_title="FAQ RAG Chatbot", layout="centered")

# ---------------- AUTH SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None


# ================= LOGIN PAGE =================
def login_page():
    st.title("🔐 Login")

    tab1, tab2 = st.tabs(["Email", "Google"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                st.session_state.user = res.user
                st.rerun()

            except Exception as e:
                st.error(e)

    with tab2:
        if st.button("Login with Google"):
            supabase.auth.sign_in_with_oauth({
                "provider": "google"
            })
            st.stop()


# ---------------- CHECK AUTH ----------------
if st.session_state.user is None:
    login_page()
    st.stop()

user = st.session_state.user
uid = user.id

st.title("🤖 Smart FAQ Chatbot (RAG)")

# ---------------- FILE STATE ----------------
if "temp_file_name" not in st.session_state:
    st.session_state.temp_file_name = None

if "temp_file_context" not in st.session_state:
    st.session_state.temp_file_context = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


# ================= DB FUNCTIONS =================
def save_message(uid, role, content):
    supabase.table("chat_history").insert({
        "user_id": uid,
        "role": role,
        "content": content
    }).execute()


def load_history(uid):
    res = supabase.table("chat_history") \
        .select("*") \
        .eq("user_id", uid) \
        .order("id") \
        .execute()
    return res.data


# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Control Panel")

st.sidebar.success(f"Logged in: {user.email}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

if st.sidebar.button("🧹 Clear Chat"):
    supabase.table("chat_history").delete().eq("user_id", uid).execute()


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


# ---------------- LOAD CHAT ----------------
chat_history = load_history(uid)

for msg in chat_history:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='background:#000;color:#fff;padding:8px;border-radius:10px;margin:5px'>{msg['content']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='background:#fff;color:#000;padding:8px;border-radius:10px;margin:5px;border:1px solid #ddd'>{msg['content']}</div>",
            unsafe_allow_html=True
        )


# ---------------- INPUT ----------------
query = st.chat_input("Savol yozing...")

if query:

    attached_file = st.session_state.temp_file_name
    attached_context = st.session_state.temp_file_context

    # reset file
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
            model="gemini-2.5-flash",
            contents=[prompt]
        )

    answer = response.text if response.text else "No response"

    # ---------------- SAVE TO SUPABASE ----------------
    save_message(uid, "user", query)
    save_message(uid, "assistant", answer)

    # ---------------- SHOW ----------------
    st.markdown(
        f"<div style='background:#eee;color:#000;padding:10px;border-radius:10px'>{answer}</div>",
        unsafe_allow_html=True
    )
