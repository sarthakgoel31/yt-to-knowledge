"""Fetch video transcripts from a YouTube channel or playlist using yt-dlp."""

import asyncio
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoInfo:
    video_id: str
    title: str


def list_videos(channel_or_playlist: str, max_videos: int = 100, is_playlist: bool = False) -> list[VideoInfo]:
    """List all video IDs and titles from a channel or playlist."""
    if is_playlist:
        url = f"https://www.youtube.com/playlist?list={channel_or_playlist}"
    elif channel_or_playlist.startswith("http"):
        url = channel_or_playlist
    elif channel_or_playlist.startswith("@"):
        url = f"https://www.youtube.com/{channel_or_playlist}/videos"
    else:
        url = f"https://www.youtube.com/@{channel_or_playlist}/videos"

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s",
        "--playlist-end", str(max_videos),
        "--no-warnings",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"Error listing videos: {result.stderr.strip()}", file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            video_id, title = parts
            # Skip shorts and live streams that have no real transcript
            if video_id and title:
                videos.append(VideoInfo(video_id=video_id.strip(), title=title.strip()))

    return videos


def _fetch_single_transcript(video: VideoInfo, output_dir: Path, lang: str) -> bool:
    """Fetch transcript for a single video. Returns True if successful."""
    transcript_path = output_dir / f"{video.video_id}.txt"

    # Resume support: skip if already fetched
    if transcript_path.exists() and transcript_path.stat().st_size > 0:
        return True

    url = f"https://www.youtube.com/watch?v={video.video_id}"
    temp_dir = output_dir / "_temp"
    temp_dir.mkdir(exist_ok=True)

    # Try manual subtitles first, then auto-generated
    cmd = [
        "yt-dlp",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "vtt",
        "--skip-download",
        "--no-warnings",
        "--output", str(temp_dir / "%(id)s.%(ext)s"),
        url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False

    # Find the subtitle file
    vtt_file = None
    for pattern in [f"{video.video_id}.{lang}.vtt", f"{video.video_id}*.vtt"]:
        matches = list(temp_dir.glob(pattern))
        if matches:
            vtt_file = matches[0]
            break

    if not vtt_file or not vtt_file.exists():
        return False

    # Parse VTT to plain text
    text = _parse_vtt(vtt_file.read_text(encoding="utf-8", errors="replace"))
    if not text.strip():
        vtt_file.unlink(missing_ok=True)
        return False

    # Write transcript with title as first line
    transcript_path.write_text(f"{video.title}\n\n{text}", encoding="utf-8")

    # Cleanup temp file
    vtt_file.unlink(missing_ok=True)
    return True


def _parse_vtt(vtt_content: str) -> str:
    """Parse VTT subtitle content into clean plain text."""
    lines = vtt_content.split("\n")
    text_lines = []
    seen = set()

    for line in lines:
        line = line.strip()
        # Skip VTT headers, timestamps, and empty lines
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        if line.startswith("NOTE"):
            continue

        # Remove VTT tags
        clean = re.sub(r"<[^>]+>", "", line)
        clean = clean.strip()

        if clean and clean not in seen:
            seen.add(clean)
            text_lines.append(clean)

    return " ".join(text_lines)


async def fetch_transcripts(
    channel_or_playlist: str,
    output_dir: Path,
    max_videos: int = 100,
    lang: str = "en",
    is_playlist: bool = False,
    max_concurrent: int = 5,
) -> list[VideoInfo]:
    """Fetch all transcripts from a channel/playlist in parallel.

    Returns list of videos that were successfully fetched.
    """
    transcripts_dir = output_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    print(f"Listing videos from {'playlist' if is_playlist else 'channel'}...")
    videos = list_videos(channel_or_playlist, max_videos, is_playlist)
    if not videos:
        print("No videos found.")
        return []

    print(f"Found {len(videos)} videos. Fetching transcripts...")

    successful = []
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        tasks = []
        for video in videos:
            task = loop.run_in_executor(
                executor, _fetch_single_transcript, video, transcripts_dir, lang
            )
            tasks.append((video, task))

        for i, (video, task) in enumerate(tasks, 1):
            success = await task
            status = "ok" if success else "skip (no transcript)"
            print(f"  [{i}/{len(videos)}] {video.title[:60]}... {status}")
            if success:
                successful.append(video)

    # Cleanup temp directory
    temp_dir = transcripts_dir / "_temp"
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\nFetched {len(successful)}/{len(videos)} transcripts.")
    return successful
