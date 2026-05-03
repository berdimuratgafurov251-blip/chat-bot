import faiss
import numpy as np
import pickle
import os
from google import genai
import streamlit as st

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

INDEX_FILE = "faiss_index.bin"
TEXT_FILE = "texts.pkl"

index = None
texts = []

# ---------------- LOAD ----------------
def load_index():
    global index, texts

    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, "rb") as f:
            texts = pickle.load(f)

    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)

# ---------------- SAVE ----------------
def save_index():
    faiss.write_index(index, INDEX_FILE)

    with open(TEXT_FILE, "wb") as f:
        pickle.dump(texts, f)

# ---------------- EMBEDDING ----------------
def get_embedding(text):
    response = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=[text]
    )

    vec = np.array(response.embeddings[0].values, dtype=np.float32)
    return vec

# ---------------- INIT INDEX (SMART) ----------------
def init_index_if_needed(vec):
    global index

    if index is None:
        dim = len(vec)
        index = faiss.IndexFlatL2(dim)
        print(f"🔥 FAISS initialized with dim = {dim}")

# ---------------- ADD ----------------
def add_to_index(chunks):
    global texts

   
    response = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=chunks
    )

    embeddings = [
        np.array(e.values, dtype=np.float32)
        for e in response.embeddings
    ]

    
    init_index_if_needed(embeddings[0])

    index.add(np.array(embeddings, dtype=np.float32))
    texts.extend(chunks)

    save_index()

# ---------------- SEARCH ----------------
def search(query, k=3):
    if index is None or len(texts) == 0:
        return []

    q_emb = get_embedding(query)

    D, I = index.search(np.array([q_emb], dtype=np.float32), k)

    return [texts[i] for i in I[0] if 0 <= i < len(texts)]

# ---------------- LOAD ON START ----------------
load_index()
