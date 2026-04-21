import faiss
import numpy as np
from openai import OpenAI
import os
import pickle
from dotenv import load_dotenv

# ---------------- ENV ----------------
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ GEMINI_API_KEY topilmadi!")

client = OpenAI(api_key=api_key)

# ---------------- FILE PATHS ----------------
INDEX_FILE = "faiss_index.bin"
TEXT_FILE = "texts.pkl"

# ---------------- INIT ----------------
dimension = 1536
index = faiss.IndexFlatL2(dimension)
texts = []

# ---------------- LOAD EXISTING DATA ----------------
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

# ---------------- EMBEDDING ----------------
def get_embedding(text):
    res = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(res.data[0].embedding, dtype=np.float32)

# ---------------- ADD DATA ----------------
def add_to_index(chunks):
    global texts

    for chunk in chunks:
        emb = get_embedding(chunk)
        index.add(np.array([emb]))
        texts.append(chunk)

    save_index()  # 🔥 HAR SAFAR SAQLANADI

# ---------------- SEARCH ----------------
def search(query, k=3):
    if len(texts) == 0:
        return []

    q_emb = get_embedding(query)
    D, I = index.search(np.array([q_emb]), k)

    return [texts[i] for i in I[0] if i < len(texts)]

# ---------------- LOAD ON START ----------------
load_index()
