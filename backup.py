#!/usr/bin/env python3
"""
Notion → Markdown backup.

Pulls every standalone page AND every data source row this integration has
access to. Updated for Notion API 2025-09-03. Captures page properties
(including relations to other databases) as a Properties section in each file.

- Standalone pages → backup/_pages/
- Data source rows → backup/<Source Name>/

Add data source names to EXCLUDED_DATABASES to skip them entirely.
"""

import os
import re
import shutil
from pathlib import Path
from notion_client import Client

# ---------- Config ----------

EXCLUDED_DATABASES = [
]

# ---------- Setup ----------

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
BACKUP_DIR = Path("backup")
notion = Client(auth=NOTION_TOKEN)

# Maps populated during the data sources pass.
_source_id_to_name = {}   # data_source_id / database_id -> source name
_row_id_to_title = {}     # row page_id -> title, used to resolve relations

# ---------- Helpers ----------

def safe_filename(text, max_len=80):
    text = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_len] or "untitled"

def rich_text_to_md(rich_text):
    out = []
    for rt in rich_text:
        text = rt.get("plain_text", "")
        ann = rt.get("annotations", {})
        if ann.get("code"):          text = f"`{text}`"
        if ann.get("bold"):          text = f"**{text}**"
        if ann.get("italic"):        text = f"*{text}*"
        if ann.get("strikethrough"): text = f"~~{text}~~"
        href = rt.get("href")
        if href:                     text = f"[{text}]({href})"
        out.append(text)
    return "".join(out)

def block_to_md(block):
    btype = block.get("type")
    data = block.get(btype, {})

    if btype == "paragraph":
        return rich_text_to_md(data.get("rich_text", []))
    if btype == "heading_1":
        return "# "  + rich_text_to_md(data.get("rich_text", []))
    if btype == "heading_2":
        return "## " + rich_text_to_md(data.get("rich_text", []))
    if btype == "heading_3":
        return "### " + rich_text_to_md(data.get("rich_text", []))
    if btype == "bulleted_list_item":
        return "- " + rich_text_to_md(data.get("rich_text", []))
    if btype == "numbered_list_item":
        return "1. " + rich_text_to_md(data.get("rich_text", []))
    if btype == "to_do":
        checked = "x" if data.get("checked") else " "
        return f"- [{checked}] " + rich_text_to_md(data.get("rich_text", []))
    if btype == "toggle":
        return "- " + rich_text_to_md(data.get("rich_text", []))
    if btype == "code":
        lang = data.get("language", "")
        text = "".join(rt.get("plain_text", "") for rt in data.get("rich_text", []))
        return f"```{lang}\n{text}\n```"
    if btype == "quote":
        return "> " + rich_text_to_md(data.get("rich_text", []))
    if btype == "callout":
        return "> " + rich_text_to_md(data.get("rich_text", []))
    if btype == "divider":
        return "---"
    if btype == "child_page":
        return f"📄 *Sub-page: {data.get('title', 'Untitled')}*"
    if btype == "child_database":
        block_id = block.get("id", "")
        name = _source_id_to_name.get(block_id)
        if not name:
            title = data.get("title", "").strip()
            if title and title.lower() != "untitled":
                name = title
        if name:
            return f"🗄️ **Linked database:** {name}"
        return f"🗄️ **Linked database** *(unresolved)*"
    return f"<!-- unsupported block: {btype} -->"

def get_all_blocks(block_id):
    blocks, cursor = [], None
    while True:
        resp = notion.blocks.children.list(block_id=block_id, start_cursor=cursor)
        blocks.extend(resp["results"])
        if not resp["has_more"]:
            break
        cursor = resp["next_cursor"]
    return blocks

def get_page_title(page):
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            rt = prop.get("title", [])
            if rt:
                return "".join(item.get("plain_text", "") for item in rt)
    return "Untitled"

def get_source_title(source):
    title_rt = source.get("title", [])
    if title_rt:
        return "".join(rt.get("plain_text", "") for rt in title_rt)
    return "Untitled"

