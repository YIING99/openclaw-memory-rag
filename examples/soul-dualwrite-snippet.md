# SOUL.md Dual-Write Rule Snippet

Add the following to your lobster's `SOUL.md` to enable automatic dual-write (Feishu Bitable + memory/ directory).

---

```markdown
### 🔴 Dual-Write Rule: Knowledge Must Also Be Written to Memory Search Index

**Every time you successfully write a record to the Feishu Bitable, you MUST also
create a corresponding knowledge file in the memory/ directory.** This is the
critical step to ensure semantic search can find this knowledge. Do NOT skip it.

#### Trigger
- After every successful record creation via feishu_bitable tool

#### File Naming
- Use the Feishu record ID: `memory/{record_id}.md`

#### File Format

## [Date] Title
- **Type**: Content type | **Source**: Source platform | **Rating**: Rating
- **Tags**: Tag list
- **Feishu Record**: record_id

**Core Insight**: Distilled core content

**My Thoughts**: Personal analysis

**Action Items**: Next steps

**Search Keywords**: synonyms, use-case terms, abbreviations (5-10 keywords)

#### Execution
Use the exec tool to write the file.

#### Self-Check
After writing, confirm the file exists: ls -la memory/{record_id}.md
```

---

## Why Dual-Write?

Without dual-write, knowledge only exists in Feishu Bitable. Since OpenClaw's semantic
search engine reads from `memory/*.md` files, new knowledge won't be searchable until
it's also written to the memory directory.

The dual-write rule ensures:
1. **Real-time searchability** — new knowledge is immediately available to semantic search
2. **Data consistency** — Feishu (structured storage) and memory/ (vector storage) stay in sync
3. **Redundancy** — even if one system fails, the other still has the data
