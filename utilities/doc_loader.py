# doc_loader.py
import os
from core.app_config import KNOWLEDGE_BASE_DIR

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_KB_DIR = str(KNOWLEDGE_BASE_DIR)

class LocalDocChunker:
    def __init__(self, kb_dir=DEFAULT_KB_DIR, chunk_size=350, chunk_overlap=50):
        self.kb_dir = kb_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_and_chunk_all(self):
        """Walks the knowledge base directory and yields processed document chunks."""
        documents = []
        if not os.path.exists(self.kb_dir):
            print(f"Warning: {self.kb_dir} does not exist.")
            return documents

        for root, _, files in os.walk(self.kb_dir):
            for file in files:
                if file.endswith((".md", ".txt")):
                    file_path = os.path.join(root, file)
                    doc_chunks = self._process_file(file_path)
                    documents.extend(doc_chunks)
        
        print(f"[💡] Processed {len(documents)} text chunks across all offline files.")
        return documents

    def _process_file(self, file_path):
        """Reads file and splits small command docs by whole file, larger docs by words."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()

            if not content:
                return []

            rel_path = os.path.relpath(file_path, self.kb_dir).replace("\\", "/")
            words = content.split()

            # Short command reference or TLDR doc -> keep whole file as single chunk
            if len(words) <= self.chunk_size:
                return [{
                    "source": rel_path,
                    "text": f"[Source: {rel_path}]\n{content}"
                }]

            # Larger doc -> word sliding window
            chunks = []
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "source": rel_path,
                    "text": f"[Source: {rel_path}]\n{chunk_text}"
                })

            return chunks
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []


if __name__ == "__main__":
    chunker = LocalDocChunker()
    docs = chunker.load_and_chunk_all()
    if docs:
        print("\nExample Chunk Output:\n" + "-"*40)
        print(docs[0]["text"][:300] + "...")