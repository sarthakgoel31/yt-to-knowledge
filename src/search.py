"""Semantic search over transcript chunks using FAISS + sentence-transformers."""

import json
import numpy as np
from pathlib import Path

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    faiss = None
    SentenceTransformer = None

from .chunker import Chunk

EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384


def build_index(chunks: list[Chunk], output_dir: Path) -> None:
    """Embed all chunks and save FAISS index + metadata."""
    if faiss is None:
        print("Install search deps: pip install faiss-cpu sentence-transformers")
        return

    print(f"Embedding {len(chunks)} chunks with {EMBED_MODEL}...")
    model = SentenceTransformer(EMBED_MODEL)
    texts = [c.text for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    index = faiss.IndexFlatIP(EMBED_DIM)  # cosine similarity (normalized vectors)
    index.add(np.array(embeddings).astype("float32"))

    search_dir = output_dir / "search"
    search_dir.mkdir(exist_ok=True)

    faiss.write_index(index, str(search_dir / "chunks.faiss"))

    metadata = [
        {
            "video_title": c.video_title,
            "video_id": c.video_id,
            "chunk_index": c.chunk_index,
            "text": c.text[:500],  # preview
            "url": f"https://youtube.com/watch?v={c.video_id}",
        }
        for c in chunks
    ]
    (search_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"Search index saved: {len(chunks)} chunks → {search_dir}/")


def search(query: str, output_dir: Path, top_k: int = 5) -> list[dict]:
    """Search the FAISS index for chunks matching a natural language query."""
    if faiss is None:
        print("Install search deps: pip install faiss-cpu sentence-transformers")
        return []

    search_dir = output_dir / "search"
    index_path = search_dir / "chunks.faiss"
    meta_path = search_dir / "metadata.json"

    if not index_path.exists():
        print("No search index found. Run with --search to build one first.")
        return []

    model = SentenceTransformer(EMBED_MODEL)
    index = faiss.read_index(str(index_path))
    metadata = json.loads(meta_path.read_text())

    query_vec = model.encode([query], normalize_embeddings=True).astype("float32")
    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        meta = metadata[idx]
        results.append({**meta, "score": float(score)})

    return results
