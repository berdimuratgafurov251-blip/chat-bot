from vectorstore import add_to_index
from utils import split_text

def load_file(file):
    filename = file.name.lower()

    if filename.endswith(".txt"):

        text = file.read().decode("utf-8", errors="ignore")

        chunks = split_text(text, chunk_size=300)

        if chunks:
            add_to_index(chunks)
            return len(chunks)

    return 0
