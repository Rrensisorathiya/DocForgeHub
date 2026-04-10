"""
restore_with_tables.py
Notion blocks ko properly markdown mein convert karta hai — tables included.
Run: python3 restore_with_tables.py
"""
import os, requests, time, sys, re
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

token = os.getenv('NOTION_TOKEN')
db_id = os.getenv('NOTION_DATABASE_ID', '').replace('-', '')

NOTION_API = "https://api.notion.com/v1"
HEADERS = {
    'Authorization': f'Bearer {token}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

# ── rich text helpers ─────────────────────────────────────────────────────

def get_plain(rich_text_list):
    return ''.join(rt.get('plain_text', '') for rt in (rich_text_list or []))

def get_markdown_text(rich_text_list):
    result = ''
    for rt in (rich_text_list or []):
        text = rt.get('plain_text', '')
        ann  = rt.get('annotations', {})
        if ann.get('code'):        text = f'`{text}`'
        if ann.get('bold') and ann.get('italic'): text = f'***{text}***'
        elif ann.get('bold'):      text = f'**{text}**'
        elif ann.get('italic'):    text = f'*{text}*'
        elif ann.get('strikethrough'): text = f'~~{text}~~'
        result += text
    return result

# ── fetch table rows (children of table block) ────────────────────────────

def fetch_table_rows(block_id):
    """Fetch table_row children of a table block."""
    rows = []
    url  = f"{NOTION_API}/blocks/{block_id}/children"
    has_more, cursor = True, None
    while has_more:
        params = {'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            for block in data.get('results', []):
                if block.get('type') == 'table_row':
                    cells = block.get('table_row', {}).get('cells', [])
                    row   = [get_plain(cell) for cell in cells]
                    rows.append(row)
            has_more = data.get('has_more', False)
            cursor   = data.get('next_cursor')
        except Exception as e:
            print(f"      Table row fetch error: {e}")
            break
    return rows

def table_rows_to_markdown(rows):
    """Convert list of row lists to markdown table string."""
    if not rows:
        return ''
    
    # Calculate column widths
    col_count = max(len(r) for r in rows)
    
    # Pad rows
    padded = [row + [''] * (col_count - len(row)) for row in rows]
    
    lines = []
    for i, row in enumerate(padded):
        line = '| ' + ' | '.join(cell.replace('|', '\\|') for cell in row) + ' |'
        lines.append(line)
        if i == 0:
            # Add separator after header row
            sep = '| ' + ' | '.join(['---'] * col_count) + ' |'
            lines.append(sep)
    
    return '\n'.join(lines)

# ── fetch all blocks as proper markdown ───────────────────────────────────

def fetch_blocks_as_markdown(page_id):
    """Fetch all blocks from a Notion page and convert to clean markdown."""
    result_lines = []
    url          = f"{NOTION_API}/blocks/{page_id}/children"
    has_more     = True
    cursor       = None

    while has_more:
        params = {'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=20)
            if r.status_code != 200:
                break
            data = r.json()

            for block in data.get('results', []):
                btype   = block.get('type', '')
                block_id= block.get('id', '')
                bdata   = block.get(btype, {})
                rich    = bdata.get('rich_text', [])
                text    = get_markdown_text(rich)
                plain   = get_plain(rich)

                # ── Headings ──────────────────────────────────────────
                if btype == 'heading_1':
                    result_lines.append(f'\n# {plain}\n')

                elif btype == 'heading_2':
                    result_lines.append(f'\n## {plain}\n')

                elif btype == 'heading_3':
                    result_lines.append(f'\n### {plain}\n')

                # ── Paragraph ─────────────────────────────────────────
                elif btype == 'paragraph':
                    if text.strip():
                        result_lines.append(f'{text}')
                    else:
                        result_lines.append('')

                # ── Lists ─────────────────────────────────────────────
                elif btype == 'bulleted_list_item':
                    result_lines.append(f'- {text}')

                elif btype == 'numbered_list_item':
                    result_lines.append(f'1. {text}')

                elif btype == 'to_do':
                    checked = '✅' if bdata.get('checked') else '⬜'
                    result_lines.append(f'{checked} {text}')

                # ── Table — fetch children separately ─────────────────
                elif btype == 'table':
                    print(f"      Fetching table ({block_id[:8]}…)…", end=' ')
                    rows = fetch_table_rows(block_id)
                    if rows:
                        md_table = table_rows_to_markdown(rows)
                        result_lines.append('')
                        result_lines.append(md_table)
                        result_lines.append('')
                        print(f"{len(rows)} rows ✅")
                    else:
                        print("empty ⚠️")
                    time.sleep(0.1)

                # ── Skip table_row (already handled above) ────────────
                elif btype == 'table_row':
                    continue

                # ── Divider ───────────────────────────────────────────
                elif btype == 'divider':
                    result_lines.append('\n---\n')

                # ── Quote ─────────────────────────────────────────────
                elif btype == 'quote':
                    result_lines.append(f'> {text}')

                # ── Code ──────────────────────────────────────────────
                elif btype == 'code':
                    lang = bdata.get('language', '')
                    result_lines.append(f'```{lang}\n{plain}\n```')

                # ── Callout ───────────────────────────────────────────
                elif btype == 'callout':
                    emoji = bdata.get('icon', {}).get('emoji', '📌')
                    result_lines.append(f'> {emoji} {text}')

                # ── Fallback ──────────────────────────────────────────
                else:
                    if plain.strip():
                        result_lines.append(plain)

            has_more = data.get('has_more', False)
            cursor   = data.get('next_cursor')

        except Exception as e:
            print(f"\n    Block fetch error: {e}")
            break

    content = '\n'.join(result_lines)
    # Clean up excessive blank lines
    content = re.sub(r'\n{4,}', '\n\n', content)
    return content.strip()

# ── property helpers ──────────────────────────────────────────────────────

def get_title(props):
    t = props.get('Title', {}).get('title', [])
    return t[0].get('plain_text', '') if t else ''

def get_select(props, key):
    s = props.get(key, {}).get('select')
    return s.get('name', '') if s else ''

# ── MAIN ──────────────────────────────────────────────────────────────────

print("=" * 60)
print("  DocForgeHub — Restore with Tables")
print("=" * 60)

# Step 1: Fetch all pages
print("\nStep 1: Fetching all Notion pages...")
all_pages = []
has_more, cursor = True, None

while has_more:
    payload = {'page_size': 100}
    if cursor:
        payload['start_cursor'] = cursor
    r = requests.post(
        f"{NOTION_API}/databases/{db_id}/query",
        headers=HEADERS, json=payload, timeout=20
    )
    data     = r.json()
    all_pages.extend(data.get('results', []))
    has_more = data.get('has_more', False)
    cursor   = data.get('next_cursor')

print(f"  Found {len(all_pages)} pages")

# Step 2: Clear old restored docs
print("\nStep 2: Clearing old notion-restored docs...")
conn = get_connection()
cur  = conn.cursor()
cur.execute("DELETE FROM generated_documents WHERE notion_published = TRUE")
deleted = cur.rowcount
conn.commit()
print(f"  Deleted {deleted} old docs")

# Step 3: Restore with proper markdown + tables
print("\nStep 3: Restoring with proper markdown + tables...")
restored = 0
skipped  = 0
failed   = 0

for i, page in enumerate(all_pages):
    try:
        props    = page.get('properties', {})
        page_id  = page['id']
        title    = get_title(props)
        dept     = get_select(props, 'Department')
        doc_type = get_select(props, 'Document Type')
        industry = get_select(props, 'Industry')
        created  = page.get('created_time', '')[:10] or None

        print(f"\n[{i+1}/{len(all_pages)}] {doc_type or title[:50]}")

        content = fetch_blocks_as_markdown(page_id)

        if not content.strip():
            print(f"  ⚠️  No content — skipping")
            skipped += 1
            time.sleep(0.1)
            continue

        notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"

        cur.execute("""
            INSERT INTO generated_documents
                (document_type, department, industry, generated_content,
                 status, notion_page_id, notion_published, notion_url,
                 notion_version, created_at)
            VALUES (%s, %s, %s, %s, 'completed', %s, TRUE, %s, 1,
                    COALESCE(%s::timestamp, CURRENT_TIMESTAMP))
        """, (
            doc_type or title,
            dept, industry, content,
            page_id, notion_url, created,
        ))

        # Check if tables present
        table_count = content.count('| --- |')
        print(f"  ✅ {len(content)} chars, {table_count} tables")
        restored += 1
        time.sleep(0.15)

    except Exception as e:
        print(f"  ❌ Error: {e}")
        failed += 1

conn.commit()
cur.close()
conn.close()

# Verify
print(f"\n{'='*60}")
print(f"✅ Restored : {restored}")
print(f"⚠️  Skipped  : {skipped}")
print(f"❌ Failed   : {failed}")

conn2 = get_connection()
cur2  = conn2.cursor()
cur2.execute("SELECT COUNT(*) FROM generated_documents")
print(f"Total in DB: {cur2.fetchone()[0]}")
cur2.execute("""
    SELECT department, COUNT(*) 
    FROM generated_documents 
    GROUP BY department 
    ORDER BY COUNT(*) DESC
""")
for dept, cnt in cur2.fetchall():
    print(f"  {str(dept):<45} {cnt} docs")
cur2.close()
conn2.close()
print("=" * 60)