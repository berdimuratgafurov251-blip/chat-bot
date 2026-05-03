from vectorstore import add_to_index
from utils import split_text

def load_file(text):
    if not text:
        return 0

    text = text.replace("\n", " ").strip()

    chunks = split_text(text, chunk_size=300)

    if len(chunks) == 0:
        return 0

    add_to_index(chunks)

    return len(chunks)
