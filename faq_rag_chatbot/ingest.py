from vectorstore import add_to_index
from utils import split_text

def load_file(text):

    if not text:
        return 0

    chunks = split_text(text, chunk_size=300)

    if chunks:
        add_to_index(chunks)
        return len(chunks)

    return 0
