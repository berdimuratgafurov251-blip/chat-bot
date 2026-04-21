import faiss
import numpy as np
import pickle
import os
from google import genai
import numpy as np
import streamlit as st

# ---------------- GEMINI CLIENT ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
http_options={"api_version": "v1"}

# ---------------- FILE PATHS ----------------
INDEX_FILE = "faiss_index.bin"
TEXT_FILE = "texts.pkl"

# ---------------- INIT ----------------
dimension = 768  # Gemini embedding size
index = faiss.IndexFlatL2(dimension)
texts = []

# ---------------- LOAD ----------------
def load_index():
    global index, texts

    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)

    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, "rb") as f:
            texts = pickle.load(f)

# ---------------- SAVE ----------------
def save_index():
    faiss.write_index(index, INDEX_FILE)

    with open(TEXT_FILE, "wb") as f:
        pickle.dump(texts, f)

# ---------------- EMBEDDING (GEMINI) ----------------
def get_embedding(text):
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=[text]
    )

    return np.array(response.embeddings[0].values, dtype=np.float32)

# ---------------- ADD TO INDEX ----------------
def add_to_index(chunks):
    global texts

    for chunk in chunks:
        emb = get_embedding(chunk)

        index.add(np.array([emb]))
        texts.append(chunk)

    save_index()

# ---------------- SEARCH ----------------
def search(query, k=3):
    if len(texts) == 0:
        return []

    q_emb = get_embedding(query)

    D, I = index.search(np.array([q_emb]), k)

    return [texts[i] for i in I[0] if i < len(texts)]

# ---------------- INIT LOAD ----------------
load_index()