# ---------- Properties → Markdown ----------

def relation_to_wikilink(row_id):
    """Render a related row as an Obsidian wikilink with display alias."""
    title = _row_id_to_title.get(row_id)
    if not title:
        return f"`{row_id[:8]}…` *(not in backup)*"
    safe_title = safe_filename(title)
    short_id = row_id.replace("-", "")[:8]
    # Obsidian: [[file (id)|display title]]
    return f"[[{safe_title} ({short_id})|{title}]]"

def format_property(prop):
    """Render one property's value as a Markdown string. Empty values return ''."""
    ptype = prop.get("type")

    if ptype == "rich_text":
        return rich_text_to_md(prop.get("rich_text", []))
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    if ptype == "multi_select":
        return ", ".join(item["name"] for item in prop.get("multi_select", []))
    if ptype == "status":
        st = prop.get("status")
        return st["name"] if st else ""
    if ptype == "number":
        n = prop.get("number")
        return str(n) if n is not None else ""
    if ptype == "checkbox":
        return "✓" if prop.get("checkbox") else "✗"
    if ptype == "date":
        d = prop.get("date")
        if not d: return ""
        start, end = d.get("start", ""), d.get("end", "")
        return f"{start} → {end}" if end else start
    if ptype == "url":
        return prop.get("url") or ""
    if ptype == "email":
        return prop.get("email") or ""
    if ptype == "phone_number":
        return prop.get("phone_number") or ""
    if ptype == "people":
        return ", ".join(p.get("name", "Unknown") for p in prop.get("people", []))
    if ptype == "files":
        return ", ".join(f.get("name", "file") for f in prop.get("files", []))
    if ptype == "created_time":
        return prop.get("created_time", "")
    if ptype == "last_edited_time":
        return prop.get("last_edited_time", "")
    if ptype == "created_by":
        return prop.get("created_by", {}).get("name", "")
    if ptype == "last_edited_by":
        return prop.get("last_edited_by", {}).get("name", "")
    if ptype == "relation":
        relations = prop.get("relation", [])
        if not relations:
            return ""
        return ", ".join(relation_to_wikilink(r.get("id", "")) for r in relations)
    if ptype == "formula":
        f = prop.get("formula", {})
        ftype = f.get("type")
        val = f.get(ftype) if ftype else None
        return str(val) if val is not None else ""
    if ptype == "rollup":
        r = prop.get("rollup", {})
        rtype = r.get("type")
        val = r.get(rtype) if rtype else None
        return str(val) if val is not None else ""
    return ""

def properties_to_md_lines(properties):
    """Return a list of '- **Name:** value' lines, skipping title and empty values."""
    lines = []
    for prop_name, prop_data in properties.items():
        if prop_data.get("type") == "title":
            continue
        value = format_property(prop_data)
        if value:
            lines.append(f"- **{prop_name}:** {value}")
    return lines

# ---------- Page rendering ----------

def page_to_markdown(page, source_database=None):
    title = get_page_title(page)
    blocks = get_all_blocks(page["id"])

    lines = [
        "---",
        f"notion_id: {page['id']}",
        f"created: {page.get('created_time', '')}",
        f"last_edited: {page.get('last_edited_time', '')}",
        f"url: {page.get('url', '')}",
    ]
    if source_database:
        lines.append(f'source_database: "{source_database}"')
    lines.extend(["---", "", f"# {title}", ""])

    # Properties section (includes relations as Obsidian wikilinks)
    prop_lines = properties_to_md_lines(page.get("properties", {}))
    if prop_lines:
        lines.append("## Properties")
        lines.append("")
        lines.extend(prop_lines)
        lines.append("")

    for block in blocks:
        md = block_to_md(block)
        if md:
            lines.append(md)
            lines.append("")
    return "\n".join(lines)

# ---------- Discovery (2025-09-03 API) ----------

def get_all_pages():
    pages, cursor = [], None
    while True:
        resp = notion.search(
            filter={"property": "object", "value": "page"},
            start_cursor=cursor,
        )
        pages.extend(resp["results"])
        if not resp["has_more"]:
            break
        cursor = resp["next_cursor"]
    return pages

