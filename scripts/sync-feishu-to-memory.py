#!/usr/bin/env python3
"""
Feishu Bitable → memory/ directory sync script (single table version)

Periodically checks Feishu for new records not yet synced to memory/.
After syncing, automatically rebuilds the OpenClaw memory index.

Usage:
  1. Fill in the configuration section below with your Feishu app credentials
  2. Run manually: python3 sync-feishu-to-memory.py
  3. Or set up as cron job: 30 */6 * * * /usr/bin/python3 $HOME/sync-feishu-to-memory.py

Cron example (every 6 hours):
  (crontab -l 2>/dev/null; echo '30 */6 * * * /usr/bin/python3 $HOME/sync-feishu-to-memory.py >> /tmp/feishu-sync.log 2>&1') | crontab -

Author: KingMaker
License: MIT
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ========== CONFIGURATION (replace with your values) ==========
FEISHU_APP_ID = "YOUR_FEISHU_APP_ID"
FEISHU_APP_SECRET = "YOUR_FEISHU_APP_SECRET"
BITABLE_APP_TOKEN = "YOUR_BITABLE_APP_TOKEN"
TABLE_ID = "YOUR_TABLE_ID"
MEMORY_DIR = os.path.expanduser("~/.openclaw/workspace/memory")
# ===============================================================


# === Feishu API ===
def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if result.get("code") != 0:
        print(f"[ERROR] Failed to get token: {result}")
        sys.exit(1)
    return result["tenant_access_token"]


def list_records(token, page_token=None):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{TABLE_ID}/records?page_size=100"
    if page_token:
        url += f"&page_token={page_token}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_all_records(token):
    records = []
    page_token = None
    while True:
        result = list_records(token, page_token)
        if result.get("code") != 0:
            print(f"[ERROR] Failed to get records: {result}")
            sys.exit(1)
        items = result.get("data", {}).get("items", [])
        records.extend(items)
        if not result["data"].get("has_more"):
            break
        page_token = result["data"].get("page_token")
    return records


# === Field extraction ===
def get_text(val):
    """Extract plain text from a Feishu field value."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, dict):
        return val.get("text", val.get("link", str(val)))
    return str(val)


def format_date(timestamp_ms):
    """Convert millisecond timestamp to date string."""
    if not timestamp_ms:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        ts = int(timestamp_ms) / 1000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return datetime.now().strftime("%Y-%m-%d")


def generate_search_keywords(fields):
    """Extract search keywords from title, tags, and tech stack fields."""
    keywords = set()
    title = get_text(fields.get("标题", ""))
    if title:
        keywords.add(title)
    # Customize these field names to match your Bitable schema
    for field_name in ["标签", "关联技术栈"]:
        val = fields.get(field_name, [])
        if isinstance(val, list):
            for t in val:
                keywords.add(str(t))
    return ", ".join(keywords) if keywords else ""


def record_to_md(record_id, fields):
    """Convert a Feishu record to a memory .md file.

    Customize the field names below to match your Bitable schema.
    """
    title = get_text(fields.get("标题", "无标题"))
    content_type = get_text(fields.get("内容类型", ""))
    source = get_text(fields.get("来源平台", ""))
    rating = get_text(fields.get("公众号素材评级", ""))
    tags = get_text(fields.get("标签", ""))
    insight = get_text(fields.get("核心洞察", ""))
    thinking = get_text(fields.get("我的思考", ""))
    action = get_text(fields.get("行动项", ""))
    date_str = format_date(fields.get("日期"))
    keywords = generate_search_keywords(fields)

    lines = []
    lines.append(f"## [{date_str}] {title}")
    lines.append(f"- **类型**：{content_type} | **来源**：{source} | **评级**：{rating}")
    lines.append(f"- **标签**：{tags}")
    lines.append(f"- **飞书记录**：{record_id}")
    lines.append("")
    if insight:
        lines.append(f"**核心洞察**：{insight}")
        lines.append("")
    if thinking:
        lines.append(f"**个人思考**：{thinking}")
        lines.append("")
    if action:
        lines.append(f"**行动项**：{action}")
        lines.append("")
    if keywords:
        lines.append(f"**搜索关键词**：{keywords}")
        lines.append("")
    return "\n".join(lines)


# === Main ===
def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting Feishu → memory sync...")

    os.makedirs(MEMORY_DIR, exist_ok=True)
    existing_ids = set()
    for f in os.listdir(MEMORY_DIR):
        if f.startswith("rec") and f.endswith(".md"):
            existing_ids.add(f[:-3])
    print(f"  memory/ has {len(existing_ids)} existing knowledge files")

    token = get_tenant_token()
    records = get_all_records(token)
    print(f"  Feishu has {len(records)} total records")

    new_count = 0
    for item in records:
        record_id = item.get("record_id", "")
        if not record_id or record_id in existing_ids:
            continue
        fields = item.get("fields", {})
        md_content = record_to_md(record_id, fields)
        filepath = os.path.join(MEMORY_DIR, f"{record_id}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
        new_count += 1
        print(f"  + New: {record_id} - {get_text(fields.get('标题', ''))}")

    if new_count > 0:
        print(f"  Added {new_count} files, rebuilding index...")
        os.system(f"cd {os.path.expanduser('~/.openclaw')} && npx openclaw memory index --force 2>&1 | tail -5")
        print("  Index rebuilt")
    else:
        print("  No new records, skipping index rebuild")

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Sync complete")


if __name__ == "__main__":
    main()
