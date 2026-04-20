from vectorstore import add_to_index
from utils import split_text

import pdfplumber
from PIL import Image
import pytesseract

def load_file(file):
    filename = file.name.lower()

    text = ""

    # ---------------- TXT ----------------
    if filename.endswith(".txt"):
        text = file.read().decode("utf-8")

    # ---------------- PDF ----------------
    elif filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    # ---------------- IMAGE (OCR) ----------------
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(file)
        text = pytesseract.image_to_string(image)

    else:
        return 0

    # ---------------- CHUNK + INDEX ----------------
    chunks = split_text(text, chunk_size=300)

    for chunk in chunks:
        add_to_index([chunk])

    return len(chunks)