def get_all_data_sources():
    sources, cursor = [], None
    while True:
        resp = notion.search(
            filter={"property": "object", "value": "data_source"},
            start_cursor=cursor,
        )
        sources.extend(resp["results"])
        if not resp["has_more"]:
            break
        cursor = resp["next_cursor"]
    return sources

def query_data_source_rows(data_source_id):
    rows, cursor = [], None
    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor
        resp = notion.request(
            path=f"data_sources/{data_source_id}/query",
            method="POST",
            body=body,
        )
        rows.extend(resp["results"])
        if not resp["has_more"]:
            break
        cursor = resp["next_cursor"]
    return rows

# ---------- Main ----------

def main():
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    BACKUP_DIR.mkdir()

    # --- Pass 1: Gather all data sources and rows, build title map ---
    print("Fetching data sources...")
    sources = get_all_data_sources()
    print(f"Found {len(sources)} data sources.\n")

    source_data = {}  # source_id -> {"name": str, "rows": list, "skipped": bool}
    for src in sources:
        name = get_source_title(src)
        _source_id_to_name[src["id"]] = name
        parent_db = src.get("parent", {}).get("database_id")
        if parent_db:
            _source_id_to_name[parent_db] = name

        if name in EXCLUDED_DATABASES:
            print(f"Will skip: {name}")
            source_data[src["id"]] = {"name": name, "rows": [], "skipped": True}
            continue

        print(f"Querying: {name}")
        try:
            rows = query_data_source_rows(src["id"])
            print(f"  {len(rows)} rows")
            source_data[src["id"]] = {"name": name, "rows": rows, "skipped": False}
            for row in rows:
                _row_id_to_title[row["id"]] = get_page_title(row)
        except Exception as e:
            print(f"  ERROR querying {name}: {e}")
            source_data[src["id"]] = {"name": name, "rows": [], "skipped": True}

    # --- Pass 2: Render rows (relations can now resolve to names) ---
    print(f"\n--- Rendering rows ---")
    processed_ids = set()
    rows_saved = rows_failed = sources_skipped = 0

    for src_id, info in source_data.items():
        if info["skipped"]:
            sources_skipped += 1
            continue
        name = info["name"]
        rows = info["rows"]
        subfolder = BACKUP_DIR / safe_filename(name)
        subfolder.mkdir(parents=True, exist_ok=True)

        for row in rows:
            try:
                processed_ids.add(row["id"])
                title = get_page_title(row)
                short_id = row["id"].replace("-", "")[:8]
                filename = f"{safe_filename(title)} ({short_id}).md"
                filepath = subfolder / filename
                filepath.write_text(page_to_markdown(row, name), encoding="utf-8")
                rows_saved += 1
            except Exception as e:
                print(f"  ERROR on row {row['id']}: {e}")
                rows_failed += 1

    # --- Pass 3: Standalone pages ---
    print(f"\nFetching standalone pages...")
    pages = get_all_pages()
    print(f"Found {len(pages)} pages.\n")

    pages_dir = BACKUP_DIR / "_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    page_saved = page_failed = page_dedup = 0
    for page in pages:
        if page["id"] in processed_ids:
            page_dedup += 1
            continue
        try:
            title = get_page_title(page)
            short_id = page["id"].replace("-", "")[:8]
            filename = f"{safe_filename(title)} ({short_id}).md"
            filepath = pages_dir / filename
            filepath.write_text(page_to_markdown(page, None), encoding="utf-8")
            page_saved += 1
        except Exception as e:
            print(f"  ERROR on page {page['id']}: {e}")
            page_failed += 1

    print(f"\n--- Summary ---")
    print(f"Data sources: {len(sources) - sources_skipped} processed, {sources_skipped} skipped.")
    print(f"Rows: {rows_saved} saved, {rows_failed} failed.")
    print(f"Pages: {page_saved} saved, {page_failed} failed, {page_dedup} deduped.")

if __name__ == "__main__":
    main()
