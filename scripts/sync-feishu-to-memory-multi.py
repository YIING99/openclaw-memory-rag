#!/usr/bin/env python3
"""
Feishu Bitable → memory/ directory sync script (multi-table version)

Syncs records from multiple Feishu Bitable tables into the memory/ directory.
Each table can have a different schema — the script handles field mapping per table.

Usage:
  1. Fill in the configuration section below
  2. Run manually: python3 sync-feishu-to-memory-multi.py
  3. Or set up as cron job: 30 */6 * * * /usr/bin/python3 $HOME/sync-feishu-to-memory-multi.py

Author: KING
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

# Define your tables here: { "table_id": "table_display_name" }
TABLES = {
    "YOUR_TABLE_ID_1": "Table One",
    "YOUR_TABLE_ID_2": "Table Two",
    "YOUR_TABLE_ID_3": "Table Three",
}

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


def list_records(token, table_id, page_token=None):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records?page_size=100"
    if page_token:
        url += f"&page_token={page_token}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_all_records(token, table_id):
    records = []
    page_token = None
    while True:
        result = list_records(token, table_id, page_token)
        if result.get("code") != 0:
            print(f"[ERROR] Failed to get records: {result}")
            return records
        items = result.get("data", {}).get("items") or []
        records.extend(items)
        if not result["data"].get("has_more"):
            break
        page_token = result["data"].get("page_token")
    return records


# === Field extraction ===
def get_text(val):
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, dict):
        return val.get("text", val.get("link", str(val)))
    return str(val)


def format_date(timestamp_ms):
    if not timestamp_ms:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        ts = int(timestamp_ms) / 1000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return datetime.now().strftime("%Y-%m-%d")


# === Record → Markdown converters ===

def primary_table_to_md(record_id, fields):
    """Convert a record from the primary table to markdown.

    Customize field names to match your primary table schema.
    This example uses fields like: 标题, 素材来源, 素材评级, 内容标签, etc.
    """
    title = get_text(fields.get("标题", "无标题"))
    source = get_text(fields.get("素材来源", ""))
    rating = get_text(fields.get("素材评级", ""))
    tags = get_text(fields.get("内容标签", ""))
    emotion = get_text(fields.get("情绪标签", ""))
    audience = get_text(fields.get("目标人群", ""))
    core_view = get_text(fields.get("核心观点", ""))
    quotes = get_text(fields.get("金句摘录", ""))
    topics = get_text(fields.get("适合选题方向", ""))
    date_str = format_date(fields.get("日期"))

    kw_set = set()
    if title:
        kw_set.add(title)
    for field_name in ["内容标签", "情绪标签", "目标人群"]:
        val = fields.get(field_name, [])
        if isinstance(val, list):
            for v in val:
                kw_set.add(str(v))

    lines = [
        f"## [{date_str}] {title}",
        f"- **来源**：Primary Table | **素材来源**：{source} | **评级**：{rating}",
        f"- **内容标签**：{tags} | **情绪标签**：{emotion}",
        f"- **目标人群**：{audience}",
        f"- **飞书记录**：{record_id}",
        "",
    ]
    if core_view:
        lines += [f"**核心观点**：{core_view}", ""]
    if quotes:
        lines += [f"**金句摘录**：{quotes}", ""]
    if topics:
        lines += [f"**适合选题方向**：{topics}", ""]
    if kw_set:
        lines += [f"**搜索关键词**：{', '.join(kw_set)}", ""]
    return "\n".join(lines)


def generic_table_to_md(record_id, fields, table_name):
    """Convert a record from any generic table to markdown.

    Automatically extracts title from common field names and dumps all fields.
    """
    title = ""
    for key in ["标题", "名称", "案例标题", "内容标题"]:
        if fields.get(key):
            title = get_text(fields[key])
            break
    if not title:
        for k, v in fields.items():
            t = get_text(v)
            if t and len(t) < 100:
                title = t
                break
    if not title:
        title = "Untitled"

    date_str = datetime.now().strftime("%Y-%m-%d")
    for key in ["日期", "创建时间", "时间"]:
        if fields.get(key):
            date_str = format_date(fields[key])
            break

    lines = [
        f"## [{date_str}] {title}",
        f"- **来源**：{table_name}",
        f"- **飞书记录**：{record_id}",
        "",
    ]
    for k, v in fields.items():
        text = get_text(v)
        if text and k not in ["标题", "名称", "日期", "创建时间"]:
            lines += [f"**{k}**：{text[:500]}", ""]

    kw_set = {title}
    for key in ["标签", "内容标签", "关键词"]:
        val = fields.get(key, [])
        if isinstance(val, list):
            for item in val:
                kw_set.add(str(item))
    if kw_set:
        lines += [f"**搜索关键词**：{', '.join(kw_set)}", ""]
    return "\n".join(lines)


# === Main ===
def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting multi-table Feishu → memory sync...")

    os.makedirs(MEMORY_DIR, exist_ok=True)
    existing_ids = set()
    for f in os.listdir(MEMORY_DIR):
        if f.startswith("rec") and f.endswith(".md"):
            existing_ids.add(f[:-3])
    print(f"  memory/ has {len(existing_ids)} existing knowledge files")

    token = get_tenant_token()
    total_new = 0

    # Customize: set your primary table name here
    PRIMARY_TABLE_NAME = "Table One"

    for table_id, table_name in TABLES.items():
        records = get_all_records(token, table_id)
        print(f"  {table_name} ({table_id}): {len(records)} records")

        for item in records:
            record_id = item.get("record_id", "")
            if not record_id or record_id in existing_ids:
                continue
            fields = item.get("fields", {})

            if table_name == PRIMARY_TABLE_NAME:
                md_content = primary_table_to_md(record_id, fields)
            else:
                md_content = generic_table_to_md(record_id, fields, table_name)

            filepath = os.path.join(MEMORY_DIR, f"{record_id}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            total_new += 1
            title = get_text(fields.get("标题", fields.get("名称", "?")))
            print(f"  + [{table_name}] {record_id} - {title}")

    if total_new > 0:
        print(f"  Added {total_new} files, rebuilding index...")
        os.system(f"cd {os.path.expanduser('~/.openclaw')} && npx openclaw memory index --force 2>&1 | tail -5")
        print("  Index rebuilt")
    else:
        print("  No new records, skipping index rebuild")

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Sync complete")


if __name__ == "__main__":
    main()
