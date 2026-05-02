"""Smart chunking of transcripts by topic boundaries."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chunk:
    text: str
    video_title: str
    video_id: str
    chunk_index: int
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())


MIN_CHUNK_WORDS = 300
MAX_CHUNK_WORDS = 800
TARGET_CHUNK_WORDS = 600


def _find_split_points(text: str) -> list[int]:
    """Find natural split points in text (paragraph breaks, topic shifts)."""
    points = []

    # Double newlines (paragraph breaks)
    for m in re.finditer(r"\n\s*\n", text):
        points.append(m.start())

    # Sentence boundaries near target length (fallback)
    for m in re.finditer(r"[.!?]\s+", text):
        points.append(m.end())

    return sorted(set(points))


def _split_text(text: str) -> list[str]:
    """Split text into chunks at natural boundaries."""
    words = text.split()
    total_words = len(words)

    if total_words <= MAX_CHUNK_WORDS:
        return [text] if total_words >= MIN_CHUNK_WORDS // 2 else []

    split_points = _find_split_points(text)
    if not split_points:
        # Fallback: split by word count
        chunks = []
        for i in range(0, total_words, TARGET_CHUNK_WORDS):
            chunk_words = words[i : i + TARGET_CHUNK_WORDS]
            if len(chunk_words) >= MIN_CHUNK_WORDS // 2:
                chunks.append(" ".join(chunk_words))
        return chunks

    # Use split points to create chunks near target size
    chunks = []
    last_pos = 0

    for point in split_points:
        segment = text[last_pos:point].strip()
        segment_words = len(segment.split())

        if segment_words >= TARGET_CHUNK_WORDS:
            chunks.append(segment)
            last_pos = point
        elif segment_words >= MAX_CHUNK_WORDS:
            # Segment too long, force split
            chunks.append(segment)
            last_pos = point

    # Don't forget the remainder
    remainder = text[last_pos:].strip()
    if remainder:
        remainder_words = len(remainder.split())
        if chunks and remainder_words < MIN_CHUNK_WORDS:
            # Merge small remainder with last chunk
            chunks[-1] = chunks[-1] + " " + remainder
        else:
            chunks.append(remainder)

    return [c for c in chunks if len(c.split()) >= MIN_CHUNK_WORDS // 2]


def chunk_transcripts(transcripts_dir: Path) -> list[Chunk]:
    """Read all transcripts and split them into smart chunks.

    Returns list of Chunk objects with metadata.
    """
    all_chunks = []

    transcript_files = sorted(transcripts_dir.glob("*.txt"))
    if not transcript_files:
        print("No transcript files found.")
        return []

    print(f"Chunking {len(transcript_files)} transcripts...")

    for filepath in transcript_files:
        video_id = filepath.stem
        content = filepath.read_text(encoding="utf-8", errors="replace")

        # First line is the title
        lines = content.split("\n", 1)
        title = lines[0].strip()
        text = lines[1].strip() if len(lines) > 1 else ""

        if not text:
            continue

        text_chunks = _split_text(text)

        for i, chunk_text in enumerate(text_chunks):
            chunk = Chunk(
                text=chunk_text,
                video_title=title,
                video_id=video_id,
                chunk_index=i,
            )
            all_chunks.append(chunk)

    print(f"Created {len(all_chunks)} chunks from {len(transcript_files)} transcripts.")
    return all_chunks
