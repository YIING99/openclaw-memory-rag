# OpenClaw Memory RAG

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Gateway-blue)](https://github.com/nicepkg/openclaw)

English | [中文](README.zh-CN.md)

> Give your OpenClaw lobster long-term memory — Hybrid Search (70% vector semantics + 30% BM25 keywords) for precise cross-session knowledge recall.

---

## What Is This?

A **ready-to-use Memory RAG solution** that gives your OpenClaw AI Agent cross-session semantic search capabilities.

**Core Features**:
- Natural language search over historical knowledge ("that article about XX from last week")
- Hybrid Search: vector semantic matching + BM25 exact keyword matching
- Feishu (Lark) Bitable dual-write sync (optional)
- Automatic daily log archival to prevent search noise

**End Result**:
```
You: "Did we ever discuss getting a US phone number?"
Lobster: Found it! Tello eSIM, $5/month US phone number... (precise recall)

You: "Find me the notes about AI hallucination"
Lobster: Found it! Trust chain pollution — description ≠ reality... (precise recall)
```

## Repository Structure

```
openclaw-memory-rag/
├── README.md                          # English README (this file)
├── README.zh-CN.md                    # Chinese README
├── LICENSE                            # MIT License
├── docs/
│   └── technical-report.zh-CN.md      # Technical report (Chinese, with industry comparisons)
├── scripts/
│   ├── sync-feishu-to-memory.py       # Feishu single-table → memory/ sync
│   ├── sync-feishu-to-memory-multi.py # Feishu multi-table → memory/ sync
│   └── move-daily-logs.sh             # Daily log archival script
└── examples/
    ├── openclaw-config.json            # memorySearch config example
    ├── soul-dualwrite-snippet.md       # SOUL.md dual-write rule snippet
    └── knowledge-file-template.md      # Knowledge file template
```

---

## Prerequisites

| Requirement | Description | If Missing |
|-------------|-------------|------------|
| **OpenClaw instance** | A running OpenClaw Gateway agent | Install OpenClaw first |
| **VPS or server** | Machine running your lobster, SSH accessible | DigitalOcean $6/mo works fine |
| **Embedding API Key** | For converting text to vectors (this guide uses ZAI) | Step 1 below |
| **Knowledge content** | Articles, notes, insights you want the lobster to remember | At least 5-10 entries |

**Optional but recommended**:
- Feishu (Lark) Bitable for structured storage + visual management
- Feishu App for API sync

---

## Quick Start

### Step 1: Get an Embedding API Key

**Recommended: ZAI embedding-3** (optimized for Chinese, 2048 dimensions, OpenAI-compatible API)

1. Sign up at [ZAI Open Platform](https://open.bigmodel.cn/)
2. Create an API Key in Console → API Keys
3. Ensure you have embedding quota (GLM Coding Pro plans may not include embedding)

**Alternatives**: OpenAI text-embedding-3-small, Gemini embedding-001

### Step 2: Configure memorySearch

Add the `memorySearch` block to your `openclaw.json` under `agents.defaults`:

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "openai",
        "model": "embedding-3",
        "remote": {
          "baseUrl": "https://open.bigmodel.cn/api/paas/v4/",
          "apiKey": "YOUR_API_KEY_HERE"
        },
        "query": {
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.7,
            "textWeight": 0.3,
            "candidateMultiplier": 4
          }
        },
        "cache": {
          "enabled": true,
          "maxEntries": 10000
        }
      }
    }
  }
}
```

See [`examples/openclaw-config.json`](examples/openclaw-config.json) for the full config example.

**Key parameters**:

| Parameter | Purpose | Recommended | Why |
|-----------|---------|-------------|-----|
| `provider` | API protocol | `"openai"` | ZAI is OpenAI-compatible |
| `model` | Embedding model | `"embedding-3"` | ZAI's model name |
| `vectorWeight` | Semantic search weight | `0.7` | 70% semantic understanding |
| `textWeight` | Keyword search weight | `0.3` | 30% exact matching |
| `candidateMultiplier` | Candidate expansion | `4` | 4x candidates before reranking |

### Step 3: Prepare Knowledge Files

**One knowledge entry = one .md file.** This is the core principle.

Place files in `~/.openclaw/workspace/memory/`:

```bash
mkdir -p ~/.openclaw/workspace/memory/
```

See [`examples/knowledge-file-template.md`](examples/knowledge-file-template.md) for the file format.

**Why one file per entry?** OpenClaw chunks by fixed character count. When multiple entries share a file, chunk boundaries cut across entries, contaminating search results. One file = one chunk = precise matching. Our tests showed a **23% precision improvement** after splitting.

### Step 4: Build Vector Index

```bash
# Multi-instance users: set HOME first
export HOME=/root/bot2-home  # your lobster's config parent dir

