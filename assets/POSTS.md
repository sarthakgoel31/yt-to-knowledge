# Launch Posts

## Reddit: r/ObsidianMD

**Title:** I built a CLI that turns any YouTube channel into an Obsidian vault with [[backlinks]]

**Body:**

I watch a lot of educational YouTube (3Blue1Brown, Lex Fridman, Huberman, etc.) and kept losing insights across hundreds of videos. So I built a tool that:

1. Downloads every transcript from a channel
2. Chunks them at natural topic boundaries
3. Uses Gemini (free tier) to identify 10-20 key topics and compile wiki articles
4. Outputs an Obsidian vault with `[[backlinks]]` between articles

One article might synthesize content from 5 different videos on the same topic. Open the vault in Obsidian and you get a graph view of the channel's entire knowledge base.

It also has optional FAISS semantic search if you want to find the exact moment something was said across all videos.

**Usage:**
```
python -m src --channel @3blue1brown --output ./3b1b-vault
```

Then open the folder in Obsidian. That's it.

Free, open source, runs locally: https://github.com/sarthakgoel31/yt-to-knowledge

Would love feedback from the community -- especially on what output format works best for your Obsidian workflow.

---

## Reddit: r/selfhosted

**Title:** Turn any YouTube channel into a searchable knowledge base -- self-hosted, free, no API costs

**Body:**

Built a Python CLI that turns YouTube channels into structured knowledge bases:

- Downloads transcripts via yt-dlp (parallel, with resume)
- Gemini free tier synthesizes wiki articles across videos
- Optional FAISS vector search over raw transcripts
- Output: Obsidian-compatible markdown with backlinks

No paid APIs. Gemini free tier handles 1,500 requests/day, a 100-video channel uses ~30-50. Runs entirely on your machine.

```
python -m src --channel @lexfridman --output ./lex-vault --max-videos 50
python -m src --query "consciousness and free will" --output ./lex-vault
```

GitHub: https://github.com/sarthakgoel31/yt-to-knowledge

---

## Reddit: r/LocalLLaMA / r/ChatGPTPro

**Title:** Free alternative to NotebookLM for YouTube channels -- outputs an Obsidian knowledge base

**Body:**

NotebookLM is great but you can't export the knowledge, can't search your own way, and it's not self-hosted.

I built a CLI that does something similar but better for power users:

- Feed it any YouTube channel or playlist
- It downloads all transcripts, identifies key topics using Gemini (free tier)
- Compiles cross-referenced wiki articles (not just raw chunks)
- Outputs an Obsidian vault with [[backlinks]] and graph view
- Optional: FAISS semantic search to find exact moments across all videos

The key difference from typical RAG tools: those just index raw transcript chunks and return snippets. This actually *synthesizes* knowledge -- one article might pull from 5 different videos on the same topic.

Free, open source, self-hosted: https://github.com/sarthakgoel31/yt-to-knowledge

---

## Hacker News: Show HN

**Title:** Show HN: Turn YouTube channels into Obsidian knowledge bases with AI synthesis

**Body:**

I built a Python CLI that takes a YouTube channel URL and produces an Obsidian vault of interconnected wiki articles.

Most YouTube-to-RAG tools index raw transcript chunks for similarity search. This tool goes further -- it uses Gemini (free tier) to identify 10-20 key topics across all videos, then synthesizes each topic into a wiki article with [[backlinks]] to related concepts.

The pipeline: yt-dlp transcripts -> smart chunking at topic boundaries -> Gemini topic identification + article compilation -> Obsidian markdown with YAML frontmatter.

Also has optional FAISS semantic search if you want to find exact moments across raw transcripts.

A 100-video channel uses ~30-50 Gemini free tier requests. Effectively zero cost.

https://github.com/sarthakgoel31/yt-to-knowledge

---

## Twitter/X

**Post 1 (launch):**

I built a CLI that turns any YouTube channel into an Obsidian knowledge base.

Feed it @3blue1brown. Get 15 interconnected wiki articles with [[backlinks]], synthesized across 100+ videos.

Free. Self-hosted. One command.

github.com/sarthakgoel31/yt-to-knowledge

[attach demo GIF]

**Post 2 (thread):**

How it works:

1/ yt-dlp downloads all transcripts in parallel
2/ Smart chunking at natural topic boundaries
3/ Gemini (free tier) identifies key topics
4/ Compiles wiki articles pulling from multiple videos
5/ Outputs Obsidian vault with backlinks + graph view

Most RAG tools give you raw chunks.
This gives you a knowledge base you can actually read.

**Post 3 (vs NotebookLM angle):**

NotebookLM but:
- Self-hosted
- Obsidian output with [[backlinks]]
- FAISS search over raw transcripts
- Free (Gemini free tier)
- You own the data

One command. Any channel.

github.com/sarthakgoel31/yt-to-knowledge
