from vectorstore import add_to_index
from utils import split_text

def load_file(file):
    filename = file.name.lower()

    text = ""
    total_chunks = 0

    if filename.endswith(".txt"):

        buffer = ""

        for line in file:
            try:
                buffer += line.decode("utf-8")
            except:
                continue

            if len(buffer) > 3000:
                chunks = split_text(buffer, chunk_size=300)
                add_to_index(chunks)
                total_chunks += len(chunks)
                buffer = ""

        if buffer:
            chunks = split_text(buffer, chunk_size=300)
            add_to_index(chunks)
            total_chunks += len(chunks)

    else:
        return 0

    return total_chunks