cd ~/.openclaw
npx openclaw memory index --force
```

Test it:
```bash
npx openclaw memory search 'your search query'
```

### Step 5: Archive Daily Logs

OpenClaw auto-generates daily heartbeat logs in memory/ that dilute search precision. Use the archival script:

```bash
# Copy and schedule
cp scripts/move-daily-logs.sh ~/move-daily-logs.sh
chmod +x ~/move-daily-logs.sh
(crontab -l 2>/dev/null; echo '0 6 * * * $HOME/move-daily-logs.sh') | crontab -
```

### Step 6: Set Up Dual-Write (Optional)

If your lobster writes to Feishu Bitable, ensure knowledge also lands in memory/:

- **Option A**: Add dual-write rules to SOUL.md — see [`examples/soul-dualwrite-snippet.md`](examples/soul-dualwrite-snippet.md)
- **Option B**: Cron sync script — see [`scripts/sync-feishu-to-memory.py`](scripts/sync-feishu-to-memory.py)

---

## Core Principles

### 1. One Knowledge = One File = One Chunk

Never merge multiple entries into one file. Separate files = precise search.

### 2. Search Keywords Are for Machines

The `**Search Keywords**` line at the bottom of each file fuels the BM25 channel. Include synonyms, use-case terms, and abbreviations.

### 3. Noise Is the Enemy of Precision

Only keep high-quality knowledge files in memory/. Archive logs, heartbeats, and temp files elsewhere.

---

## Architecture

```
User speaks to lobster / sends article
              ↓
     Lobster distills knowledge
              ↓
      ┌───────┴───────┐
      ↓               ↓
Feishu Bitable    memory/{id}.md     ← dual-write
(structured)      (vectorized)
      ↓               ↓
Visual mgmt      Hybrid Search
Tags/ratings     vector 70% + BM25 30%
      ↓               ↓
      └───────┬───────┘
              ↓
   User asks "that article from before..."
              ↓
        Precise recall ✅
```

---

## FAQ

| Question | Answer |
|----------|--------|
| No search results? | Check memory/ has .md files, rebuild index with `--force`, verify HOME for multi-instance |
| Inaccurate results? | Archive daily logs, split merged files, add search keywords |
| Need to rebuild after adding files? | SOUL.md dual-write auto-indexes; manual adds need `index --force` |
| VPS too small for embedding? | Embedding is cloud API — no local resources needed, 3.8GB VPS is fine |
| No Feishu? | Feishu is optional. Core is .md files in memory/ — create manually or sync from Notion/Obsidian |
| Share knowledge across lobsters? | Symlinks, rsync, or independent maintenance all work |

---

## Technical Report

For the full technical design, industry comparison, and four-round optimization data:

📄 [Technical Report (Chinese)](docs/technical-report.zh-CN.md)

---

## Contributing

Issues and PRs welcome!

- **Bug reports**: Include your OpenClaw version, embedding model, and reproduction steps
- **Feature requests**: Describe the scenario and expected outcome
- **Script improvements**: Support for more knowledge sources (Notion, Obsidian, Telegram, etc.) is welcome

## License

[MIT](LICENSE)

---

*Author: KingMaker | Built from real-world lobster fleet experience*
