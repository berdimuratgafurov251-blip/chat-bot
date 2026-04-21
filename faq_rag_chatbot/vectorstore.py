import faiss
import numpy as np
import pickle
import os
from google import genai
import streamlit as st

# ---------------- GEMINI CLIENT ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- FILE PATHS ----------------
INDEX_FILE = "faiss_index.bin"
TEXT_FILE = "texts.pkl"

# ---------------- INIT ----------------
dimension = 1024  # 🔥 Gemini embedding size FIXED
index = faiss.IndexFlatL2(dimension)
texts = []

# ---------------- LOAD INDEX ----------------
def load_index():
    global index, texts

    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)

    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, "rb") as f:
            texts = pickle.load(f)

# ---------------- SAVE INDEX ----------------
def save_index():
    faiss.write_index(index, INDEX_FILE)

    with open(TEXT_FILE, "wb") as f:
        pickle.dump(texts, f)

# ---------------- EMBEDDING ----------------
def get_embedding(text: str):
    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=[text]
        )

        # Gemini embedding vector
        vec = np.array(response.embeddings[0].values, dtype=np.float32)

        # safety check
        if len(vec) != dimension:
            raise ValueError(f"Embedding size mismatch: {len(vec)} != {dimension}")

        return vec

    except Exception as e:
        print("❌ Embedding error:", e)
        raise e

# ---------------- ADD TO INDEX ----------------
def add_to_index(chunks):
    global texts

    for chunk in chunks:
        emb = get_embedding(chunk)

        # FAISS expects 2D array
        index.add(np.array([emb], dtype=np.float32))
        texts.append(chunk)

    save_index()

# ---------------- SEARCH ----------------
def search(query, k=3):
    if len(texts) == 0:
        return []

    q_emb = get_embedding(query)

    D, I = index.search(np.array([q_emb], dtype=np.float32), k)

    return [texts[i] for i in I[0] if 0 <= i < len(texts)]

# ---------------- INIT LOAD ----------------
load_index()
