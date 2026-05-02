"""Compile chunks into interconnected wiki articles using Gemini."""

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from google import genai

from .chunker import Chunk


@dataclass
class Article:
    title: str
    slug: str
    tags: list[str]
    content: str
    source_videos: list[dict]  # [{title, video_id}]
    backlinks: list[str]  # slugs of related articles


def _get_client() -> genai.Client:
    """Get Gemini client."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Export it or add to .env", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


def _slugify(title: str) -> str:
    """Convert title to kebab-case slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _build_chunk_summary(chunks: list[Chunk], max_chars: int = 200_000) -> str:
    """Build a text summary of all chunks for topic identification."""
    lines = []
    total = 0
    for chunk in chunks:
        entry = f"[Video: {chunk.video_title} | ID: {chunk.video_id} | Chunk {chunk.chunk_index}]\n{chunk.text[:500]}\n"
        if total + len(entry) > max_chars:
            break
        lines.append(entry)
        total += len(entry)
    return "\n---\n".join(lines)


def _call_gemini(client: genai.Client, prompt: str, retries: int = 3) -> str:
    """Call Gemini with retry logic."""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=prompt,
            )
            return response.text or ""
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Gemini error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Gemini failed after {retries} attempts: {e}", file=sys.stderr)
                return ""


def identify_topics(client: genai.Client, chunks: list[Chunk]) -> list[dict]:
    """Use Gemini to identify 10-20 key topics from the channel's content."""
    summary = _build_chunk_summary(chunks)

    prompt = f"""You are analyzing transcripts from a YouTube channel to identify the key topics and concepts covered.

Here are excerpts from the channel's videos:

{summary}

Based on these transcripts, identify 10-20 key topics/concepts that the channel covers extensively. For each topic, provide:
1. A clear, concise title (2-5 words)
2. A brief description (1 sentence)
3. 3-5 relevant tags

Return ONLY valid JSON in this exact format (no markdown code fences):
[
  {{"title": "Topic Title", "description": "Brief description", "tags": ["tag1", "tag2", "tag3"]}},
  ...
]"""

    print("Identifying key topics across the channel...")
    response = _call_gemini(client, prompt)

    # Parse JSON from response (handle markdown fences)
    response = response.strip()
    if response.startswith("```"):
        response = re.sub(r"^```\w*\n?", "", response)
        response = re.sub(r"\n?```$", "", response)

    try:
        topics = json.loads(response)
        print(f"Identified {len(topics)} topics.")
        return topics
    except json.JSONDecodeError:
        print("Failed to parse topics from Gemini response. Using fallback.", file=sys.stderr)
        return [{"title": "General Content", "description": "Main channel content", "tags": ["general"]}]


def compile_article(
    client: genai.Client,
    topic: dict,
    chunks: list[Chunk],
    all_topic_titles: list[str],
) -> Article | None:
    """Compile an article for a single topic from relevant chunks."""
    # Build context from all chunks (Gemini will pick the relevant ones)
    chunk_texts = []
    for chunk in chunks:
        chunk_texts.append(
            f"[Source: {chunk.video_title} | https://youtube.com/watch?v={chunk.video_id}]\n{chunk.text}"
        )

    # Limit total context to avoid token limits
    combined = "\n\n---\n\n".join(chunk_texts)
    if len(combined) > 300_000:
        combined = combined[:300_000] + "\n\n[...truncated]"

    other_topics = [t for t in all_topic_titles if t != topic["title"]]
    backlink_suggestions = ", ".join(other_topics)

    prompt = f"""You are writing a wiki article for an Obsidian knowledge base compiled from YouTube video transcripts.

TOPIC: {topic["title"]}
DESCRIPTION: {topic["description"]}

OTHER TOPICS IN THIS VAULT (use [[Topic Title]] syntax to link to them where relevant):
{backlink_suggestions}

SOURCE TRANSCRIPTS:
{combined}

Write a comprehensive wiki article about "{topic["title"]}" using ONLY information from the transcripts above. Follow these rules:

1. Write in clear, informative prose. Not a transcript summary — a proper article.
2. Synthesize information from multiple videos where possible.
3. Use [[Topic Title]] backlinks to reference other topics in the vault (use the exact titles listed above).
4. At the end, add source attributions like: [Source: Video Title](https://youtube.com/watch?v=VIDEO_ID)
5. Keep it between 500-2000 words.
6. Do NOT invent information not in the transcripts.
7. Do NOT include YAML frontmatter — just the article content.

Return ONLY the article content in Markdown format."""

    response = _call_gemini(client, prompt)
    if not response.strip():
        return None

    # Extract video sources mentioned
    source_pattern = r"youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"
    mentioned_ids = set(re.findall(source_pattern, response))

    source_videos = []
    seen_ids = set()
    for chunk in chunks:
        if chunk.video_id in mentioned_ids and chunk.video_id not in seen_ids:
            source_videos.append({"title": chunk.video_title, "video_id": chunk.video_id})
            seen_ids.add(chunk.video_id)

    # If no sources were explicitly mentioned, add top 3 most relevant
    if not source_videos:
        seen_ids = set()
        for chunk in chunks[:10]:
            if chunk.video_id not in seen_ids:
                source_videos.append({"title": chunk.video_title, "video_id": chunk.video_id})
                seen_ids.add(chunk.video_id)
            if len(source_videos) >= 3:
                break

    # Extract backlinks used
    backlink_pattern = r"\[\[([^\]]+)\]\]"
    used_backlinks = re.findall(backlink_pattern, response)
    backlink_slugs = [_slugify(b) for b in used_backlinks if b in all_topic_titles]

    slug = _slugify(topic["title"])

    return Article(
        title=topic["title"],
        slug=slug,
        tags=topic.get("tags", []),
        content=response.strip(),
        source_videos=source_videos,
        backlinks=backlink_slugs,
    )


def compile_articles(chunks: list[Chunk]) -> list[Article]:
    """Main compilation pipeline: identify topics, then compile each article."""
    if not chunks:
        print("No chunks to compile.")
        return []

    client = _get_client()

    # Step 1: Identify topics
    topics = identify_topics(client, chunks)
    if not topics:
        return []

    all_titles = [t["title"] for t in topics]

    # Step 2: Compile each topic into an article
    articles = []
    for i, topic in enumerate(topics, 1):
        print(f"  Compiling article [{i}/{len(topics)}]: {topic['title']}...")
        article = compile_article(client, topic, chunks, all_titles)
        if article:
            articles.append(article)
        # Small delay to respect rate limits
        if i < len(topics):
            time.sleep(1)

    print(f"\nCompiled {len(articles)} articles.")
    return articles
