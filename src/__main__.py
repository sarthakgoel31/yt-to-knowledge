"""
yt-to-knowledge: Turn any YouTube channel into an Obsidian knowledge base.

Usage:
  python -m src --channel @3blue1brown --output ./vault
  python -m src --channel "https://youtube.com/@lexfridman" --output ./vault --max-videos 50
  python -m src --playlist "PLZHQObOWTQDNU6R1_67000Dx_ZZJNR6-1" --output ./vault
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from .chunker import chunk_transcripts
from .compiler import compile_articles
from .fetcher import fetch_transcripts
from .vault import write_vault


def main():
    parser = argparse.ArgumentParser(
        prog="yt-to-knowledge",
        description="Turn any YouTube channel into an Obsidian knowledge base.",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--channel", help="YouTube channel URL or @handle (e.g., @3blue1brown)")
    source.add_argument("--playlist", help="YouTube playlist ID")

    parser.add_argument("--output", default="./output", help="Output directory for the vault (default: ./output)")
    parser.add_argument("--max-videos", type=int, default=100, help="Maximum videos to process (default: 100)")
    parser.add_argument("--lang", default="en", help="Subtitle language code (default: en)")

    args = parser.parse_args()

    output_dir = Path(args.output)
    source_name = args.channel or args.playlist
    is_playlist = args.playlist is not None

    print(f"yt-to-knowledge v1.0.0")
    print(f"{'Playlist' if is_playlist else 'Channel'}: {source_name}")
    print(f"Output: {output_dir.resolve()}")
    print(f"Max videos: {args.max_videos}")
    print()

    start = time.time()

    # Step 1: Fetch transcripts
    videos = asyncio.run(
        fetch_transcripts(
            channel_or_playlist=source_name,
            output_dir=output_dir,
            max_videos=args.max_videos,
            lang=args.lang,
            is_playlist=is_playlist,
        )
    )

    if not videos:
        print("No transcripts fetched. Exiting.")
        sys.exit(1)

    # Step 2: Chunk transcripts
    transcripts_dir = output_dir / "transcripts"
    chunks = chunk_transcripts(transcripts_dir)

    if not chunks:
        print("No chunks created. Exiting.")
        sys.exit(1)

    # Step 3: Compile into wiki articles
    print(f"\nCompiling wiki articles with Gemini...")
    articles = compile_articles(chunks)

    if not articles:
        print("No articles compiled. Exiting.")
        sys.exit(1)

    # Step 4: Write vault
    print()
    write_vault(articles, videos, output_dir)

    elapsed = time.time() - start
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"\nDone in {minutes}m {seconds}s.")


if __name__ == "__main__":
    main()
