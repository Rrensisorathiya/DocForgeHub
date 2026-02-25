import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import re
import requests
from typing import Optional

# ============================================================
# CONFIG
# ============================================================
API_BASE_URL   = "http://127.0.0.1:8000"
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# ============================================================
# API HELPERS
# ============================================================
def api_get(endpoint: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Run: `python -m uvicorn main:app --reload`")
        return None
    except Exception as e:
        st.error(f"❌ API Error: {str(e)}")
        return None

def api_post(endpoint: str, data: dict):
    try:
        r = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=180)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend.")
        return None
    except requests.exceptions.HTTPError:
        st.error(f"❌ API Error {r.status_code}: {r.text}")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def api_delete(endpoint: str):
    try:
        r = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Delete failed: {str(e)}")
        return None

def fetch_file(document_id, fmt: str) -> bytes:
    """Download .docx or .pdf bytes from FastAPI export router."""
    try:
        r = requests.get(
            f"{API_BASE_URL}/export/{document_id}/{fmt}",
            timeout=30
        )
        if r.status_code == 200:
            return r.content
        st.error(f"❌ Export failed ({fmt}): {r.text[:200]}")
        return None
    except Exception as e:
        st.error(f"❌ Export error: {str(e)}")
        return None

def to_markdown(doc: dict) -> str:
    header = (
        f"---\n"
        f"Type       : {doc.get('document_type','')}\n"
        f"Department : {doc.get('department','')}\n"
        f"Industry   : {doc.get('industry','')}\n"
        f"Date       : {doc.get('created_at','')[:16]}\n"
        f"---\n\n"
    )
    return header + doc.get("generated_content", "")

def safe_fname(doc_type: str, department: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_',
                  f"{doc_type}_{department}")

# ============================================================
# NOTION HELPERS
# ============================================================
def notion_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

def notion_test(token):
    try:
        r = requests.get(f"{NOTION_API_URL}/users/me",
                         headers=notion_headers(token), timeout=10)
        return r.status_code == 200, r.json()
    except Exception as e:
        return False, str(e)

def notion_databases(token):
    try:
        r = requests.post(f"{NOTION_API_URL}/search",
                          headers=notion_headers(token),
                          json={"filter": {"value": "database", "property": "object"}},
                          timeout=10)
        if r.status_code == 200:
            return [{"id": db["id"],
                     "name": (db.get("title") or [{}])[0].get("plain_text", "Untitled")}
                    for db in r.json().get("results", [])]
        return []
    except Exception:
        return []

def notion_publish(token, database_id, doc, content):
    def para(text):
        return {"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]}}
    def heading(text, level=2):
        ht = f"heading_{level}"
        return {"object": "block", "type": ht,
                ht: {"rich_text": [{"type": "text", "text": {"content": text[:100]}}]}}

    blocks = [para(f"Department: {doc.get('department','')}  |  Industry: {doc.get('industry','')}  |  ID: {doc.get('id','')}")]
    for line in content.split("\n"):
        if not line.strip(): continue
        if line.startswith("# "):   blocks.append(heading(line[2:], 1))
        elif line.startswith("## "): blocks.append(heading(line[3:], 2))
        elif line.startswith("### "): blocks.append(heading(line[4:], 3))
        else:
            for chunk in range(0, len(line), 1999):
                blocks.append(para(line[chunk:chunk+1999]))
        if len(blocks) >= 95: break

    payload = {
        "parent": {"database_id": database_id},
        "properties": {"Name": {"title": [{"text": {"content": f"{doc.get('document_type','')} — {doc.get('department','')}"}}]}},
        "children": blocks[:95],
    }
    try:
        r = requests.post(f"{NOTION_API_URL}/pages",
                          headers=notion_headers(token), json=payload, timeout=30)
        if r.status_code == 200:
            page = r.json()
            return True, page.get("url", ""), page.get("id", "")
        return False, r.text, ""
    except Exception as e:
        return False, str(e), ""

# ============================================================
# PAGE CONFIG & CSS
# ============================================================
st.set_page_config(
    page_title="DocForgeHub",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#1e3c72 0%,#2a5298 100%); }
    .main-header { font-size:2.2rem; font-weight:700; color:#1e3c72; text-align:center; margin-bottom:8px; }
    .sub-header  { font-size:1.5rem; font-weight:600; color:#2a5298; border-bottom:3px solid #4CAF50; padding-bottom:8px; margin:25px 0 15px; }
    .stat-box    { background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:18px; border-radius:12px; text-align:center; }
    .stat-number { font-size:2rem; font-weight:700; }
    .stat-label  { font-size:0.8rem; opacity:.9; text-transform:uppercase; letter-spacing:1px; }
    .doc-card    { background:white; padding:18px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.08); margin-bottom:12px; border:2px solid #e0e0e0; }
    .doc-card:hover { border-color:#4CAF50; }
    .custom-card { background:white; padding:22px; border-radius:14px; box-shadow:0 3px 8px rgba(0,0,0,.1); margin-bottom:18px; border-left:5px solid #4CAF50; }
    .success-box { background:linear-gradient(135deg,#11998e,#38ef7d); color:white; padding:18px; border-radius:12px; margin:15px 0; text-align:center; font-weight:600; }
    .info-box    { background:linear-gradient(135deg,#4facfe,#00f2fe); color:white; padding:18px; border-radius:12px; margin:15px 0; }
    .q-block     { background:#f8f9ff; border-left:4px solid #667eea; padding:12px 18px; border-radius:8px; margin-bottom:12px; }
    .badge-type  { background:linear-gradient(135deg,#f093fb,#f5576c); color:white; padding:4px 14px; border-radius:20px; font-size:.8rem; font-weight:600; display:inline-block; }
    .badge-done  { background:#4CAF50; color:white; padding:4px 12px; border-radius:14px; font-size:.8rem; font-weight:600; }
    .badge-draft { background:#FF9800; color:white; padding:4px 12px; border-radius:14px; font-size:.8rem; font-weight:600; }
    .divider     { height:3px; background:linear-gradient(90deg,#667eea,#764ba2); border:none; margin:25px 0; border-radius:5px; }
    .stButton>button { background:linear-gradient(135deg,#667eea,#764ba2); color:white; border:none; border-radius:8px; padding:10px 28px; font-weight:600; box-shadow:0 3px 8px rgba(0,0,0,.2); }
    .dl-box { background:#f0f4ff; border:2px solid #667eea; border-radius:12px; padding:20px; margin:15px 0; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
def init_session():
    for k, v in {
        "page": "Home",
        "gen_step": 1,
        "sel_industry": "SaaS",
        "sel_dept": None,
        "sel_type": None,
        "qa": {},
        "last_doc": None,
        "notion_published": {},
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ============================================================
# CACHED API CALLS
# ============================================================
@st.cache_data(ttl=300)
def get_departments():
    data = api_get("/templates/departments")
    if data: return data.get("departments", [])
    return ["HR & People Operations","Legal & Compliance","Sales & Customer-Facing",
            "Engineering & Operations","Product & Design","Marketing & Content",
            "Finance & Operations","Partnership & Alliances","IT & Internal Systems",
            "Platform & Infrastructure Operation","Data & Analytics",
            "QA & Testing","Security & Information Assurance"]

@st.cache_data(ttl=300)
def get_doc_types():
    data = api_get("/templates/document-types")
    if data: return data.get("document_types", [])
    return ["SOP","Policy","Proposal","SOW","Incident Report",
            "FAQ","Runbook","Playbook","RCA","SLA","Change Management","Handbook"]

@st.cache_data(ttl=300)
def get_questions(dept, doc_type):
    data = api_get("/questionnaires/by-type", params={"department": dept, "document_type": doc_type})
    if data and "questions" in data: return data["questions"]
    return []

@st.cache_data(ttl=60)
def get_stats():
    return api_get("/system/stats")

@st.cache_data(ttl=30)
def get_docs(dept=None, dtype=None):
    params = {}
    if dept:  params["department"]   = dept
    if dtype: params["document_type"] = dtype
    return api_get("/documents/", params=params) or []

# ============================================================
# REUSABLE DOWNLOAD WIDGET
# ============================================================
def render_download_buttons(document_id, doc_type: str, department: str, full_doc: dict = None, key_prefix: str = "dl"):
    """Render Word, PDF, Markdown download buttons for a document."""
    fname = safe_fname(doc_type, department)

    st.markdown("<div class='dl-box'>", unsafe_allow_html=True)
    st.markdown("**⬇️ Download this document:**", unsafe_allow_html=False)

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📘 Prepare Word (.docx)", key=f"{key_prefix}_prep_docx_{document_id}", use_container_width=True):
            st.session_state[f"{key_prefix}_fetch_docx_{document_id}"] = True

        if st.session_state.get(f"{key_prefix}_fetch_docx_{document_id}"):
            with st.spinner("Generating Word file..."):
                data = fetch_file(document_id, "docx")
            if data:
                st.download_button(
                    label="⬇️ Click to Download .docx",
                    data=data,
                    file_name=f"{fname}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"{key_prefix}_docx_{document_id}",
                    use_container_width=True,
                )

    with c2:
        if st.button("📕 Prepare PDF (.pdf)", key=f"{key_prefix}_prep_pdf_{document_id}", use_container_width=True):
            st.session_state[f"{key_prefix}_fetch_pdf_{document_id}"] = True

        if st.session_state.get(f"{key_prefix}_fetch_pdf_{document_id}"):
            with st.spinner("Generating PDF file..."):
                data = fetch_file(document_id, "pdf")
            if data:
                st.download_button(
                    label="⬇️ Click to Download .pdf",
                    data=data,
                    file_name=f"{fname}.pdf",
                    mime="application/pdf",
                    key=f"{key_prefix}_pdf_{document_id}",
                    use_container_width=True,
                )

    with c3:
        if full_doc is None:
            full_doc = api_get(f"/documents/{document_id}")
        if full_doc:
            st.download_button(
                label="📄 Download Markdown (.md)",
                data=to_markdown(full_doc),
                file_name=f"{fname}.md",
                mime="text/markdown",
                key=f"{key_prefix}_md_{document_id}",
                use_container_width=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("<h1 style='color:white;text-align:center;margin-bottom:15px;'>📄 DocForgeHub</h1>", unsafe_allow_html=True)
        health = api_get("/system/health")
        if health and health.get("database") == "connected":
            st.markdown("<div style='background:#4CAF50;padding:7px;border-radius:8px;text-align:center;color:white;font-size:.85rem;margin-bottom:12px;'>🟢 Backend Connected</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:#f44336;padding:7px;border-radius:8px;text-align:center;color:white;font-size:.85rem;margin-bottom:12px;'>🔴 Backend Offline</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);'>", unsafe_allow_html=True)

        pages = {"🏠 Home":"Home","✨ Generate":"Generate","📚 Library":"Library",
                 "🗂 Templates":"Templates","❓ Questionnaires":"Questionnaires",
                 "🚀 Publish to Notion":"Notion","📊 Stats":"Stats"}
        for label, key in pages.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()

        st.markdown("<hr style='border:1px solid rgba(255,255,255,.3);margin:15px 0;'>", unsafe_allow_html=True)
        stats = get_stats()
        if stats:
            st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
            st.metric("Templates",  stats.get("templates", 0))
            st.metric("Documents",  stats.get("documents_generated", 0))
            st.metric("Jobs Done",  stats.get("jobs_completed", 0))

        st.markdown("<div style='color:rgba(255,255,255,.6);text-align:center;font-size:.75rem;margin-top:25px;'>Powered by Azure OpenAI + LangChain<br>© 2026 DocForgeHub</div>", unsafe_allow_html=True)

# ============================================================
# PAGE: HOME
# ============================================================
def page_home():
    st.markdown("<h1 class='main-header'>🚀 Welcome to DocForgeHub</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;font-size:1.1rem;color:#555;'>AI-Powered Enterprise Document Generation — PostgreSQL + Azure OpenAI</p>", unsafe_allow_html=True)

    stats = get_stats()
    c1,c2,c3,c4 = st.columns(4)
    for col, num, label in [
        (c1, stats.get("templates",0) if stats else 0, "Templates"),
        (c2, stats.get("documents_generated",0) if stats else 0, "Documents"),
        (c3, stats.get("departments",0) if stats else 0, "Departments"),
        (c4, stats.get("document_types",0) if stats else 0, "Doc Types"),
    ]:
        with col:
            st.markdown(f"<div class='stat-box'><div class='stat-number'>{num}</div><div class='stat-label'>{label}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1: st.markdown("<div class='custom-card'><h3 style='color:#1e3c72;'>🤖 AI Generation</h3><p>Azure OpenAI + LangChain generates professional documents with your company context.</p></div>", unsafe_allow_html=True)
    with c2: st.markdown("<div class='custom-card' style='border-left-color:#764ba2'><h3 style='color:#1e3c72;'>🗄️ PostgreSQL Backend</h3><p>All templates, questionnaires, and documents stored in your PostgreSQL database.</p></div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='custom-card' style='border-left-color:#4facfe'><h3 style='color:#1e3c72;'>📥 Export Formats</h3><p>Download as Word (.docx), PDF (.pdf), or Markdown (.md) with one click.</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("✨ Generate New Document", use_container_width=True):
            st.session_state.page = "Generate"; st.session_state.gen_step = 1; st.rerun()
    with c2:
        if st.button("📚 View Document Library", use_container_width=True):
            st.session_state.page = "Library"; st.rerun()

    docs = get_docs()
    if docs:
        st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
        for doc in docs[:5]:
            badge = "badge-done" if doc["status"]=="completed" else "badge-draft"
            st.markdown(f"<div class='doc-card'><b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']} | {doc['department']}</b><br><span style='color:#999;font-size:.85rem;'>📅 {doc['created_at'][:16]}</span> <span class='{badge}'>{doc['status'].upper()}</span></div>", unsafe_allow_html=True)

# ============================================================
# PAGE: GENERATE
# ============================================================
def page_generate():
    st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)

    step = st.session_state.gen_step
    st.progress((step-1)/3)
    labels = ["📋 Select Type","❓ Answer Questions","🎉 Generate & Review"]
    cols = st.columns(3)
    for i,(col,lbl) in enumerate(zip(cols,labels)):
        with col:
            if i+1 < step: st.markdown(f"<p style='text-align:center;color:#4CAF50;font-weight:600;'>✅ {lbl}</p>", unsafe_allow_html=True)
            elif i+1 == step: st.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>▶️ {lbl}</p>", unsafe_allow_html=True)
            else: st.markdown(f"<p style='text-align:center;color:#999;'>⏺️ {lbl}</p>", unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # STEP 1
    if step == 1:
        st.markdown("<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True)
        depts = get_departments(); dtypes = get_doc_types()
        c1,c2,c3 = st.columns(3)
        with c1: industry = st.selectbox("🏢 Industry", ["SaaS"], key="s1_ind")
        with c2: dept     = st.selectbox("🏛️ Department", depts, key="s1_dept")
        with c3: dtype    = st.selectbox("📄 Document Type", dtypes, key="s1_type")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➡️ Next: Answer Questions", use_container_width=True):
            st.session_state.sel_industry = industry
            st.session_state.sel_dept     = dept
            st.session_state.sel_type     = dtype
            st.session_state.gen_step     = 2
            st.rerun()

    # STEP 2
    elif step == 2:
        st.markdown("<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True)
        dept  = st.session_state.sel_dept
        dtype = st.session_state.sel_type
        st.markdown(f"<div class='info-box'><b>Generating:</b> {dtype} for <b>{dept}</b></div>", unsafe_allow_html=True)

        questions = get_questions(dept, dtype)
        if not questions:
            questions = [
                {"id":"company_name",     "question":"Company name?",              "type":"text",     "required":True,  "options":[],"category":"common"},
                {"id":"company_size",     "question":"Company size?",              "type":"select",   "required":True,  "options":["1-10","11-50","51-200","201-500","1000+"],"category":"common"},
                {"id":"primary_product",  "question":"Primary SaaS product?",      "type":"text",     "required":True,  "options":[],"category":"common"},
                {"id":"tools_used",       "question":"Tools/systems used?",        "type":"text",     "required":False, "options":[],"category":"common"},
                {"id":"specific_focus",   "question":"Specific topic to cover?",   "type":"text",     "required":False, "options":[],"category":"common"},
                {"id":"tone_preference",  "question":"Preferred tone?",            "type":"select",   "required":False, "options":["Professional & Formal","Professional & Friendly","Technical & Detailed","Executive-level & Concise"],"category":"common"},
                {"id":"compliance_requirements","question":"Compliance requirements?","type":"text",  "required":False, "options":[],"category":"common"},
                {"id":"additional_context","question":"Any additional context?",   "type":"textarea", "required":False, "options":[],"category":"common"},
            ]

        answers = {}
        cats = {}
        for q in questions:
            cats.setdefault(q.get("category","common"), []).append(q)

        cat_labels = {
            "common": "📋 General Questions",
            "document_type_specific": f"📄 {dtype} Specific",
            "department_specific": f"🏛️ {dept} Specific",
        }

        for cat, qs in cats.items():
            if qs:
                st.markdown(f"<h3 style='color:#2a5298;margin-top:20px;'>{cat_labels.get(cat,cat)}</h3>", unsafe_allow_html=True)
                for q in qs:
                    qid  = q.get("id","")
                    qtext= q.get("question","")
                    qtype= q.get("type","text")
                    qreq = q.get("required",False)
                    qopts= q.get("options",[])
                    label= f"{'🔴 ' if qreq else ''}{qtext}"
                    st.markdown(f"<div class='q-block'><b style='color:#1e3c72;'>{label}</b></div>", unsafe_allow_html=True)
                    wkey = f"qa_{qid}"
                    if qtype == "text":
                        answers[qid] = st.text_input("", key=wkey, label_visibility="collapsed")
                    elif qtype == "textarea":
                        answers[qid] = st.text_area("", key=wkey, height=90, label_visibility="collapsed")
                    elif qtype == "select" and qopts:
                        answers[qid] = st.selectbox("", ["(select)"]+qopts, key=wkey, label_visibility="collapsed")
                    elif qtype in ("multi_select","multiselect") and qopts:
                        answers[qid] = st.multiselect("", qopts, key=wkey, label_visibility="collapsed")
                    else:
                        answers[qid] = st.text_input("", key=wkey, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.gen_step = 1; st.rerun()
        with c2:
            if st.button("🚀 Generate Document", use_container_width=True):
                missing = [q.get("question","") for q in questions if q.get("required") and not answers.get(q.get("id",""))]
                if missing:
                    for m in missing: st.error(f"Required: {m}")
                else:
                    clean = {k:v for k,v in answers.items() if v and v != "(select)"}
                    st.session_state.qa       = clean
                    st.session_state.gen_step = 3
                    st.rerun()

    # STEP 3
    elif step == 3:
        st.markdown("<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True)

        if st.session_state.last_doc is None:
            pb = st.progress(0); status = st.empty()
            phases = [
                ("Connecting to FastAPI...", .15),
                ("Loading template from DB...", .30),
                ("Loading questionnaire...", .45),
                ("Building AI prompt...", .60),
                ("Calling Azure OpenAI...", .80),
                ("Saving to database...", .95),
            ]
            for txt, pct in phases:
                status.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>{txt}</p>", unsafe_allow_html=True)
                pb.progress(pct); time.sleep(0.4)

            result = api_post("/documents/generate", {
                "industry":         st.session_state.sel_industry,
                "department":       st.session_state.sel_dept,
                "document_type":    st.session_state.sel_type,
                "question_answers": st.session_state.qa,
            })
            pb.progress(1.0); status.empty(); pb.empty()

            if result:
                st.session_state.last_doc = result
            else:
                st.error("Document generation failed. Check FastAPI logs.")
                if st.button("⬅️ Try Again"):
                    st.session_state.gen_step = 2; st.rerun()
                return

        doc      = st.session_state.last_doc
        doc_id   = doc.get("document_id")
        v        = doc.get("validation", {})
        score    = v.get("score", 0)
        grade    = v.get("grade", "N/A")
        wc       = v.get("word_count", 0)

        st.markdown(f"<div class='success-box'>✅ Document Generated! ID: {doc_id} | Job: {doc.get('job_id','')[:8]}...</div>", unsafe_allow_html=True)

        # Validation report
        st.markdown("<h3 style='color:#1e3c72;margin-top:20px;'>📊 Quality Report</h3>", unsafe_allow_html=True)
        score_color = "#4CAF50" if score>=75 else "#FF9800" if score>=60 else "#f44336"
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(f"<div style='background:{score_color};padding:14px;border-radius:10px;text-align:center;color:white;'><div style='font-size:1.8rem;font-weight:700;'>{score}/100</div><div style='font-size:.8rem;'>Quality Score</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div style='background:{score_color};padding:14px;border-radius:10px;text-align:center;color:white;'><div style='font-size:1.8rem;font-weight:700;'>{grade}</div><div style='font-size:.8rem;'>Grade</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='stat-box'><div class='stat-number'>{wc:,}</div><div class='stat-label'>Words</div></div>", unsafe_allow_html=True)
        with c4:
            pc = len(v.get("passed",[])); ic = len(v.get("issues",[]))
            st.markdown(f"<div class='stat-box'><div class='stat-number'>{pc}✅ {ic}❌</div><div class='stat-label'>Checks</div></div>", unsafe_allow_html=True)

        if v.get("passed") or v.get("warnings") or v.get("issues"):
            ca, cb, cc = st.columns(3)
            with ca:
                if v.get("passed"):
                    st.markdown("**✅ Passed**")
                    for p in v["passed"]: st.markdown(f"<span style='color:#4CAF50;font-size:.85rem;'>{p}</span>", unsafe_allow_html=True)
            with cb:
                if v.get("warnings"):
                    st.markdown("**⚠️ Warnings**")
                    for w in v["warnings"]: st.markdown(f"<span style='color:#FF9800;font-size:.85rem;'>{w}</span>", unsafe_allow_html=True)
            with cc:
                st.markdown("**❌ Issues**")
                if v.get("issues"):
                    for i in v["issues"]: st.markdown(f"<span style='color:#f44336;font-size:.85rem;'>{i}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#4CAF50;font-size:.85rem;'>None!</span>", unsafe_allow_html=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Document preview
        st.markdown("<h3 style='color:#1e3c72;'>📄 Document Preview</h3>", unsafe_allow_html=True)
        st.markdown(f"<div class='doc-card'><span class='badge-type'>{st.session_state.sel_type}</span> &nbsp; <b style='color:#1e3c72;'>{st.session_state.sel_dept}</b><br><span style='color:#999;font-size:.85rem;'>ID: {doc_id}</span></div>", unsafe_allow_html=True)

        with st.expander("📖 View Full Generated Content", expanded=True):
            st.markdown(doc.get("document","No content."))

        with st.expander("📋 Your Submitted Answers"):
            st.json(st.session_state.qa)

        # ── DOWNLOAD BUTTONS ──
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        full_doc = api_get(f"/documents/{doc_id}")
        render_download_buttons(doc_id, st.session_state.sel_type,
                                st.session_state.sel_dept, full_doc, key_prefix="gen")

        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            if st.button("🔄 Generate Another", use_container_width=True):
                st.session_state.gen_step = 1
                st.session_state.last_doc = None
                st.session_state.qa = {}
                st.rerun()
        with c2:
            if st.button("📚 Go to Library", use_container_width=True):
                st.session_state.page = "Library"
                st.session_state.gen_step = 1
                st.session_state.last_doc = None
                st.rerun()

# ============================================================
# PAGE: LIBRARY
# ============================================================
def page_library():
    st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)

    depts  = get_departments()
    dtypes = get_doc_types()
    c1,c2,c3 = st.columns(3)
    with c1: f_dept  = st.selectbox("Filter Department",     ["All"]+depts,  key="lib_d")
    with c2: f_type  = st.selectbox("Filter Document Type",  ["All"]+dtypes, key="lib_t")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            get_docs.clear(); st.rerun()

    docs = get_docs(
        dept =f_dept  if f_dept  != "All" else None,
        dtype=f_type  if f_type  != "All" else None,
    )
    st.markdown(f"<p style='color:#666;'><b>{len(docs)}</b> documents found</p>", unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if not docs:
        st.markdown("<div class='info-box'><h3>📭 No Documents</h3><p>Generate your first document.</p></div>", unsafe_allow_html=True)
        if st.button("✨ Generate Document", use_container_width=True):
            st.session_state.page = "Generate"; st.rerun()
        return

    for doc in docs:
        doc_id = str(doc["id"])
        badge  = "badge-done" if doc["status"]=="completed" else "badge-draft"
        st.markdown(f"""
        <div class='doc-card'>
            <b style='color:#1e3c72;font-size:1.05rem;'>#{doc['id']} — {doc['document_type']}</b><br>
            <span style='color:#666;'>🏛️ {doc['department']} | 🏢 {doc['industry']}</span><br>
            <span style='color:#999;font-size:.85rem;'>📅 {doc['created_at'][:16]}</span>
            <span class='{badge}' style='margin-left:10px;'>{doc['status'].upper()}</span>
        </div>""", unsafe_allow_html=True)

        c1,c2,c3 = st.columns([3,1,1])
        with c1:
            if st.button(f"📖 View #{doc['id']}", key=f"view_{doc_id}", use_container_width=True):
                full = api_get(f"/documents/{doc['id']}")
                if full:
                    with st.expander(f"📄 Document #{doc['id']} — Full View", expanded=True):
                        meta = full.get("metadata",{})
                        st.markdown(f"**Type:** {full['document_type']} | **Dept:** {full['department']} | **Words:** {meta.get('word_count','N/A')}")
                        st.markdown("---")
                        st.markdown(full.get("generated_content","No content"))

        with c2:
            # Download button (opens download section)
            if st.button(f"⬇️ Download #{doc['id']}", key=f"dl_toggle_{doc_id}", use_container_width=True):
                st.session_state[f"show_dl_{doc_id}"] = not st.session_state.get(f"show_dl_{doc_id}", False)

        with c3:
            if st.button(f"🗑️ Delete #{doc['id']}", key=f"del_{doc_id}", use_container_width=True):
                if api_delete(f"/documents/{doc['id']}"):
                    st.success("Deleted!")
                    get_docs.clear(); time.sleep(1); st.rerun()

        # Download section (shown when toggled)
        if st.session_state.get(f"show_dl_{doc_id}"):
            render_download_buttons(doc["id"], doc["document_type"],
                                    doc["department"], key_prefix=f"lib_{doc_id}")

# ============================================================
# PAGE: TEMPLATES
# ============================================================
def page_templates():
    st.markdown("<h1 class='main-header'>🗂 Templates</h1>", unsafe_allow_html=True)
    depts  = get_departments(); dtypes = get_doc_types()
    c1,c2 = st.columns(2)
    with c1: fd = st.selectbox("Department",     ["All"]+depts,  key="t_d")
    with c2: ft = st.selectbox("Document Type",  ["All"]+dtypes, key="t_t")

    params = {}
    if fd!="All": params["department"]   = fd
    if ft!="All": params["document_type"] = ft
    templates = api_get("/templates/", params=params) or []

    st.markdown(f"<p style='color:#666;'><b>{len(templates)}</b> templates</p>", unsafe_allow_html=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    for tmpl in templates:
        with st.expander(f"🗂 {tmpl['department']} — {tmpl['document_type']}  (v{tmpl['version']})"):
            full = api_get(f"/templates/{tmpl['id']}")
            if full and full.get("structure"):
                sections = full["structure"].get("sections",[])
                st.markdown(f"**Sections ({len(sections)}):**")
                for i,s in enumerate(sections,1):
                    st.markdown(f"  `{i}.` {s}")
            st.markdown(f"**Active:** {'✅' if tmpl.get('is_active') else '❌'}")

# ============================================================
# PAGE: QUESTIONNAIRES
# ============================================================
def page_questionnaires():
    st.markdown("<h1 class='main-header'>❓ Questionnaires</h1>", unsafe_allow_html=True)
    depts  = get_departments(); dtypes = get_doc_types()
    c1,c2 = st.columns(2)
    with c1: dept  = st.selectbox("Department",    depts,  key="qa_d")
    with c2: dtype = st.selectbox("Document Type", dtypes, key="qa_t")

    if st.button("🔍 Load Questions", use_container_width=True):
        qs = get_questions(dept, dtype)
        if not qs:
            st.warning("No questionnaire found for this combination.")
        else:
            st.markdown(f"<div class='success-box'>✅ {len(qs)} questions for {dept} — {dtype}</div>", unsafe_allow_html=True)
            cats = {}
            for q in qs: cats.setdefault(q.get("category","common"),[]).append(q)
            for cat, cqs in cats.items():
                st.markdown(f"<h3 style='color:#2a5298;margin-top:15px;'>{cat.replace('_',' ').title()} ({len(cqs)})</h3>", unsafe_allow_html=True)
                for q in cqs:
                    req = "🔴 Required" if q.get("required") else "⚪ Optional"
                    st.markdown(f"<div class='q-block'><b>{q.get('question','')}</b><br><span style='color:#888;font-size:.85rem;'>Type: {q.get('type','')} | {req}</span></div>", unsafe_allow_html=True)

# ============================================================
# PAGE: NOTION
# ============================================================
def page_notion():
    st.markdown("<h1 class='main-header'>🚀 Publish to Notion</h1>", unsafe_allow_html=True)

    st.markdown("<h2 class='sub-header'>🔑 Step 1: Connect Notion</h2>", unsafe_allow_html=True)
    with st.expander("ℹ️ How to get your Notion Token"):
        st.markdown("""
1. Go to **https://www.notion.so/my-integrations** → New Integration → copy token (`secret_...`)
2. Open your Notion database → `...` → Add connections → select your integration
3. Copy the **Database ID** from the URL: `notion.so/workspace/**DATABASE_ID**?v=...`
        """)

    c1,c2 = st.columns(2)
    with c1:
        token = st.text_input("🔐 Integration Token", type="password",
                               placeholder="secret_xxxx", key="notion_token")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Test Connection", use_container_width=True):
            if not token: st.error("Enter token first.")
            else:
                ok, resp = notion_test(token)
                if ok:
                    st.success(f"✅ Connected!")
                else:
                    st.error(f"❌ Failed: {resp}")

    db_id = st.text_input("📋 Database ID", placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", key="notion_db_id")
    if token and st.button("🔍 Auto-detect Databases", use_container_width=True):
        dbs = notion_databases(token)
        if dbs:
            st.markdown(f"<div class='info-box'>Found <b>{len(dbs)}</b> databases:</div>", unsafe_allow_html=True)
            for db in dbs: st.code(f"{db['name']}  →  {db['id']}")
        else:
            st.warning("No databases found. Share your database with the integration first.")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>📄 Step 2: Select & Publish</h2>", unsafe_allow_html=True)

    docs = get_docs()
    if not docs:
        st.info("No documents yet. Generate some first.")
        return

    if "notion_published" not in st.session_state:
        st.session_state.notion_published = {}

    pub_count = len(st.session_state.notion_published)
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(docs)}</div><div class='stat-label'>Total Docs</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(docs)-pub_count}</div><div class='stat-label'>Unpublished</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='stat-box'><div class='stat-number'>{pub_count}</div><div class='stat-label'>Published</div></div>", unsafe_allow_html=True)

    unpublished = [d for d in docs if str(d["id"]) not in st.session_state.notion_published]
    if unpublished and st.button(f"🚀 Publish All ({len(unpublished)}) to Notion", use_container_width=True):
        if not token or not db_id:
            st.error("Enter Token and Database ID first.")
        else:
            pb = st.progress(0); status = st.empty(); errors = []
            for idx,d in enumerate(unpublished):
                status.markdown(f"<p style='text-align:center;'>Publishing: {d['document_type']} — {d['department']}...</p>", unsafe_allow_html=True)
                full = api_get(f"/documents/{d['id']}")
                if full:
                    ok, url, pid = notion_publish(token, db_id, full, full.get("generated_content",""))
                    if ok: st.session_state.notion_published[str(d["id"])] = {"url":url,"pid":pid,"title":f"{d['document_type']} — {d['department']}"}
                    else:  errors.append(f"Doc #{d['id']}: {url}")
                pb.progress((idx+1)/len(unpublished))
            status.empty()
            if errors: st.error("\n".join(errors))
            else: st.markdown(f"<div class='success-box'>🎉 All {len(unpublished)} published!</div>", unsafe_allow_html=True)
            st.rerun()

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    for doc in docs:
        doc_id = str(doc["id"])
        is_pub = doc_id in st.session_state.notion_published
        pub_info = st.session_state.notion_published.get(doc_id,{})

        c1,c2,c3 = st.columns([4,2,2])
        with c1:
            link = f"<a href='{pub_info.get('url','#')}' target='_blank' style='color:#4CAF50;'>🔗 View in Notion</a>" if is_pub else ""
            st.markdown(f"<div class='doc-card'><b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']}</b><br><span style='color:#666;font-size:.9rem;'>🏛️ {doc['department']}</span> {link}</div>", unsafe_allow_html=True)
        with c2:
            if is_pub:
                st.markdown("<div style='background:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;font-weight:600;margin-top:8px;'>✅ Published</div>", unsafe_allow_html=True)
            else:
                if st.button(f"🚀 Publish #{doc['id']}", key=f"pub_{doc_id}", use_container_width=True):
                    if not token or not db_id:
                        st.error("Enter Token and Database ID first.")
                    else:
                        with st.spinner("Publishing..."):
                            full = api_get(f"/documents/{doc['id']}")
                            if full:
                                ok, url, pid = notion_publish(token, db_id, full, full.get("generated_content",""))
                                if ok:
                                    st.session_state.notion_published[doc_id] = {"url":url,"pid":pid,"title":f"{doc['document_type']} — {doc['department']}"}
                                    st.success("✅ Published!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {url}")
        with c3:
            # Download from Notion page too
            if st.button(f"⬇️ Download #{doc['id']}", key=f"ndl_{doc_id}", use_container_width=True):
                st.session_state[f"notion_dl_{doc_id}"] = not st.session_state.get(f"notion_dl_{doc_id}", False)

        if st.session_state.get(f"notion_dl_{doc_id}"):
            render_download_buttons(doc["id"], doc["document_type"],
                                    doc["department"], key_prefix=f"notion_{doc_id}")

# ============================================================
# PAGE: STATS
# ============================================================
def page_stats():
    st.markdown("<h1 class='main-header'>📊 System Stats</h1>", unsafe_allow_html=True)
    if st.button("🔄 Refresh"): get_stats.clear(); st.rerun()

    health = api_get("/system/health")
    if health:
        color = "#4CAF50" if health.get("database")=="connected" else "#f44336"
        st.markdown(f"<div style='background:{color};padding:12px;border-radius:10px;color:white;text-align:center;font-weight:600;margin-bottom:18px;'>Database: {health.get('database','unknown').upper()}</div>", unsafe_allow_html=True)

    stats = get_stats()
    if stats:
        c1,c2,c3,c4 = st.columns(4)
        for col, lbl, key in [
            (c1,"📋 Templates","templates"), (c2,"❓ Questionnaires","questionnaires"),
            (c3,"📄 Documents","documents_generated"), (c4,"⚙️ Jobs","total_jobs"),
        ]:
            with col: st.metric(lbl, stats.get(key,0))
        c1,c2,c3,c4 = st.columns(4)
        for col, lbl, key in [
            (c1,"✅ Completed","jobs_completed"), (c2,"❌ Failed","jobs_failed"),
            (c3,"🏢 Depts","departments"), (c4,"📁 Types","document_types"),
        ]:
            with col: st.metric(lbl, stats.get(key,0))

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>⚙️ Recent Jobs</h2>", unsafe_allow_html=True)
    jobs = api_get("/documents/jobs") or []
    if jobs:
        rows = [{"Job ID": j["job_id"][:12]+"...", "Status": j["status"],
                 "Type": j["document_type"], "Department": j["department"],
                 "Started": j["started_at"][:16]} for j in jobs]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No jobs yet.")

# ============================================================
# MAIN
# ============================================================
def main():
    load_css()
    init_session()
    render_sidebar()

    page = st.session_state.page
    if   page == "Home":           page_home()
    elif page == "Generate":       page_generate()
    elif page == "Library":        page_library()
    elif page == "Templates":      page_templates()
    elif page == "Questionnaires": page_questionnaires()
    elif page == "Notion":         page_notion()
    elif page == "Stats":          page_stats()

if __name__ == "__main__":
    main()
# import streamlit as st
# import pandas as pd
# from datetime import datetime
# import time
# import json
# import requests
# from typing import List, Dict, Optional

# # ============================================
# # CONFIGURATION
# # ============================================
# API_BASE_URL    = "http://127.0.0.1:8000"
# NOTION_API_URL  = "https://api.notion.com/v1"
# NOTION_VERSION  = "2022-06-28"

# def api_get(endpoint: str, params: dict = None):
#     try:
#         r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to backend. Make sure FastAPI is running: `python -m uvicorn main:app --reload`")
#         return None
#     except Exception as e:
#         st.error(f"❌ API Error: {str(e)}")
#         return None

# def api_post(endpoint: str, data: dict):
#     try:
#         r = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=60)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to backend.")
#         return None
#     except requests.exceptions.HTTPError as e:
#         st.error(f"❌ API Error {r.status_code}: {r.text}")
#         return None
#     except Exception as e:
#         st.error(f"❌ Error: {str(e)}")
#         return None

# def api_delete(endpoint: str):
#     try:
#         r = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except Exception as e:
#         st.error(f"❌ Delete failed: {str(e)}")
#         return None

# # ============================================
# # NOTION FUNCTIONS
# # ============================================

# def notion_headers(token: str):
#     return {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json",
#         "Notion-Version": NOTION_VERSION,
#     }

# def notion_test_connection(token: str):
#     try:
#         r = requests.get(f"{NOTION_API_URL}/users/me", headers=notion_headers(token), timeout=10)
#         return r.status_code == 200, r.json()
#     except Exception as e:
#         return False, str(e)

# def notion_get_databases(token: str):
#     try:
#         r = requests.post(
#             f"{NOTION_API_URL}/search",
#             headers=notion_headers(token),
#             json={"filter": {"value": "database", "property": "object"}},
#             timeout=10,
#         )
#         if r.status_code == 200:
#             results = r.json().get("results", [])
#             return [
#                 {
#                     "id": db["id"],
#                     "name": db.get("title", [{}])[0].get("plain_text", "Untitled") if db.get("title") else "Untitled",
#                 }
#                 for db in results
#             ]
#         return []
#     except Exception:
#         return []

# def notion_create_page(token: str, database_id: str, doc: dict, content: str):
#     """Create a Notion page with document content."""
#     doc_type = doc.get("document_type", "Document")
#     dept     = doc.get("department", "")
#     industry = doc.get("industry", "SaaS")
#     doc_id   = doc.get("id", "")

#     # Split content into blocks (max 2000 chars per block)
#     def make_paragraph(text):
#         return {
#             "object": "block",
#             "type": "paragraph",
#             "paragraph": {
#                 "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
#             }
#         }

#     def make_heading(text, level=2):
#         h_type = f"heading_{level}"
#         return {
#             "object": "block",
#             "type": h_type,
#             h_type: {
#                 "rich_text": [{"type": "text", "text": {"content": text[:100]}}]
#             }
#         }

#     # Build blocks from markdown content
#     blocks = []
#     blocks.append(make_paragraph(f"📋 Department: {dept}  |  Industry: {industry}  |  Doc ID: {doc_id}"))
#     blocks.append(make_paragraph("─" * 40))

#     for line in content.split("\n"):
#         if not line.strip():
#             continue
#         if line.startswith("## "):
#             blocks.append(make_heading(line[3:], 2))
#         elif line.startswith("# "):
#             blocks.append(make_heading(line[2:], 1))
#         elif line.startswith("### "):
#             blocks.append(make_heading(line[4:], 3))
#         else:
#             # Split long lines
#             for i in range(0, len(line), 1999):
#                 blocks.append(make_paragraph(line[i:i+1999]))

#         if len(blocks) > 95:  # Notion limit is 100 blocks per request
#             break

#     payload = {
#         "parent": {"database_id": database_id},
#         "properties": {
#             "Name": {
#                 "title": [{"text": {"content": f"{doc_type} — {dept}"}}]
#             },
#         },
#         "children": blocks[:95],
#     }

#     try:
#         r = requests.post(
#             f"{NOTION_API_URL}/pages",
#             headers=notion_headers(token),
#             json=payload,
#             timeout=30,
#         )
#         if r.status_code == 200:
#             page = r.json()
#             return True, page.get("url", ""), page.get("id", "")
#         else:
#             return False, r.text, ""
#     except Exception as e:
#         return False, str(e), ""


# # ============================================
# # DOWNLOAD HELPERS
# # ============================================

# def doc_to_markdown(doc: dict) -> str:
#     content = doc.get("generated_content", "")
#     meta = doc.get("metadata", {})
#     header = f"""---
# Document Type : {doc.get('document_type','')}
# Department    : {doc.get('department','')}
# Industry      : {doc.get('industry','')}
# Status        : {meta.get('doc_status','Draft')}
# Word Count    : {meta.get('word_count','N/A')}
# Reading Time  : {meta.get('reading_time_minutes','N/A')} min
# Generated At  : {doc.get('created_at','')[:16]}
# ---

# """
#     return header + content


# def doc_to_txt(doc: dict) -> str:
#     content = doc.get("generated_content", "")
#     # Strip markdown symbols
#     import re
#     content = re.sub(r"#{1,6}\s", "", content)
#     content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
#     content = re.sub(r"\*(.*?)\*", r"\1", content)
#     content = re.sub(r"`(.*?)`", r"\1", content)
#     return content


# def doc_to_html(doc: dict) -> str:
#     import re
#     content = doc.get("generated_content", "")
#     dept     = doc.get("department", "")
#     doc_type = doc.get("document_type", "")
#     meta     = doc.get("metadata", {})

#     def md_to_html(text):
#         text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
#         text = re.sub(r"^## (.+)$",  r"<h2>\1</h2>", text, flags=re.MULTILINE)
#         text = re.sub(r"^# (.+)$",   r"<h1>\1</h1>", text, flags=re.MULTILINE)
#         text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
#         text = re.sub(r"\*(.+?)\*",     r"<em>\1</em>", text)
#         text = re.sub(r"\n\n", r"</p><p>", text)
#         return f"<p>{text}</p>"

#     return f"""<!DOCTYPE html>
# <html>
# <head>
#   <meta charset="UTF-8">
#   <title>{doc_type} — {dept}</title>
#   <style>
#     body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.7; }}
#     h1 {{ color: #1e3c72; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
#     h2 {{ color: #2a5298; margin-top: 30px; }}
#     h3 {{ color: #555; }}
#     .meta {{ background: #f5f7fa; padding: 15px; border-radius: 8px; margin-bottom: 30px; font-size: 0.9rem; }}
#     .meta span {{ margin-right: 20px; }}
#   </style>
# </head>
# <body>
#   <h1>{doc_type} — {dept}</h1>
#   <div class="meta">
#     <span>🏢 {doc.get('industry','SaaS')}</span>
#     <span>📋 {meta.get('doc_status','Draft')}</span>
#     <span>📝 {meta.get('word_count','N/A')} words</span>
#     <span>⏱️ {meta.get('reading_time_minutes','N/A')} min read</span>
#   </div>
#   {md_to_html(content)}
# </body>
# </html>"""


# # ============================================
# # PAGE CONFIGURATION
# # ============================================
# st.set_page_config(
#     page_title="DocForgeHub - AI Document Generator",
#     page_icon="📄",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # ============================================
# # CUSTOM CSS
# # ============================================
# def load_custom_css():
#     st.markdown("""
#         <style>
#         @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
#         * { font-family: 'Inter', sans-serif; }
#         .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
#         [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%); }
#         .custom-card {
#             background: white; padding: 25px; border-radius: 15px;
#             box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
#             border-left: 5px solid #4CAF50;
#         }
#         .doc-card {
#             background: white; padding: 20px; border-radius: 12px;
#             box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 15px;
#             border: 2px solid #e0e0e0; transition: all 0.3s ease;
#         }
#         .doc-card:hover { border-color: #4CAF50; box-shadow: 0 4px 12px rgba(76,175,80,0.3); }
#         .main-header {
#             font-size: 2.5rem; font-weight: 700; color: #1e3c72;
#             margin-bottom: 10px; text-align: center;
#         }
#         .sub-header {
#             font-size: 1.8rem; font-weight: 600; color: #2a5298;
#             margin-top: 30px; margin-bottom: 20px;
#             border-bottom: 3px solid #4CAF50; padding-bottom: 10px;
#         }
#         .stat-box {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white; padding: 20px; border-radius: 12px;
#             text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
#         }
#         .stat-number { font-size: 2.5rem; font-weight: 700; margin-bottom: 5px; }
#         .stat-label { font-size: 0.9rem; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }
#         .success-box {
#             background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
#             color: white; padding: 20px; border-radius: 12px;
#             margin: 20px 0; text-align: center; font-weight: 600;
#         }
#         .info-box {
#             background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
#             color: white; padding: 20px; border-radius: 12px; margin: 20px 0;
#         }
#         .warning-box {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white; padding: 20px; border-radius: 12px; margin: 20px 0;
#         }
#         .stButton>button {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white; border: none; border-radius: 8px;
#             padding: 12px 30px; font-weight: 600; font-size: 1rem;
#             transition: all 0.3s ease; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
#         }
#         .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.3); }
#         .tag {
#             display: inline-block; background: #e3f2fd; color: #1976d2;
#             padding: 5px 12px; border-radius: 20px; font-size: 0.85rem;
#             margin-right: 8px; margin-bottom: 8px; font-weight: 500;
#         }
#         .doc-type-badge {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white; padding: 5px 15px; border-radius: 20px;
#             font-size: 0.8rem; font-weight: 600; display: inline-block;
#         }
#         .status-published {
#             background: #4CAF50; color: white; padding: 5px 12px;
#             border-radius: 15px; font-size: 0.8rem; font-weight: 600;
#         }
#         .status-draft {
#             background: #FF9800; color: white; padding: 5px 12px;
#             border-radius: 15px; font-size: 0.8rem; font-weight: 600;
#         }
#         .custom-divider {
#             height: 3px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
#             border: none; margin: 30px 0; border-radius: 5px;
#         }
#         .question-block {
#             background: #f8f9ff; border-left: 4px solid #667eea;
#             padding: 15px 20px; border-radius: 8px; margin-bottom: 15px;
#         }
#         </style>
#     """, unsafe_allow_html=True)

# # ============================================
# # SESSION STATE INIT
# # ============================================
# def init_session():
#     defaults = {
#         "current_page": "Home",
#         "generation_step": 1,
#         "selected_industry": "SaaS",
#         "selected_department": None,
#         "selected_doc_type": None,
#         "question_answers": {},
#         "last_generated_doc": None,
#         "departments_cache": None,
#         "doc_types_cache": None,
#         "questionnaire_cache": {},
#     }
#     for k, v in defaults.items():
#         if k not in st.session_state:
#             st.session_state[k] = v

# # ============================================
# # CACHED API CALLS
# # ============================================
# @st.cache_data(ttl=300)
# def fetch_departments():
#     data = api_get("/templates/departments")
#     if data:
#         return data.get("departments", [])
#     return [
#         "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
#         "Engineering & Operations", "Product & Design", "Marketing & Content",
#         "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
#         "Platform & Infrastructure Operation", "Data & Analytics",
#         "QA & Testing", "Security & Information Assurance"
#     ]

# @st.cache_data(ttl=300)
# def fetch_document_types():
#     data = api_get("/templates/document-types")
#     if data:
#         return data.get("document_types", [])
#     return ["SOP", "Policy", "Proposal", "SOW", "Incident Report",
#             "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"]

# @st.cache_data(ttl=300)
# def fetch_questionnaire(department: str, document_type: str):
#     data = api_get("/questionnaires/by-type", params={
#         "department": department,
#         "document_type": document_type
#     })
#     if data and "questions" in data:
#         return data["questions"]
#     return []

# @st.cache_data(ttl=60)
# def fetch_stats():
#     return api_get("/system/stats")

# @st.cache_data(ttl=30)
# def fetch_documents(department=None, document_type=None):
#     params = {}
#     if department: params["department"] = department
#     if document_type: params["document_type"] = document_type
#     return api_get("/documents/", params=params) or []

# # ============================================
# # SIDEBAR
# # ============================================
# def render_sidebar():
#     with st.sidebar:
#         st.markdown("<h1 style='color:white;text-align:center;margin-bottom:20px;'>📄 DocForgeHub</h1>", unsafe_allow_html=True)

#         # Backend health check
#         health = api_get("/system/health")
#         if health and health.get("database") == "connected":
#             st.markdown("<div style='background:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;font-size:0.85rem;margin-bottom:15px;'>🟢 Backend Connected</div>", unsafe_allow_html=True)
#         else:
#             st.markdown("<div style='background:#f44336;padding:8px;border-radius:8px;text-align:center;color:white;font-size:0.85rem;margin-bottom:15px;'>🔴 Backend Offline</div>", unsafe_allow_html=True)

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,0.3);'>", unsafe_allow_html=True)

#         pages = {
#             "🏠 Home": "Home",
#             "✨ Generate Document": "Generate",
#             "📚 Document Library": "Library",
#             "🗂 Templates": "Templates",
#             "❓ Questionnaires": "Questionnaires",
#             "🚀 Publish to Notion": "Notion",
#             "📊 System Stats": "Stats",
#         }

#         for label, key in pages.items():
#             if st.button(label, key=f"nav_{key}", use_container_width=True):
#                 st.session_state.current_page = key
#                 st.rerun()

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,0.3);margin:20px 0;'>", unsafe_allow_html=True)

#         # Live stats from DB
#         stats = fetch_stats()
#         if stats:
#             st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
#             st.metric("Templates", stats.get("templates", 0))
#             st.metric("Documents", stats.get("documents_generated", 0))
#             st.metric("Jobs Done", stats.get("jobs_completed", 0))

#         st.markdown("""
#             <div style='color:rgba(255,255,255,0.7);text-align:center;font-size:0.8rem;margin-top:30px;'>
#                 <p>Powered by Azure OpenAI + LangChain</p>
#                 <p>© 2026 DocForgeHub</p>
#             </div>
#         """, unsafe_allow_html=True)

# # ============================================
# # PAGE: HOME
# # ============================================
# def render_home():
#     st.markdown("<h1 class='main-header'>🚀 Welcome to DocForgeHub</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;font-size:1.2rem;color:#555;margin-bottom:30px;'>AI-Powered Enterprise Document Generation — Backed by PostgreSQL + Azure OpenAI</p>", unsafe_allow_html=True)

#     stats = fetch_stats()

#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('templates',0) if stats else 0}</div><div class='stat-label'>Templates</div></div>", unsafe_allow_html=True)
#     with col2:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('documents_generated',0) if stats else 0}</div><div class='stat-label'>Documents</div></div>", unsafe_allow_html=True)
#     with col3:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('departments',0) if stats else 0}</div><div class='stat-label'>Departments</div></div>", unsafe_allow_html=True)
#     with col4:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('document_types',0) if stats else 0}</div><div class='stat-label'>Doc Types</div></div>", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.markdown("""<div class='custom-card'><h3 style='color:#1e3c72;'>🤖 AI Generation</h3>
#         <p style='color:#555;'>Azure OpenAI + LangChain generates professional documents with your exact company context.</p></div>""", unsafe_allow_html=True)
#     with col2:
#         st.markdown("""<div class='custom-card' style='border-left-color:#764ba2'><h3 style='color:#1e3c72;'>🗄️ PostgreSQL Backend</h3>
#         <p style='color:#555;'>All templates, questionnaires, and documents stored in your PostgreSQL database.</p></div>""", unsafe_allow_html=True)
#     with col3:
#         st.markdown("""<div class='custom-card' style='border-left-color:#4facfe'><h3 style='color:#1e3c72;'>📋 Smart Q&A</h3>
#         <p style='color:#555;'>Dynamic questions per department × document type, loaded from your database.</p></div>""", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     col1, col2 = st.columns(2)
#     with col1:
#         if st.button("✨ Generate New Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.session_state.generation_step = 1
#             st.rerun()
#     with col2:
#         if st.button("📚 View Document Library", use_container_width=True):
#             st.session_state.current_page = "Library"
#             st.rerun()

#     # Recent documents
#     docs = fetch_documents()
#     if docs:
#         st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
#         for doc in docs[:5]:
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <div style='display:flex;justify-content:space-between;align-items:center;'>
#                     <div>
#                         <b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']} — {doc['department']}</b><br>
#                         <span style='color:#999;font-size:0.85rem;'>Industry: {doc['industry']} | Created: {doc['created_at'][:16]}</span>
#                     </div>
#                     <span class='status-{"published" if doc["status"]=="completed" else "draft"}'>{doc['status'].upper()}</span>
#                 </div>
#             </div>""", unsafe_allow_html=True)

# # ============================================
# # PAGE: GENERATE DOCUMENT
# # ============================================
# def render_generate():
#     st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)

#     step = st.session_state.generation_step
#     progress = (step - 1) / 3
#     st.progress(progress)

#     steps_labels = ["📋 Select Type", "❓ Answer Questions", "🎉 Generate & Review"]
#     cols = st.columns(3)
#     for idx, (col, label) in enumerate(zip(cols, steps_labels)):
#         with col:
#             if idx + 1 < step:
#                 st.markdown(f"<p style='text-align:center;color:#4CAF50;font-weight:600;'>✅ {label}</p>", unsafe_allow_html=True)
#             elif idx + 1 == step:
#                 st.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>▶️ {label}</p>", unsafe_allow_html=True)
#             else:
#                 st.markdown(f"<p style='text-align:center;color:#999;'>⏺️ {label}</p>", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── STEP 1: Select Type ──
#     if step == 1:
#         st.markdown("<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True)

#         departments = fetch_departments()
#         doc_types   = fetch_document_types()

#         col1, col2, col3 = st.columns(3)
#         with col1:
#             industry = st.selectbox("🏢 Industry", ["SaaS"], key="s1_industry")
#         with col2:
#             department = st.selectbox("🏛️ Department", departments, key="s1_dept")
#         with col3:
#             doc_type = st.selectbox("📄 Document Type", doc_types, key="s1_type")

#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("➡️ Next: Answer Questions", use_container_width=True):
#             st.session_state.selected_industry   = industry
#             st.session_state.selected_department = department
#             st.session_state.selected_doc_type   = doc_type
#             st.session_state.generation_step     = 2
#             st.rerun()

#     # ── STEP 2: Answer Questions from DB ──
#     elif step == 2:
#         st.markdown("<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True)

#         dept     = st.session_state.selected_department
#         doc_type = st.session_state.selected_doc_type

#         st.markdown(f"""
#         <div class='info-box'>
#             <strong>Generating:</strong> {doc_type} for <strong>{dept}</strong>
#         </div>""", unsafe_allow_html=True)

#         # Fetch questions from DB
#         questions = fetch_questionnaire(dept, doc_type)

#         if not questions:
#             st.warning("No questionnaire found in DB. Using default questions.")
#             questions = [
#                 {"id": "company_name",    "question": "What is your company name?",            "type": "text",     "required": True,  "options": []},
#                 {"id": "company_size",    "question": "Company size?",                          "type": "select",   "required": True,  "options": ["1-10","11-50","51-200","201-500","1000+"]},
#                 {"id": "primary_product", "question": "What is your primary SaaS product?",     "type": "text",     "required": True,  "options": []},
#                 {"id": "specific_focus",  "question": "What specific topic should this cover?", "type": "text",     "required": False, "options": []},
#                 {"id": "tools_used",      "question": "Tools/systems used?",                    "type": "text",     "required": False, "options": []},
#                 {"id": "tone_preference", "question": "Preferred document tone?",               "type": "select",   "required": False, "options": ["Professional & Formal","Professional & Friendly","Technical & Detailed","Executive-level & Concise"]},
#                 {"id": "additional_context","question":"Any additional context?",               "type": "textarea", "required": False, "options": []},
#             ]

#         answers = {}

#         # Group questions by category
#         categories = {}
#         for q in questions:
#             cat = q.get("category", "common")
#             categories.setdefault(cat, []).append(q)

#         category_labels = {
#             "common": "📋 General Questions",
#             "document_type_specific": f"📄 {doc_type} Specific Questions",
#             "department_specific": f"🏛️ {dept} Specific Questions",
#         }

#         for cat_key, cat_questions in categories.items():
#             if cat_questions:
#                 st.markdown(f"<h3 style='color:#2a5298;margin-top:25px;'>{category_labels.get(cat_key, cat_key)}</h3>", unsafe_allow_html=True)

#                 for q in cat_questions:
#                     q_id   = q.get("id", "")
#                     q_text = q.get("question", "")
#                     q_type = q.get("type", "text")
#                     q_req  = q.get("required", False)
#                     q_opts = q.get("options", [])
#                     q_placeholder = q.get("placeholder", "")

#                     label = f"{'🔴 ' if q_req else ''}{q_text}"

#                     st.markdown(f"<div class='question-block'><b style='color:#1e3c72;'>{label}</b></div>", unsafe_allow_html=True)

#                     widget_key = f"q_{q_id}"

#                     if q_type == "text":
#                         answers[q_id] = st.text_input("", key=widget_key, placeholder=q_placeholder or "", label_visibility="collapsed")

#                     elif q_type == "textarea":
#                         answers[q_id] = st.text_area("", key=widget_key, height=100, placeholder=q_placeholder or "", label_visibility="collapsed")

#                     elif q_type == "select" and q_opts:
#                         answers[q_id] = st.selectbox("", ["(select)"] + q_opts, key=widget_key, label_visibility="collapsed")

#                     elif q_type == "multi_select" and q_opts:
#                         answers[q_id] = st.multiselect("", q_opts, key=widget_key, label_visibility="collapsed")

#                     else:
#                         answers[q_id] = st.text_input("", key=widget_key, label_visibility="collapsed")

#         st.markdown("<br>", unsafe_allow_html=True)
#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("⬅️ Back", use_container_width=True):
#                 st.session_state.generation_step = 1
#                 st.rerun()
#         with col2:
#             if st.button("🚀 Generate Document", use_container_width=True):
#                 # Validate required
#                 missing = []
#                 for q in questions:
#                     if q.get("required") and not answers.get(q.get("id", "")):
#                         missing.append(q.get("question", ""))
#                 if missing:
#                     for m in missing:
#                         st.error(f"Required: {m}")
#                 else:
#                     # Clean answers — remove empty/default
#                     clean_answers = {k: v for k, v in answers.items() if v and v != "(select)"}
#                     st.session_state.question_answers = clean_answers
#                     st.session_state.generation_step  = 3
#                     st.rerun()

#     # ── STEP 3: Generate via API ──
#     elif step == 3:
#         st.markdown("<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True)

#         if st.session_state.last_generated_doc is None:
#             progress_bar = st.progress(0)
#             status_text  = st.empty()

#             phases = [
#                 ("Connecting to FastAPI backend...", 0.15),
#                 ("Loading template from PostgreSQL...", 0.30),
#                 ("Loading questionnaire from DB...", 0.45),
#                 ("Building AI prompt...", 0.60),
#                 ("Calling Azure OpenAI...", 0.80),
#                 ("Saving document to database...", 0.95),
#             ]

#             for text, pct in phases:
#                 status_text.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>{text}</p>", unsafe_allow_html=True)
#                 progress_bar.progress(pct)
#                 time.sleep(0.4)

#             # Call FastAPI
#             payload = {
#                 "industry":         st.session_state.selected_industry,
#                 "department":       st.session_state.selected_department,
#                 "document_type":    st.session_state.selected_doc_type,
#                 "question_answers": st.session_state.question_answers,
#             }

#             result = api_post("/documents/generate", payload)

#             progress_bar.progress(1.0)
#             status_text.empty()
#             progress_bar.empty()

#             if result:
#                 st.session_state.last_generated_doc = result
#             else:
#                 st.error("Document generation failed. Check FastAPI logs.")
#                 if st.button("⬅️ Try Again"):
#                     st.session_state.generation_step = 2
#                     st.rerun()
#                 return

#         doc = st.session_state.last_generated_doc
#         v   = doc.get("validation", {})

#         st.markdown(f"""
#         <div class='success-box'>
#             ✅ Document Generated! ID: {doc.get('document_id')} | Job: {doc.get('job_id','')[:8]}...
#         </div>""", unsafe_allow_html=True)

#         # ── Validation Report ──
#         st.markdown("<h3 style='color:#1e3c72;margin-top:25px;'>📊 Quality Validation Report</h3>", unsafe_allow_html=True)

#         score = v.get("score", 0)
#         grade = v.get("grade", "N/A")
#         label = v.get("label", "")
#         wc    = v.get("word_count", 0)

#         score_color = "#4CAF50" if score >= 75 else "#FF9800" if score >= 60 else "#f44336"
#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.markdown(f"<div style='background:{score_color};padding:15px;border-radius:10px;text-align:center;color:white;'><div style='font-size:2rem;font-weight:700;'>{score}/100</div><div style='font-size:0.85rem;'>Quality Score</div></div>", unsafe_allow_html=True)
#         with col2:
#             st.markdown(f"<div style='background:{score_color};padding:15px;border-radius:10px;text-align:center;color:white;'><div style='font-size:2rem;font-weight:700;'>{grade}</div><div style='font-size:0.85rem;'>Grade</div></div>", unsafe_allow_html=True)
#         with col3:
#             st.markdown(f"<div class='stat-box'><div class='stat-number'>{wc:,}</div><div class='stat-label'>Words</div></div>", unsafe_allow_html=True)
#         with col4:
#             passed_count = len(v.get("passed", []))
#             issue_count  = len(v.get("issues", []))
#             st.markdown(f"<div class='stat-box'><div class='stat-number'>{passed_count}✅ {issue_count}❌</div><div class='stat-label'>Checks</div></div>", unsafe_allow_html=True)

#         st.markdown("<br>", unsafe_allow_html=True)
#         col_a, col_b, col_c = st.columns(3)

#         with col_a:
#             if v.get("passed"):
#                 st.markdown("**✅ Passed Checks**")
#                 for p in v["passed"]:
#                     st.markdown(f"<span style='color:#4CAF50;font-size:0.9rem;'>{p}</span>", unsafe_allow_html=True)

#         with col_b:
#             if v.get("warnings"):
#                 st.markdown("**⚠️ Warnings**")
#                 for w in v["warnings"]:
#                     st.markdown(f"<span style='color:#FF9800;font-size:0.9rem;'>{w}</span>", unsafe_allow_html=True)

#         with col_c:
#             if v.get("issues"):
#                 st.markdown("**❌ Issues**")
#                 for i in v["issues"]:
#                     st.markdown(f"<span style='color:#f44336;font-size:0.9rem;'>{i}</span>", unsafe_allow_html=True)
#             else:
#                 st.markdown("**❌ Issues**")
#                 st.markdown("<span style='color:#4CAF50;font-size:0.9rem;'>None — document passed all checks!</span>", unsafe_allow_html=True)

#         st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#         # Show document details
#         st.markdown("<h3 style='color:#1e3c72;margin-top:10px;'>📄 Document Preview</h3>", unsafe_allow_html=True)

#         st.markdown(f"""
#         <div class='doc-card'>
#             <p><span class='doc-type-badge'>{st.session_state.selected_doc_type}</span></p>
#             <p style='color:#666;'><strong>Department:</strong> {st.session_state.selected_department}</p>
#             <p style='color:#666;'><strong>Industry:</strong> {st.session_state.selected_industry}</p>
#             <p style='color:#666;'><strong>Document ID:</strong> {doc.get('document_id')}</p>
#             <p style='color:#666;'><strong>Job ID:</strong> {doc.get('job_id')}</p>
#         </div>""", unsafe_allow_html=True)

#         with st.expander("📖 View Full Generated Content", expanded=True):
#             content = doc.get("document", "No content returned.")
#             st.markdown(content)

#         with st.expander("📋 Your Answers Submitted"):
#             st.json(st.session_state.question_answers)

#         # Download buttons - multiple formats
#         full_doc = api_get(f"/documents/{doc.get('document_id')}")
#         if full_doc:
#             st.markdown("<h3 style='color:#1e3c72;margin-top:20px;'>⬇️ Download Document</h3>", unsafe_allow_html=True)
#             col1, col2, col3 = st.columns(3)
#             fname_base = f"{st.session_state.selected_doc_type}_{st.session_state.selected_department.replace(' ','_').replace('&','and')}"

#             with col1:
#                 st.download_button(
#                     label="📄 Download .md",
#                     data=doc_to_markdown(full_doc),
#                     file_name=f"{fname_base}.md",
#                     mime="text/markdown",
#                     use_container_width=True,
#                 )
#             with col2:
#                 st.download_button(
#                     label="📝 Download .txt",
#                     data=doc_to_txt(full_doc),
#                     file_name=f"{fname_base}.txt",
#                     mime="text/plain",
#                     use_container_width=True,
#                 )
#             with col3:
#                 st.download_button(
#                     label="🌐 Download .html",
#                     data=doc_to_html(full_doc),
#                     file_name=f"{fname_base}.html",
#                     mime="text/html",
#                     use_container_width=True,
#                 )

#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("🔄 Generate Another", use_container_width=True):
#                 st.session_state.generation_step    = 1
#                 st.session_state.last_generated_doc = None
#                 st.session_state.question_answers   = {}
#                 st.rerun()
#         with col2:
#             if st.button("📚 Go to Library", use_container_width=True):
#                 st.session_state.current_page       = "Library"
#                 st.session_state.generation_step    = 1
#                 st.session_state.last_generated_doc = None
#                 st.rerun()

# # ============================================
# # PAGE: DOCUMENT LIBRARY
# # ============================================
# def render_library():
#     st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         f_dept = st.selectbox("Filter by Department", ["All"] + departments, key="lib_dept")
#     with col2:
#         f_type = st.selectbox("Filter by Document Type", ["All"] + doc_types, key="lib_type")
#     with col3:
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("🔄 Refresh", use_container_width=True):
#             fetch_documents.clear()
#             st.rerun()

#     docs = fetch_documents(
#         department=f_dept if f_dept != "All" else None,
#         document_type=f_type if f_type != "All" else None,
#     )

#     st.markdown(f"<p style='color:#666;'><strong>{len(docs)}</strong> documents found</p>", unsafe_allow_html=True)
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     if not docs:
#         st.markdown("""<div class='info-box'><h3>📭 No Documents Found</h3>
#         <p>Generate your first document using the Generate page.</p></div>""", unsafe_allow_html=True)
#         if st.button("✨ Generate Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
#         return

#     for doc in docs:
#         with st.container():
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <div style='display:flex;justify-content:space-between;align-items:start;'>
#                     <div>
#                         <b style='color:#1e3c72;font-size:1.1rem;'>#{doc['id']} — {doc['document_type']}</b><br>
#                         <span style='color:#666;'>🏛️ {doc['department']} | 🏢 {doc['industry']}</span><br>
#                         <span style='color:#999;font-size:0.85rem;'>📅 {doc['created_at'][:16]}</span>
#                     </div>
#                     <span class='{"status-published" if doc["status"]=="completed" else "status-draft"}'>{doc['status'].upper()}</span>
#                 </div>
#             </div>""", unsafe_allow_html=True)

#             col1, col2 = st.columns([3, 1])
#             with col1:
#                 if st.button(f"📖 View Document #{doc['id']}", key=f"view_{doc['id']}", use_container_width=True):
#                     full = api_get(f"/documents/{doc['id']}")
#                     if full:
#                         with st.expander(f"📄 Document #{doc['id']} — Full View", expanded=True):
#                             st.markdown(f"**Type:** {full['document_type']}  |  **Department:** {full['department']}  |  **Industry:** {full['industry']}")
#                             if full.get("metadata"):
#                                 meta = full["metadata"]
#                                 st.markdown(f"**Word Count:** {meta.get('word_count','N/A')}  |  **Reading Time:** {meta.get('reading_time_minutes','N/A')} min  |  **Status:** {meta.get('doc_status','N/A')}")
#                             st.markdown("---")
#                             st.markdown(full.get("generated_content", "No content"))
#             with col2:
#                 if st.button(f"🗑️ Delete #{doc['id']}", key=f"del_{doc['id']}", use_container_width=True):
#                     result = api_delete(f"/documents/{doc['id']}")
#                     if result:
#                         st.success("Deleted!")
#                         fetch_documents.clear()
#                         time.sleep(1)
#                         st.rerun()

# # ============================================
# # PAGE: TEMPLATES
# # ============================================
# def render_templates():
#     st.markdown("<h1 class='main-header'>🗂 Templates</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;color:#555;'>All templates seeded from content.json via PostgreSQL</p>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2 = st.columns(2)
#     with col1:
#         f_dept = st.selectbox("Filter Department", ["All"] + departments, key="tmpl_dept")
#     with col2:
#         f_type = st.selectbox("Filter Document Type", ["All"] + doc_types, key="tmpl_type")

#     params = {}
#     if f_dept != "All": params["department"] = f_dept
#     if f_type != "All": params["document_type"] = f_type

#     templates = api_get("/templates/", params=params) or []

#     st.markdown(f"<p style='color:#666;'><strong>{len(templates)}</strong> templates found</p>", unsafe_allow_html=True)
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     for tmpl in templates:
#         with st.expander(f"🗂 {tmpl['department']} — {tmpl['document_type']}  (v{tmpl['version']})"):
#             full = api_get(f"/templates/{tmpl['id']}")
#             if full and full.get("structure"):
#                 sections = full["structure"].get("sections", [])
#                 st.markdown(f"**Total Sections:** {len(sections)}")
#                 for i, s in enumerate(sections, 1):
#                     st.markdown(f"  `{i}.` {s}")
#             st.markdown(f"**Active:** {'✅' if tmpl.get('is_active') else '❌'}  |  **Created:** {tmpl.get('created_at','')[:10]}")

# # ============================================
# # PAGE: QUESTIONNAIRES
# # ============================================
# def render_questionnaires():
#     st.markdown("<h1 class='main-header'>❓ Questionnaires</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;color:#555;'>All Q&A seeded from Question_Answer.json via PostgreSQL</p>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2 = st.columns(2)
#     with col1:
#         dept = st.selectbox("Department", departments, key="qa_dept")
#     with col2:
#         doc_type = st.selectbox("Document Type", doc_types, key="qa_type")

#     if st.button("🔍 Load Questions", use_container_width=True):
#         questions = fetch_questionnaire(dept, doc_type)

#         if not questions:
#             st.warning("No questionnaire found for this combination.")
#         else:
#             st.markdown(f"<div class='success-box'>✅ {len(questions)} questions loaded for {dept} — {doc_type}</div>", unsafe_allow_html=True)

#             categories = {}
#             for q in questions:
#                 cat = q.get("category", "common")
#                 categories.setdefault(cat, []).append(q)

#             for cat, qs in categories.items():
#                 st.markdown(f"<h3 style='color:#2a5298;margin-top:20px;'>{cat.replace('_',' ').title()} ({len(qs)} questions)</h3>", unsafe_allow_html=True)
#                 for q in qs:
#                     req_badge = "🔴 Required" if q.get("required") else "⚪ Optional"
#                     st.markdown(f"""
#                     <div class='question-block'>
#                         <b>{q.get('question','')}</b><br>
#                         <span style='color:#888;font-size:0.85rem;'>Type: {q.get('type','')} | {req_badge}</span>
#                         {f"<br><span style='color:#1976d2;font-size:0.8rem;'>💡 {q.get('used_in_prompt','')}</span>" if q.get('used_in_prompt') else ''}
#                     </div>""", unsafe_allow_html=True)

# # ============================================
# # PAGE: SYSTEM STATS
# # ============================================
# def render_stats():
#     st.markdown("<h1 class='main-header'>📊 System Statistics</h1>", unsafe_allow_html=True)

#     if st.button("🔄 Refresh Stats"):
#         fetch_stats.clear()
#         st.rerun()

#     stats = fetch_stats()
#     health = api_get("/system/health")

#     if health:
#         db_status = health.get("database", "unknown")
#         color = "#4CAF50" if db_status == "connected" else "#f44336"
#         st.markdown(f"<div style='background:{color};padding:15px;border-radius:10px;color:white;text-align:center;font-weight:600;margin-bottom:20px;'>Database: {db_status.upper()}</div>", unsafe_allow_html=True)

#     if stats:
#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.metric("📋 Templates",      stats.get("templates", 0))
#         with col2:
#             st.metric("❓ Questionnaires", stats.get("questionnaires", 0))
#         with col3:
#             st.metric("📄 Documents",      stats.get("documents_generated", 0))
#         with col4:
#             st.metric("⚙️ Total Jobs",     stats.get("total_jobs", 0))

#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.metric("✅ Jobs Completed", stats.get("jobs_completed", 0))
#         with col2:
#             st.metric("❌ Jobs Failed",    stats.get("jobs_failed", 0))
#         with col3:
#             st.metric("🏢 Departments",    stats.get("departments", 0))
#         with col4:
#             st.metric("📁 Document Types", stats.get("document_types", 0))

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # Recent jobs
#     st.markdown("<h2 class='sub-header'>⚙️ Recent Generation Jobs</h2>", unsafe_allow_html=True)
#     jobs = api_get("/documents/jobs") or []
#     if jobs:
#         df = pd.DataFrame(jobs)[["job_id", "status", "document_type", "department", "started_at"]]
#         df["job_id"] = df["job_id"].str[:12] + "..."
#         st.dataframe(df, use_container_width=True)
#     else:
#         st.info("No jobs yet.")

# # ============================================
# # PAGE: PUBLISH TO NOTION
# # ============================================
# def render_notion():
#     st.markdown("<h1 class='main-header'>🚀 Publish to Notion</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;font-size:1.1rem;color:#555;margin-bottom:30px;'>Connect your Notion workspace and publish documents directly</p>", unsafe_allow_html=True)

#     # ── Step 1: Notion credentials ──
#     st.markdown("<h2 class='sub-header'>🔑 Step 1: Notion Connection</h2>", unsafe_allow_html=True)

#     with st.expander("ℹ️ How to get your Notion API Token", expanded=False):
#         st.markdown("""
#         1. Go to **https://www.notion.so/my-integrations**
#         2. Click **"New Integration"** → give it a name like *DocForgeHub*
#         3. Copy the **Internal Integration Token** (starts with `secret_...`)
#         4. Open the Notion Database you want to publish to
#         5. Click **"..."** → **"Add connections"** → select your integration
#         6. Copy the **Database ID** from the URL:
#            `https://notion.so/YOUR_WORKSPACE/**DATABASE_ID**?v=...`
#         """)

#     col1, col2 = st.columns(2)
#     with col1:
#         notion_token = st.text_input(
#             "🔐 Notion Integration Token",
#             type="password",
#             placeholder="secret_xxxxxxxxxxxxxxxxxxxx",
#             key="notion_token",
#             help="Get from https://www.notion.so/my-integrations"
#         )
#     with col2:
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("🔍 Test Connection", use_container_width=True):
#             if not notion_token:
#                 st.error("Enter your Notion token first.")
#             else:
#                 ok, resp = notion_test_connection(notion_token)
#                 if ok:
#                     name = resp.get("name", resp.get("bot", {}).get("owner", {}).get("user", {}).get("name", "User"))
#                     st.success(f"✅ Connected as: {name}")
#                     st.session_state.notion_connected = True
#                 else:
#                     st.error(f"❌ Connection failed: {resp}")
#                     st.session_state.notion_connected = False

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── Step 2: Select Database ──
#     st.markdown("<h2 class='sub-header'>🗄️ Step 2: Select Target Database</h2>", unsafe_allow_html=True)

#     database_id = st.text_input(
#         "📋 Notion Database ID",
#         placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
#         key="notion_db_id",
#         help="Copy from your Notion database URL"
#     )

#     if notion_token and st.button("🔍 Auto-detect my Databases", use_container_width=True):
#         dbs = notion_get_databases(notion_token)
#         if dbs:
#             st.markdown(f"<div class='info-box'>Found <strong>{len(dbs)}</strong> databases in your workspace:</div>", unsafe_allow_html=True)
#             for db in dbs:
#                 st.code(f"{db['name']}  →  ID: {db['id']}")
#         else:
#             st.warning("No databases found. Make sure you've shared databases with your integration.")

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── Step 3: Select Documents to Publish ──
#     st.markdown("<h2 class='sub-header'>📄 Step 3: Select Documents</h2>", unsafe_allow_html=True)

#     docs = fetch_documents()

#     if not docs:
#         st.markdown("""<div class='info-box'><h3>📭 No Documents Found</h3>
#         <p>Generate documents first, then publish them here.</p></div>""", unsafe_allow_html=True)
#         if st.button("✨ Generate Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
#         return

#     # Track published doc IDs in session
#     if "notion_published_ids" not in st.session_state:
#         st.session_state.notion_published_ids = {}

#     # Stats row
#     published_count = len(st.session_state.notion_published_ids)
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(docs)}</div><div class='stat-label'>Total Docs</div></div>", unsafe_allow_html=True)
#     with col2:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(docs)-published_count}</div><div class='stat-label'>Ready to Publish</div></div>", unsafe_allow_html=True)
#     with col3:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{published_count}</div><div class='stat-label'>Published</div></div>", unsafe_allow_html=True)

#     st.markdown("<br>", unsafe_allow_html=True)

#     # Publish ALL button
#     unpublished = [d for d in docs if str(d['id']) not in st.session_state.notion_published_ids]
#     if unpublished and st.button(f"🚀 Publish All ({len(unpublished)}) to Notion", use_container_width=True):
#         if not notion_token or not database_id:
#             st.error("❌ Please enter your Notion Token and Database ID first.")
#         else:
#             progress = st.progress(0)
#             status   = st.empty()
#             errors   = []

#             for idx, doc in enumerate(unpublished):
#                 status.markdown(f"<p style='text-align:center;color:#667eea;'>Publishing: {doc['document_type']} — {doc['department']}...</p>", unsafe_allow_html=True)

#                 full_doc = api_get(f"/documents/{doc['id']}")
#                 if full_doc:
#                     ok, url, page_id = notion_create_page(
#                         notion_token, database_id, full_doc,
#                         full_doc.get("generated_content", "")
#                     )
#                     if ok:
#                         st.session_state.notion_published_ids[str(doc['id'])] = {
#                             "url": url, "page_id": page_id,
#                             "title": f"{doc['document_type']} — {doc['department']}"
#                         }
#                     else:
#                         errors.append(f"Doc #{doc['id']}: {url}")

#                 progress.progress((idx + 1) / len(unpublished))

#             status.empty()
#             if errors:
#                 st.error(f"Some failed:\n" + "\n".join(errors))
#             else:
#                 st.markdown(f"<div class='success-box'>🎉 All {len(unpublished)} documents published to Notion!</div>", unsafe_allow_html=True)
#             st.rerun()

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # Individual document list
#     for doc in docs:
#         doc_id     = str(doc['id'])
#         is_pub     = doc_id in st.session_state.notion_published_ids
#         pub_info   = st.session_state.notion_published_ids.get(doc_id, {})

#         with st.container():
#             col1, col2, col3 = st.columns([4, 2, 2])

#             with col1:
#                 st.markdown(f"""
#                 <div class='doc-card' style='margin-bottom:5px;'>
#                     <b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']}</b><br>
#                     <span style='color:#666;font-size:0.9rem;'>🏛️ {doc['department']} | 📅 {doc['created_at'][:10]}</span>
#                     {f"<br><a href='{pub_info.get('url','#')}' target='_blank' style='color:#4CAF50;font-size:0.85rem;'>🔗 View in Notion</a>" if is_pub else ''}
#                 </div>""", unsafe_allow_html=True)

#             with col2:
#                 if is_pub:
#                     st.markdown("<div style='background:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;font-weight:600;margin-top:8px;'>✅ Published</div>", unsafe_allow_html=True)
#                 else:
#                     if st.button(f"🚀 Publish #{doc['id']}", key=f"pub_{doc['id']}", use_container_width=True):
#                         if not notion_token or not database_id:
#                             st.error("Enter Notion Token and Database ID first.")
#                         else:
#                             with st.spinner("Publishing..."):
#                                 full_doc = api_get(f"/documents/{doc['id']}")
#                                 if full_doc:
#                                     ok, url, page_id = notion_create_page(
#                                         notion_token, database_id, full_doc,
#                                         full_doc.get("generated_content", "")
#                                     )
#                                     if ok:
#                                         st.session_state.notion_published_ids[doc_id] = {
#                                             "url": url, "page_id": page_id,
#                                             "title": f"{doc['document_type']} — {doc['department']}"
#                                         }
#                                         st.success(f"✅ Published!")
#                                         st.rerun()
#                                     else:
#                                         st.error(f"Failed: {url}")

#             with col3:
#                 # Download from library too
#                 if st.button(f"⬇️ Download #{doc['id']}", key=f"dl_{doc['id']}", use_container_width=True):
#                     full_doc = api_get(f"/documents/{doc['id']}")
#                     if full_doc:
#                         st.session_state[f"download_doc_{doc_id}"] = full_doc

#                 if st.session_state.get(f"download_doc_{doc_id}"):
#                     full_doc  = st.session_state[f"download_doc_{doc_id}"]
#                     fname     = f"{doc['document_type']}_{doc['department'].replace(' ','_').replace('&','and')}"
#                     st.download_button("📄 .md",   doc_to_markdown(full_doc), f"{fname}.md",   "text/markdown",    key=f"md_{doc_id}")
#                     st.download_button("📝 .txt",  doc_to_txt(full_doc),      f"{fname}.txt",  "text/plain",       key=f"txt_{doc_id}")
#                     st.download_button("🌐 .html", doc_to_html(full_doc),     f"{fname}.html", "text/html",        key=f"html_{doc_id}")

#     # Published history
#     if st.session_state.notion_published_ids:
#         st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
#         st.markdown("<h2 class='sub-header'>✅ Published to Notion</h2>", unsafe_allow_html=True)
#         for doc_id, info in st.session_state.notion_published_ids.items():
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <b style='color:#1e3c72;'>{info.get('title','Document')}</b><br>
#                 <a href='{info.get('url','#')}' target='_blank' style='color:#4CAF50;'>🔗 Open in Notion</a>
#                 <span style='color:#999;font-size:0.8rem;margin-left:15px;'>Page ID: {info.get('page_id','')[:8]}...</span>
#             </div>""", unsafe_allow_html=True)


# # ============================================
# # MAIN
# # ============================================
# def main():
#     load_custom_css()
#     init_session()
#     render_sidebar()

#     page = st.session_state.current_page

#     if page == "Home":           render_home()
#     elif page == "Generate":     render_generate()
#     elif page == "Library":      render_library()
#     elif page == "Templates":    render_templates()
#     elif page == "Questionnaires": render_questionnaires()
#     elif page == "Notion":           render_notion()
#     elif page == "Stats":            render_stats()

# if __name__ == "__main__":
#     main()
# import streamlit as st
# import pandas as pd
# from datetime import datetime
# import time
# import json
# import requests
# from typing import List, Dict, Optional

# # ============================================
# # CONFIGURATION
# # ============================================
# API_BASE_URL    = "http://127.0.0.1:8000"
# NOTION_API_URL  = "https://api.notion.com/v1"
# NOTION_VERSION  = "2022-06-28"

# def api_get(endpoint: str, params: dict = None):
#     try:
#         r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to backend. Make sure FastAPI is running: `python -m uvicorn main:app --reload`")
#         return None
#     except Exception as e:
#         st.error(f"❌ API Error: {str(e)}")
#         return None

# def api_post(endpoint: str, data: dict):
#     try:
#         r = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=60)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to backend.")
#         return None
#     except requests.exceptions.HTTPError as e:
#         st.error(f"❌ API Error {r.status_code}: {r.text}")
#         return None
#     except Exception as e:
#         st.error(f"❌ Error: {str(e)}")
#         return None

# def api_delete(endpoint: str):
#     try:
#         r = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except Exception as e:
#         st.error(f"❌ Delete failed: {str(e)}")
#         return None

# # ============================================
# # NOTION FUNCTIONS
# # ============================================

# def notion_headers(token: str):
#     return {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json",
#         "Notion-Version": NOTION_VERSION,
#     }

# def notion_test_connection(token: str):
#     try:
#         r = requests.get(f"{NOTION_API_URL}/users/me", headers=notion_headers(token), timeout=10)
#         return r.status_code == 200, r.json()
#     except Exception as e:
#         return False, str(e)

# def notion_get_databases(token: str):
#     try:
#         r = requests.post(
#             f"{NOTION_API_URL}/search",
#             headers=notion_headers(token),
#             json={"filter": {"value": "database", "property": "object"}},
#             timeout=10,
#         )
#         if r.status_code == 200:
#             results = r.json().get("results", [])
#             return [
#                 {
#                     "id": db["id"],
#                     "name": db.get("title", [{}])[0].get("plain_text", "Untitled") if db.get("title") else "Untitled",
#                 }
#                 for db in results
#             ]
#         return []
#     except Exception:
#         return []

# def notion_create_page(token: str, database_id: str, doc: dict, content: str):
#     """Create a Notion page with document content."""
#     doc_type = doc.get("document_type", "Document")
#     dept     = doc.get("department", "")
#     industry = doc.get("industry", "SaaS")
#     doc_id   = doc.get("id", "")

#     # Split content into blocks (max 2000 chars per block)
#     def make_paragraph(text):
#         return {
#             "object": "block",
#             "type": "paragraph",
#             "paragraph": {
#                 "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
#             }
#         }

#     def make_heading(text, level=2):
#         h_type = f"heading_{level}"
#         return {
#             "object": "block",
#             "type": h_type,
#             h_type: {
#                 "rich_text": [{"type": "text", "text": {"content": text[:100]}}]
#             }
#         }

#     # Build blocks from markdown content
#     blocks = []
#     blocks.append(make_paragraph(f"📋 Department: {dept}  |  Industry: {industry}  |  Doc ID: {doc_id}"))
#     blocks.append(make_paragraph("─" * 40))

#     for line in content.split("\n"):
#         if not line.strip():
#             continue
#         if line.startswith("## "):
#             blocks.append(make_heading(line[3:], 2))
#         elif line.startswith("# "):
#             blocks.append(make_heading(line[2:], 1))
#         elif line.startswith("### "):
#             blocks.append(make_heading(line[4:], 3))
#         else:
#             # Split long lines
#             for i in range(0, len(line), 1999):
#                 blocks.append(make_paragraph(line[i:i+1999]))

#         if len(blocks) > 95:  # Notion limit is 100 blocks per request
#             break

#     payload = {
#         "parent": {"database_id": database_id},
#         "properties": {
#             "Name": {
#                 "title": [{"text": {"content": f"{doc_type} — {dept}"}}]
#             },
#         },
#         "children": blocks[:95],
#     }

#     try:
#         r = requests.post(
#             f"{NOTION_API_URL}/pages",
#             headers=notion_headers(token),
#             json=payload,
#             timeout=30,
#         )
#         if r.status_code == 200:
#             page = r.json()
#             return True, page.get("url", ""), page.get("id", "")
#         else:
#             return False, r.text, ""
#     except Exception as e:
#         return False, str(e), ""


# # ============================================
# # DOWNLOAD HELPERS
# # ============================================

# def doc_to_markdown(doc: dict) -> str:
#     content = doc.get("generated_content", "")
#     meta = doc.get("metadata", {})
#     header = f"""---
# Document Type : {doc.get('document_type','')}
# Department    : {doc.get('department','')}
# Industry      : {doc.get('industry','')}
# Status        : {meta.get('doc_status','Draft')}
# Word Count    : {meta.get('word_count','N/A')}
# Reading Time  : {meta.get('reading_time_minutes','N/A')} min
# Generated At  : {doc.get('created_at','')[:16]}
# ---

# """
#     return header + content


# def doc_to_txt(doc: dict) -> str:
#     content = doc.get("generated_content", "")
#     # Strip markdown symbols
#     import re
#     content = re.sub(r"#{1,6}\s", "", content)
#     content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
#     content = re.sub(r"\*(.*?)\*", r"\1", content)
#     content = re.sub(r"`(.*?)`", r"\1", content)
#     return content


# def doc_to_html(doc: dict) -> str:
#     import re
#     content = doc.get("generated_content", "")
#     dept     = doc.get("department", "")
#     doc_type = doc.get("document_type", "")
#     meta     = doc.get("metadata", {})

#     def md_to_html(text):
#         text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
#         text = re.sub(r"^## (.+)$",  r"<h2>\1</h2>", text, flags=re.MULTILINE)
#         text = re.sub(r"^# (.+)$",   r"<h1>\1</h1>", text, flags=re.MULTILINE)
#         text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
#         text = re.sub(r"\*(.+?)\*",     r"<em>\1</em>", text)
#         text = re.sub(r"\n\n", r"</p><p>", text)
#         return f"<p>{text}</p>"

#     return f"""<!DOCTYPE html>
# <html>
# <head>
#   <meta charset="UTF-8">
#   <title>{doc_type} — {dept}</title>
#   <style>
#     body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.7; }}
#     h1 {{ color: #1e3c72; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
#     h2 {{ color: #2a5298; margin-top: 30px; }}
#     h3 {{ color: #555; }}
#     .meta {{ background: #f5f7fa; padding: 15px; border-radius: 8px; margin-bottom: 30px; font-size: 0.9rem; }}
#     .meta span {{ margin-right: 20px; }}
#   </style>
# </head>
# <body>
#   <h1>{doc_type} — {dept}</h1>
#   <div class="meta">
#     <span>🏢 {doc.get('industry','SaaS')}</span>
#     <span>📋 {meta.get('doc_status','Draft')}</span>
#     <span>📝 {meta.get('word_count','N/A')} words</span>
#     <span>⏱️ {meta.get('reading_time_minutes','N/A')} min read</span>
#   </div>
#   {md_to_html(content)}
# </body>
# </html>"""


# # ============================================
# # PAGE CONFIGURATION
# # ============================================
# st.set_page_config(
#     page_title="DocForgeHub - AI Document Generator",
#     page_icon="📄",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # ============================================
# # CUSTOM CSS
# # ============================================
# def load_custom_css():
#     st.markdown("""
#         <style>
#         @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
#         * { font-family: 'Inter', sans-serif; }
#         .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
#         [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%); }
#         .custom-card {
#             background: white; padding: 25px; border-radius: 15px;
#             box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
#             border-left: 5px solid #4CAF50;
#         }
#         .doc-card {
#             background: white; padding: 20px; border-radius: 12px;
#             box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 15px;
#             border: 2px solid #e0e0e0; transition: all 0.3s ease;
#         }
#         .doc-card:hover { border-color: #4CAF50; box-shadow: 0 4px 12px rgba(76,175,80,0.3); }
#         .main-header {
#             font-size: 2.5rem; font-weight: 700; color: #1e3c72;
#             margin-bottom: 10px; text-align: center;
#         }
#         .sub-header {
#             font-size: 1.8rem; font-weight: 600; color: #2a5298;
#             margin-top: 30px; margin-bottom: 20px;
#             border-bottom: 3px solid #4CAF50; padding-bottom: 10px;
#         }
#         .stat-box {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white; padding: 20px; border-radius: 12px;
#             text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
#         }
#         .stat-number { font-size: 2.5rem; font-weight: 700; margin-bottom: 5px; }
#         .stat-label { font-size: 0.9rem; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }
#         .success-box {
#             background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
#             color: white; padding: 20px; border-radius: 12px;
#             margin: 20px 0; text-align: center; font-weight: 600;
#         }
#         .info-box {
#             background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
#             color: white; padding: 20px; border-radius: 12px; margin: 20px 0;
#         }
#         .warning-box {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white; padding: 20px; border-radius: 12px; margin: 20px 0;
#         }
#         .stButton>button {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white; border: none; border-radius: 8px;
#             padding: 12px 30px; font-weight: 600; font-size: 1rem;
#             transition: all 0.3s ease; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
#         }
#         .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.3); }
#         .tag {
#             display: inline-block; background: #e3f2fd; color: #1976d2;
#             padding: 5px 12px; border-radius: 20px; font-size: 0.85rem;
#             margin-right: 8px; margin-bottom: 8px; font-weight: 500;
#         }
#         .doc-type-badge {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white; padding: 5px 15px; border-radius: 20px;
#             font-size: 0.8rem; font-weight: 600; display: inline-block;
#         }
#         .status-published {
#             background: #4CAF50; color: white; padding: 5px 12px;
#             border-radius: 15px; font-size: 0.8rem; font-weight: 600;
#         }
#         .status-draft {
#             background: #FF9800; color: white; padding: 5px 12px;
#             border-radius: 15px; font-size: 0.8rem; font-weight: 600;
#         }
#         .custom-divider {
#             height: 3px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
#             border: none; margin: 30px 0; border-radius: 5px;
#         }
#         .question-block {
#             background: #f8f9ff; border-left: 4px solid #667eea;
#             padding: 15px 20px; border-radius: 8px; margin-bottom: 15px;
#         }
#         </style>
#     """, unsafe_allow_html=True)

# # ============================================
# # SESSION STATE INIT
# # ============================================
# def init_session():
#     defaults = {
#         "current_page": "Home",
#         "generation_step": 1,
#         "selected_industry": "SaaS",
#         "selected_department": None,
#         "selected_doc_type": None,
#         "question_answers": {},
#         "last_generated_doc": None,
#         "departments_cache": None,
#         "doc_types_cache": None,
#         "questionnaire_cache": {},
#     }
#     for k, v in defaults.items():
#         if k not in st.session_state:
#             st.session_state[k] = v

# # ============================================
# # CACHED API CALLS
# # ============================================
# @st.cache_data(ttl=300)
# def fetch_departments():
#     data = api_get("/templates/departments")
#     if data:
#         return data.get("departments", [])
#     return [
#         "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
#         "Engineering & Operations", "Product & Design", "Marketing & Content",
#         "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
#         "Platform & Infrastructure Operation", "Data & Analytics",
#         "QA & Testing", "Security & Information Assurance"
#     ]

# @st.cache_data(ttl=300)
# def fetch_document_types():
#     data = api_get("/templates/document-types")
#     if data:
#         return data.get("document_types", [])
#     return ["SOP", "Policy", "Proposal", "SOW", "Incident Report",
#             "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"]

# @st.cache_data(ttl=300)
# def fetch_questionnaire(department: str, document_type: str):
#     data = api_get("/questionnaires/by-type", params={
#         "department": department,
#         "document_type": document_type
#     })
#     if data and "questions" in data:
#         return data["questions"]
#     return []

# @st.cache_data(ttl=60)
# def fetch_stats():
#     return api_get("/system/stats")

# @st.cache_data(ttl=30)
# def fetch_documents(department=None, document_type=None):
#     params = {}
#     if department: params["department"] = department
#     if document_type: params["document_type"] = document_type
#     return api_get("/documents/", params=params) or []

# # ============================================
# # SIDEBAR
# # ============================================
# def render_sidebar():
#     with st.sidebar:
#         st.markdown("<h1 style='color:white;text-align:center;margin-bottom:20px;'>📄 DocForgeHub</h1>", unsafe_allow_html=True)

#         # Backend health check
#         health = api_get("/system/health")
#         if health and health.get("database") == "connected":
#             st.markdown("<div style='background:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;font-size:0.85rem;margin-bottom:15px;'>🟢 Backend Connected</div>", unsafe_allow_html=True)
#         else:
#             st.markdown("<div style='background:#f44336;padding:8px;border-radius:8px;text-align:center;color:white;font-size:0.85rem;margin-bottom:15px;'>🔴 Backend Offline</div>", unsafe_allow_html=True)

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,0.3);'>", unsafe_allow_html=True)

#         pages = {
#             "🏠 Home": "Home",
#             "✨ Generate Document": "Generate",
#             "📚 Document Library": "Library",
#             "🗂 Templates": "Templates",
#             "❓ Questionnaires": "Questionnaires",
#             "🚀 Publish to Notion": "Notion",
#             "📊 System Stats": "Stats",
#         }

#         for label, key in pages.items():
#             if st.button(label, key=f"nav_{key}", use_container_width=True):
#                 st.session_state.current_page = key
#                 st.rerun()

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,0.3);margin:20px 0;'>", unsafe_allow_html=True)

#         # Live stats from DB
#         stats = fetch_stats()
#         if stats:
#             st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
#             st.metric("Templates", stats.get("templates", 0))
#             st.metric("Documents", stats.get("documents_generated", 0))
#             st.metric("Jobs Done", stats.get("jobs_completed", 0))

#         st.markdown("""
#             <div style='color:rgba(255,255,255,0.7);text-align:center;font-size:0.8rem;margin-top:30px;'>
#                 <p>Powered by Azure OpenAI + LangChain</p>
#                 <p>© 2026 DocForgeHub</p>
#             </div>
#         """, unsafe_allow_html=True)

# # ============================================
# # PAGE: HOME
# # ============================================
# def render_home():
#     st.markdown("<h1 class='main-header'>🚀 Welcome to DocForgeHub</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;font-size:1.2rem;color:#555;margin-bottom:30px;'>AI-Powered Enterprise Document Generation — Backed by PostgreSQL + Azure OpenAI</p>", unsafe_allow_html=True)

#     stats = fetch_stats()

#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('templates',0) if stats else 0}</div><div class='stat-label'>Templates</div></div>", unsafe_allow_html=True)
#     with col2:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('documents_generated',0) if stats else 0}</div><div class='stat-label'>Documents</div></div>", unsafe_allow_html=True)
#     with col3:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('departments',0) if stats else 0}</div><div class='stat-label'>Departments</div></div>", unsafe_allow_html=True)
#     with col4:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('document_types',0) if stats else 0}</div><div class='stat-label'>Doc Types</div></div>", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.markdown("""<div class='custom-card'><h3 style='color:#1e3c72;'>🤖 AI Generation</h3>
#         <p style='color:#555;'>Azure OpenAI + LangChain generates professional documents with your exact company context.</p></div>""", unsafe_allow_html=True)
#     with col2:
#         st.markdown("""<div class='custom-card' style='border-left-color:#764ba2'><h3 style='color:#1e3c72;'>🗄️ PostgreSQL Backend</h3>
#         <p style='color:#555;'>All templates, questionnaires, and documents stored in your PostgreSQL database.</p></div>""", unsafe_allow_html=True)
#     with col3:
#         st.markdown("""<div class='custom-card' style='border-left-color:#4facfe'><h3 style='color:#1e3c72;'>📋 Smart Q&A</h3>
#         <p style='color:#555;'>Dynamic questions per department × document type, loaded from your database.</p></div>""", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     col1, col2 = st.columns(2)
#     with col1:
#         if st.button("✨ Generate New Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.session_state.generation_step = 1
#             st.rerun()
#     with col2:
#         if st.button("📚 View Document Library", use_container_width=True):
#             st.session_state.current_page = "Library"
#             st.rerun()

#     # Recent documents
#     docs = fetch_documents()
#     if docs:
#         st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
#         for doc in docs[:5]:
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <div style='display:flex;justify-content:space-between;align-items:center;'>
#                     <div>
#                         <b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']} — {doc['department']}</b><br>
#                         <span style='color:#999;font-size:0.85rem;'>Industry: {doc['industry']} | Created: {doc['created_at'][:16]}</span>
#                     </div>
#                     <span class='status-{"published" if doc["status"]=="completed" else "draft"}'>{doc['status'].upper()}</span>
#                 </div>
#             </div>""", unsafe_allow_html=True)

# # ============================================
# # PAGE: GENERATE DOCUMENT
# # ============================================
# def render_generate():
#     st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)

#     step = st.session_state.generation_step
#     progress = (step - 1) / 3
#     st.progress(progress)

#     steps_labels = ["📋 Select Type", "❓ Answer Questions", "🎉 Generate & Review"]
#     cols = st.columns(3)
#     for idx, (col, label) in enumerate(zip(cols, steps_labels)):
#         with col:
#             if idx + 1 < step:
#                 st.markdown(f"<p style='text-align:center;color:#4CAF50;font-weight:600;'>✅ {label}</p>", unsafe_allow_html=True)
#             elif idx + 1 == step:
#                 st.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>▶️ {label}</p>", unsafe_allow_html=True)
#             else:
#                 st.markdown(f"<p style='text-align:center;color:#999;'>⏺️ {label}</p>", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── STEP 1: Select Type ──
#     if step == 1:
#         st.markdown("<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True)

#         departments = fetch_departments()
#         doc_types   = fetch_document_types()

#         col1, col2, col3 = st.columns(3)
#         with col1:
#             industry = st.selectbox("🏢 Industry", ["SaaS"], key="s1_industry")
#         with col2:
#             department = st.selectbox("🏛️ Department", departments, key="s1_dept")
#         with col3:
#             doc_type = st.selectbox("📄 Document Type", doc_types, key="s1_type")

#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("➡️ Next: Answer Questions", use_container_width=True):
#             st.session_state.selected_industry   = industry
#             st.session_state.selected_department = department
#             st.session_state.selected_doc_type   = doc_type
#             st.session_state.generation_step     = 2
#             st.rerun()

#     # ── STEP 2: Answer Questions from DB ──
#     elif step == 2:
#         st.markdown("<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True)

#         dept     = st.session_state.selected_department
#         doc_type = st.session_state.selected_doc_type

#         st.markdown(f"""
#         <div class='info-box'>
#             <strong>Generating:</strong> {doc_type} for <strong>{dept}</strong>
#         </div>""", unsafe_allow_html=True)

#         # Fetch questions from DB
#         questions = fetch_questionnaire(dept, doc_type)

#         if not questions:
#             st.warning("No questionnaire found in DB. Using default questions.")
#             questions = [
#                 {"id": "company_name",    "question": "What is your company name?",            "type": "text",     "required": True,  "options": []},
#                 {"id": "company_size",    "question": "Company size?",                          "type": "select",   "required": True,  "options": ["1-10","11-50","51-200","201-500","1000+"]},
#                 {"id": "primary_product", "question": "What is your primary SaaS product?",     "type": "text",     "required": True,  "options": []},
#                 {"id": "specific_focus",  "question": "What specific topic should this cover?", "type": "text",     "required": False, "options": []},
#                 {"id": "tools_used",      "question": "Tools/systems used?",                    "type": "text",     "required": False, "options": []},
#                 {"id": "tone_preference", "question": "Preferred document tone?",               "type": "select",   "required": False, "options": ["Professional & Formal","Professional & Friendly","Technical & Detailed","Executive-level & Concise"]},
#                 {"id": "additional_context","question":"Any additional context?",               "type": "textarea", "required": False, "options": []},
#             ]

#         answers = {}

#         # Group questions by category
#         categories = {}
#         for q in questions:
#             cat = q.get("category", "common")
#             categories.setdefault(cat, []).append(q)

#         category_labels = {
#             "common": "📋 General Questions",
#             "document_type_specific": f"📄 {doc_type} Specific Questions",
#             "department_specific": f"🏛️ {dept} Specific Questions",
#         }

#         for cat_key, cat_questions in categories.items():
#             if cat_questions:
#                 st.markdown(f"<h3 style='color:#2a5298;margin-top:25px;'>{category_labels.get(cat_key, cat_key)}</h3>", unsafe_allow_html=True)

#                 for q in cat_questions:
#                     q_id   = q.get("id", "")
#                     q_text = q.get("question", "")
#                     q_type = q.get("type", "text")
#                     q_req  = q.get("required", False)
#                     q_opts = q.get("options", [])
#                     q_placeholder = q.get("placeholder", "")

#                     label = f"{'🔴 ' if q_req else ''}{q_text}"

#                     st.markdown(f"<div class='question-block'><b style='color:#1e3c72;'>{label}</b></div>", unsafe_allow_html=True)

#                     widget_key = f"q_{q_id}"

#                     if q_type == "text":
#                         answers[q_id] = st.text_input("", key=widget_key, placeholder=q_placeholder or "", label_visibility="collapsed")

#                     elif q_type == "textarea":
#                         answers[q_id] = st.text_area("", key=widget_key, height=100, placeholder=q_placeholder or "", label_visibility="collapsed")

#                     elif q_type == "select" and q_opts:
#                         answers[q_id] = st.selectbox("", ["(select)"] + q_opts, key=widget_key, label_visibility="collapsed")

#                     elif q_type == "multi_select" and q_opts:
#                         answers[q_id] = st.multiselect("", q_opts, key=widget_key, label_visibility="collapsed")

#                     else:
#                         answers[q_id] = st.text_input("", key=widget_key, label_visibility="collapsed")

#         st.markdown("<br>", unsafe_allow_html=True)
#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("⬅️ Back", use_container_width=True):
#                 st.session_state.generation_step = 1
#                 st.rerun()
#         with col2:
#             if st.button("🚀 Generate Document", use_container_width=True):
#                 # Validate required
#                 missing = []
#                 for q in questions:
#                     if q.get("required") and not answers.get(q.get("id", "")):
#                         missing.append(q.get("question", ""))
#                 if missing:
#                     for m in missing:
#                         st.error(f"Required: {m}")
#                 else:
#                     # Clean answers — remove empty/default
#                     clean_answers = {k: v for k, v in answers.items() if v and v != "(select)"}
#                     st.session_state.question_answers = clean_answers
#                     st.session_state.generation_step  = 3
#                     st.rerun()

#     # ── STEP 3: Generate via API ──
#     elif step == 3:
#         st.markdown("<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True)

#         if st.session_state.last_generated_doc is None:
#             progress_bar = st.progress(0)
#             status_text  = st.empty()

#             phases = [
#                 ("Connecting to FastAPI backend...", 0.15),
#                 ("Loading template from PostgreSQL...", 0.30),
#                 ("Loading questionnaire from DB...", 0.45),
#                 ("Building AI prompt...", 0.60),
#                 ("Calling Azure OpenAI...", 0.80),
#                 ("Saving document to database...", 0.95),
#             ]

#             for text, pct in phases:
#                 status_text.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>{text}</p>", unsafe_allow_html=True)
#                 progress_bar.progress(pct)
#                 time.sleep(0.4)

#             # Call FastAPI
#             payload = {
#                 "industry":         st.session_state.selected_industry,
#                 "department":       st.session_state.selected_department,
#                 "document_type":    st.session_state.selected_doc_type,
#                 "question_answers": st.session_state.question_answers,
#             }

#             result = api_post("/documents/generate", payload)

#             progress_bar.progress(1.0)
#             status_text.empty()
#             progress_bar.empty()

#             if result:
#                 st.session_state.last_generated_doc = result
#             else:
#                 st.error("Document generation failed. Check FastAPI logs.")
#                 if st.button("⬅️ Try Again"):
#                     st.session_state.generation_step = 2
#                     st.rerun()
#                 return

#         doc = st.session_state.last_generated_doc

#         st.markdown(f"""
#         <div class='success-box'>
#             ✅ Document Generated! ID: {doc.get('document_id')} | Job: {doc.get('job_id','')[:8]}...
#         </div>""", unsafe_allow_html=True)

#         # Show document details
#         st.markdown("<h3 style='color:#1e3c72;margin-top:30px;'>📄 Document Preview</h3>", unsafe_allow_html=True)

#         st.markdown(f"""
#         <div class='doc-card'>
#             <p><span class='doc-type-badge'>{st.session_state.selected_doc_type}</span></p>
#             <p style='color:#666;'><strong>Department:</strong> {st.session_state.selected_department}</p>
#             <p style='color:#666;'><strong>Industry:</strong> {st.session_state.selected_industry}</p>
#             <p style='color:#666;'><strong>Document ID:</strong> {doc.get('document_id')}</p>
#             <p style='color:#666;'><strong>Job ID:</strong> {doc.get('job_id')}</p>
#         </div>""", unsafe_allow_html=True)

#         with st.expander("📖 View Full Generated Content", expanded=True):
#             content = doc.get("document", "No content returned.")
#             st.markdown(content)

#         with st.expander("📋 Your Answers Submitted"):
#             st.json(st.session_state.question_answers)

#         # Download buttons - multiple formats
#         full_doc = api_get(f"/documents/{doc.get('document_id')}")
#         if full_doc:
#             st.markdown("<h3 style='color:#1e3c72;margin-top:20px;'>⬇️ Download Document</h3>", unsafe_allow_html=True)
#             col1, col2, col3 = st.columns(3)
#             fname_base = f"{st.session_state.selected_doc_type}_{st.session_state.selected_department.replace(' ','_').replace('&','and')}"

#             with col1:
#                 st.download_button(
#                     label="📄 Download .md",
#                     data=doc_to_markdown(full_doc),
#                     file_name=f"{fname_base}.md",
#                     mime="text/markdown",
#                     use_container_width=True,
#                 )
#             with col2:
#                 st.download_button(
#                     label="📝 Download .txt",
#                     data=doc_to_txt(full_doc),
#                     file_name=f"{fname_base}.txt",
#                     mime="text/plain",
#                     use_container_width=True,
#                 )
#             with col3:
#                 st.download_button(
#                     label="🌐 Download .html",
#                     data=doc_to_html(full_doc),
#                     file_name=f"{fname_base}.html",
#                     mime="text/html",
#                     use_container_width=True,
#                 )

#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("🔄 Generate Another", use_container_width=True):
#                 st.session_state.generation_step    = 1
#                 st.session_state.last_generated_doc = None
#                 st.session_state.question_answers   = {}
#                 st.rerun()
#         with col2:
#             if st.button("📚 Go to Library", use_container_width=True):
#                 st.session_state.current_page       = "Library"
#                 st.session_state.generation_step    = 1
#                 st.session_state.last_generated_doc = None
#                 st.rerun()

# # ============================================
# # PAGE: DOCUMENT LIBRARY
# # ============================================
# def render_library():
#     st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         f_dept = st.selectbox("Filter by Department", ["All"] + departments, key="lib_dept")
#     with col2:
#         f_type = st.selectbox("Filter by Document Type", ["All"] + doc_types, key="lib_type")
#     with col3:
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("🔄 Refresh", use_container_width=True):
#             fetch_documents.clear()
#             st.rerun()

#     docs = fetch_documents(
#         department=f_dept if f_dept != "All" else None,
#         document_type=f_type if f_type != "All" else None,
#     )

#     st.markdown(f"<p style='color:#666;'><strong>{len(docs)}</strong> documents found</p>", unsafe_allow_html=True)
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     if not docs:
#         st.markdown("""<div class='info-box'><h3>📭 No Documents Found</h3>
#         <p>Generate your first document using the Generate page.</p></div>""", unsafe_allow_html=True)
#         if st.button("✨ Generate Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
#         return

#     for doc in docs:
#         with st.container():
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <div style='display:flex;justify-content:space-between;align-items:start;'>
#                     <div>
#                         <b style='color:#1e3c72;font-size:1.1rem;'>#{doc['id']} — {doc['document_type']}</b><br>
#                         <span style='color:#666;'>🏛️ {doc['department']} | 🏢 {doc['industry']}</span><br>
#                         <span style='color:#999;font-size:0.85rem;'>📅 {doc['created_at'][:16]}</span>
#                     </div>
#                     <span class='{"status-published" if doc["status"]=="completed" else "status-draft"}'>{doc['status'].upper()}</span>
#                 </div>
#             </div>""", unsafe_allow_html=True)

#             col1, col2 = st.columns([3, 1])
#             with col1:
#                 if st.button(f"📖 View Document #{doc['id']}", key=f"view_{doc['id']}", use_container_width=True):
#                     full = api_get(f"/documents/{doc['id']}")
#                     if full:
#                         with st.expander(f"📄 Document #{doc['id']} — Full View", expanded=True):
#                             st.markdown(f"**Type:** {full['document_type']}  |  **Department:** {full['department']}  |  **Industry:** {full['industry']}")
#                             if full.get("metadata"):
#                                 meta = full["metadata"]
#                                 st.markdown(f"**Word Count:** {meta.get('word_count','N/A')}  |  **Reading Time:** {meta.get('reading_time_minutes','N/A')} min  |  **Status:** {meta.get('doc_status','N/A')}")
#                             st.markdown("---")
#                             st.markdown(full.get("generated_content", "No content"))
#             with col2:
#                 if st.button(f"🗑️ Delete #{doc['id']}", key=f"del_{doc['id']}", use_container_width=True):
#                     result = api_delete(f"/documents/{doc['id']}")
#                     if result:
#                         st.success("Deleted!")
#                         fetch_documents.clear()
#                         time.sleep(1)
#                         st.rerun()

# # ============================================
# # PAGE: TEMPLATES
# # ============================================
# def render_templates():
#     st.markdown("<h1 class='main-header'>🗂 Templates</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;color:#555;'>All templates seeded from content.json via PostgreSQL</p>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2 = st.columns(2)
#     with col1:
#         f_dept = st.selectbox("Filter Department", ["All"] + departments, key="tmpl_dept")
#     with col2:
#         f_type = st.selectbox("Filter Document Type", ["All"] + doc_types, key="tmpl_type")

#     params = {}
#     if f_dept != "All": params["department"] = f_dept
#     if f_type != "All": params["document_type"] = f_type

#     templates = api_get("/templates/", params=params) or []

#     st.markdown(f"<p style='color:#666;'><strong>{len(templates)}</strong> templates found</p>", unsafe_allow_html=True)
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     for tmpl in templates:
#         with st.expander(f"🗂 {tmpl['department']} — {tmpl['document_type']}  (v{tmpl['version']})"):
#             full = api_get(f"/templates/{tmpl['id']}")
#             if full and full.get("structure"):
#                 sections = full["structure"].get("sections", [])
#                 st.markdown(f"**Total Sections:** {len(sections)}")
#                 for i, s in enumerate(sections, 1):
#                     st.markdown(f"  `{i}.` {s}")
#             st.markdown(f"**Active:** {'✅' if tmpl.get('is_active') else '❌'}  |  **Created:** {tmpl.get('created_at','')[:10]}")

# # ============================================
# # PAGE: QUESTIONNAIRES
# # ============================================
# def render_questionnaires():
#     st.markdown("<h1 class='main-header'>❓ Questionnaires</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;color:#555;'>All Q&A seeded from Question_Answer.json via PostgreSQL</p>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2 = st.columns(2)
#     with col1:
#         dept = st.selectbox("Department", departments, key="qa_dept")
#     with col2:
#         doc_type = st.selectbox("Document Type", doc_types, key="qa_type")

#     if st.button("🔍 Load Questions", use_container_width=True):
#         questions = fetch_questionnaire(dept, doc_type)

#         if not questions:
#             st.warning("No questionnaire found for this combination.")
#         else:
#             st.markdown(f"<div class='success-box'>✅ {len(questions)} questions loaded for {dept} — {doc_type}</div>", unsafe_allow_html=True)

#             categories = {}
#             for q in questions:
#                 cat = q.get("category", "common")
#                 categories.setdefault(cat, []).append(q)

#             for cat, qs in categories.items():
#                 st.markdown(f"<h3 style='color:#2a5298;margin-top:20px;'>{cat.replace('_',' ').title()} ({len(qs)} questions)</h3>", unsafe_allow_html=True)
#                 for q in qs:
#                     req_badge = "🔴 Required" if q.get("required") else "⚪ Optional"
#                     st.markdown(f"""
#                     <div class='question-block'>
#                         <b>{q.get('question','')}</b><br>
#                         <span style='color:#888;font-size:0.85rem;'>Type: {q.get('type','')} | {req_badge}</span>
#                         {f"<br><span style='color:#1976d2;font-size:0.8rem;'>💡 {q.get('used_in_prompt','')}</span>" if q.get('used_in_prompt') else ''}
#                     </div>""", unsafe_allow_html=True)

# # ============================================
# # PAGE: SYSTEM STATS
# # ============================================
# def render_stats():
#     st.markdown("<h1 class='main-header'>📊 System Statistics</h1>", unsafe_allow_html=True)

#     if st.button("🔄 Refresh Stats"):
#         fetch_stats.clear()
#         st.rerun()

#     stats = fetch_stats()
#     health = api_get("/system/health")

#     if health:
#         db_status = health.get("database", "unknown")
#         color = "#4CAF50" if db_status == "connected" else "#f44336"
#         st.markdown(f"<div style='background:{color};padding:15px;border-radius:10px;color:white;text-align:center;font-weight:600;margin-bottom:20px;'>Database: {db_status.upper()}</div>", unsafe_allow_html=True)

#     if stats:
#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.metric("📋 Templates",      stats.get("templates", 0))
#         with col2:
#             st.metric("❓ Questionnaires", stats.get("questionnaires", 0))
#         with col3:
#             st.metric("📄 Documents",      stats.get("documents_generated", 0))
#         with col4:
#             st.metric("⚙️ Total Jobs",     stats.get("total_jobs", 0))

#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.metric("✅ Jobs Completed", stats.get("jobs_completed", 0))
#         with col2:
#             st.metric("❌ Jobs Failed",    stats.get("jobs_failed", 0))
#         with col3:
#             st.metric("🏢 Departments",    stats.get("departments", 0))
#         with col4:
#             st.metric("📁 Document Types", stats.get("document_types", 0))

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # Recent jobs
#     st.markdown("<h2 class='sub-header'>⚙️ Recent Generation Jobs</h2>", unsafe_allow_html=True)
#     jobs = api_get("/documents/jobs") or []
#     if jobs:
#         df = pd.DataFrame(jobs)[["job_id", "status", "document_type", "department", "started_at"]]
#         df["job_id"] = df["job_id"].str[:12] + "..."
#         st.dataframe(df, use_container_width=True)
#     else:
#         st.info("No jobs yet.")

# # ============================================
# # PAGE: PUBLISH TO NOTION
# # ============================================
# def render_notion():
#     st.markdown("<h1 class='main-header'>🚀 Publish to Notion</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;font-size:1.1rem;color:#555;margin-bottom:30px;'>Connect your Notion workspace and publish documents directly</p>", unsafe_allow_html=True)

#     # ── Step 1: Notion credentials ──
#     st.markdown("<h2 class='sub-header'>🔑 Step 1: Notion Connection</h2>", unsafe_allow_html=True)

#     with st.expander("ℹ️ How to get your Notion API Token", expanded=False):
#         st.markdown("""
#         1. Go to **https://www.notion.so/my-integrations**
#         2. Click **"New Integration"** → give it a name like *DocForgeHub*
#         3. Copy the **Internal Integration Token** (starts with `secret_...`)
#         4. Open the Notion Database you want to publish to
#         5. Click **"..."** → **"Add connections"** → select your integration
#         6. Copy the **Database ID** from the URL:
#            `https://notion.so/YOUR_WORKSPACE/**DATABASE_ID**?v=...`
#         """)

#     col1, col2 = st.columns(2)
#     with col1:
#         notion_token = st.text_input(
#             "🔐 Notion Integration Token",
#             type="password",
#             placeholder="secret_xxxxxxxxxxxxxxxxxxxx",
#             key="notion_token",
#             help="Get from https://www.notion.so/my-integrations"
#         )
#     with col2:
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("🔍 Test Connection", use_container_width=True):
#             if not notion_token:
#                 st.error("Enter your Notion token first.")
#             else:
#                 ok, resp = notion_test_connection(notion_token)
#                 if ok:
#                     name = resp.get("name", resp.get("bot", {}).get("owner", {}).get("user", {}).get("name", "User"))
#                     st.success(f"✅ Connected as: {name}")
#                     st.session_state.notion_connected = True
#                 else:
#                     st.error(f"❌ Connection failed: {resp}")
#                     st.session_state.notion_connected = False

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── Step 2: Select Database ──
#     st.markdown("<h2 class='sub-header'>🗄️ Step 2: Select Target Database</h2>", unsafe_allow_html=True)

#     database_id = st.text_input(
#         "📋 Notion Database ID",
#         placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
#         key="notion_db_id",
#         help="Copy from your Notion database URL"
#     )

#     if notion_token and st.button("🔍 Auto-detect my Databases", use_container_width=True):
#         dbs = notion_get_databases(notion_token)
#         if dbs:
#             st.markdown(f"<div class='info-box'>Found <strong>{len(dbs)}</strong> databases in your workspace:</div>", unsafe_allow_html=True)
#             for db in dbs:
#                 st.code(f"{db['name']}  →  ID: {db['id']}")
#         else:
#             st.warning("No databases found. Make sure you've shared databases with your integration.")

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── Step 3: Select Documents to Publish ──
#     st.markdown("<h2 class='sub-header'>📄 Step 3: Select Documents</h2>", unsafe_allow_html=True)

#     docs = fetch_documents()

#     if not docs:
#         st.markdown("""<div class='info-box'><h3>📭 No Documents Found</h3>
#         <p>Generate documents first, then publish them here.</p></div>""", unsafe_allow_html=True)
#         if st.button("✨ Generate Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
#         return

#     # Track published doc IDs in session
#     if "notion_published_ids" not in st.session_state:
#         st.session_state.notion_published_ids = {}

#     # Stats row
#     published_count = len(st.session_state.notion_published_ids)
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(docs)}</div><div class='stat-label'>Total Docs</div></div>", unsafe_allow_html=True)
#     with col2:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(docs)-published_count}</div><div class='stat-label'>Ready to Publish</div></div>", unsafe_allow_html=True)
#     with col3:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{published_count}</div><div class='stat-label'>Published</div></div>", unsafe_allow_html=True)

#     st.markdown("<br>", unsafe_allow_html=True)

#     # Publish ALL button
#     unpublished = [d for d in docs if str(d['id']) not in st.session_state.notion_published_ids]
#     if unpublished and st.button(f"🚀 Publish All ({len(unpublished)}) to Notion", use_container_width=True):
#         if not notion_token or not database_id:
#             st.error("❌ Please enter your Notion Token and Database ID first.")
#         else:
#             progress = st.progress(0)
#             status   = st.empty()
#             errors   = []

#             for idx, doc in enumerate(unpublished):
#                 status.markdown(f"<p style='text-align:center;color:#667eea;'>Publishing: {doc['document_type']} — {doc['department']}...</p>", unsafe_allow_html=True)

#                 full_doc = api_get(f"/documents/{doc['id']}")
#                 if full_doc:
#                     ok, url, page_id = notion_create_page(
#                         notion_token, database_id, full_doc,
#                         full_doc.get("generated_content", "")
#                     )
#                     if ok:
#                         st.session_state.notion_published_ids[str(doc['id'])] = {
#                             "url": url, "page_id": page_id,
#                             "title": f"{doc['document_type']} — {doc['department']}"
#                         }
#                     else:
#                         errors.append(f"Doc #{doc['id']}: {url}")

#                 progress.progress((idx + 1) / len(unpublished))

#             status.empty()
#             if errors:
#                 st.error(f"Some failed:\n" + "\n".join(errors))
#             else:
#                 st.markdown(f"<div class='success-box'>🎉 All {len(unpublished)} documents published to Notion!</div>", unsafe_allow_html=True)
#             st.rerun()

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # Individual document list
#     for doc in docs:
#         doc_id     = str(doc['id'])
#         is_pub     = doc_id in st.session_state.notion_published_ids
#         pub_info   = st.session_state.notion_published_ids.get(doc_id, {})

#         with st.container():
#             col1, col2, col3 = st.columns([4, 2, 2])

#             with col1:
#                 st.markdown(f"""
#                 <div class='doc-card' style='margin-bottom:5px;'>
#                     <b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']}</b><br>
#                     <span style='color:#666;font-size:0.9rem;'>🏛️ {doc['department']} | 📅 {doc['created_at'][:10]}</span>
#                     {f"<br><a href='{pub_info.get('url','#')}' target='_blank' style='color:#4CAF50;font-size:0.85rem;'>🔗 View in Notion</a>" if is_pub else ''}
#                 </div>""", unsafe_allow_html=True)

#             with col2:
#                 if is_pub:
#                     st.markdown("<div style='background:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;font-weight:600;margin-top:8px;'>✅ Published</div>", unsafe_allow_html=True)
#                 else:
#                     if st.button(f"🚀 Publish #{doc['id']}", key=f"pub_{doc['id']}", use_container_width=True):
#                         if not notion_token or not database_id:
#                             st.error("Enter Notion Token and Database ID first.")
#                         else:
#                             with st.spinner("Publishing..."):
#                                 full_doc = api_get(f"/documents/{doc['id']}")
#                                 if full_doc:
#                                     ok, url, page_id = notion_create_page(
#                                         notion_token, database_id, full_doc,
#                                         full_doc.get("generated_content", "")
#                                     )
#                                     if ok:
#                                         st.session_state.notion_published_ids[doc_id] = {
#                                             "url": url, "page_id": page_id,
#                                             "title": f"{doc['document_type']} — {doc['department']}"
#                                         }
#                                         st.success(f"✅ Published!")
#                                         st.rerun()
#                                     else:
#                                         st.error(f"Failed: {url}")

#             with col3:
#                 # Download from library too
#                 if st.button(f"⬇️ Download #{doc['id']}", key=f"dl_{doc['id']}", use_container_width=True):
#                     full_doc = api_get(f"/documents/{doc['id']}")
#                     if full_doc:
#                         st.session_state[f"download_doc_{doc_id}"] = full_doc

#                 if st.session_state.get(f"download_doc_{doc_id}"):
#                     full_doc  = st.session_state[f"download_doc_{doc_id}"]
#                     fname     = f"{doc['document_type']}_{doc['department'].replace(' ','_').replace('&','and')}"
#                     st.download_button("📄 .md",   doc_to_markdown(full_doc), f"{fname}.md",   "text/markdown",    key=f"md_{doc_id}")
#                     st.download_button("📝 .txt",  doc_to_txt(full_doc),      f"{fname}.txt",  "text/plain",       key=f"txt_{doc_id}")
#                     st.download_button("🌐 .html", doc_to_html(full_doc),     f"{fname}.html", "text/html",        key=f"html_{doc_id}")

#     # Published history
#     if st.session_state.notion_published_ids:
#         st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
#         st.markdown("<h2 class='sub-header'>✅ Published to Notion</h2>", unsafe_allow_html=True)
#         for doc_id, info in st.session_state.notion_published_ids.items():
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <b style='color:#1e3c72;'>{info.get('title','Document')}</b><br>
#                 <a href='{info.get('url','#')}' target='_blank' style='color:#4CAF50;'>🔗 Open in Notion</a>
#                 <span style='color:#999;font-size:0.8rem;margin-left:15px;'>Page ID: {info.get('page_id','')[:8]}...</span>
#             </div>""", unsafe_allow_html=True)


# # ============================================
# # MAIN
# # ============================================
# def main():
#     load_custom_css()
#     init_session()
#     render_sidebar()

#     page = st.session_state.current_page

#     if page == "Home":           render_home()
#     elif page == "Generate":     render_generate()
#     elif page == "Library":      render_library()
#     elif page == "Templates":    render_templates()
#     elif page == "Questionnaires": render_questionnaires()
#     elif page == "Notion":           render_notion()
#     elif page == "Stats":            render_stats()

# if __name__ == "__main__":
#     main()

#------------------------------------------------------------------
# import streamlit as st
# import pandas as pd
# from datetime import datetime
# import time
# import json
# import requests
# from typing import List, Dict, Optional

# # ============================================
# # CONFIGURATION
# # ============================================
# API_BASE_URL = "http://127.0.0.1:8000"

# def api_get(endpoint: str, params: dict = None):
#     try:
#         r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to backend. Make sure FastAPI is running: `python -m uvicorn main:app --reload`")
#         return None
#     except Exception as e:
#         st.error(f"❌ API Error: {str(e)}")
#         return None

# def api_post(endpoint: str, data: dict):
#     try:
#         r = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=60)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to backend.")
#         return None
#     except requests.exceptions.HTTPError as e:
#         st.error(f"❌ API Error {r.status_code}: {r.text}")
#         return None
#     except Exception as e:
#         st.error(f"❌ Error: {str(e)}")
#         return None

# def api_delete(endpoint: str):
#     try:
#         r = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except Exception as e:
#         st.error(f"❌ Delete failed: {str(e)}")
#         return None

# # ============================================
# # PAGE CONFIGURATION
# # ============================================
# st.set_page_config(
#     page_title="DocForgeHub - AI Document Generator",
#     page_icon="📄",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # ============================================
# # CUSTOM CSS
# # ============================================
# def load_custom_css():
#     st.markdown("""
#         <style>
#         @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
#         * { font-family: 'Inter', sans-serif; }
#         .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
#         [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%); }
#         .custom-card {
#             background: white; padding: 25px; border-radius: 15px;
#             box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
#             border-left: 5px solid #4CAF50;
#         }
#         .doc-card {
#             background: white; padding: 20px; border-radius: 12px;
#             box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 15px;
#             border: 2px solid #e0e0e0; transition: all 0.3s ease;
#         }
#         .doc-card:hover { border-color: #4CAF50; box-shadow: 0 4px 12px rgba(76,175,80,0.3); }
#         .main-header {
#             font-size: 2.5rem; font-weight: 700; color: #1e3c72;
#             margin-bottom: 10px; text-align: center;
#         }
#         .sub-header {
#             font-size: 1.8rem; font-weight: 600; color: #2a5298;
#             margin-top: 30px; margin-bottom: 20px;
#             border-bottom: 3px solid #4CAF50; padding-bottom: 10px;
#         }
#         .stat-box {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white; padding: 20px; border-radius: 12px;
#             text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
#         }
#         .stat-number { font-size: 2.5rem; font-weight: 700; margin-bottom: 5px; }
#         .stat-label { font-size: 0.9rem; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }
#         .success-box {
#             background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
#             color: white; padding: 20px; border-radius: 12px;
#             margin: 20px 0; text-align: center; font-weight: 600;
#         }
#         .info-box {
#             background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
#             color: white; padding: 20px; border-radius: 12px; margin: 20px 0;
#         }
#         .warning-box {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white; padding: 20px; border-radius: 12px; margin: 20px 0;
#         }
#         .stButton>button {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white; border: none; border-radius: 8px;
#             padding: 12px 30px; font-weight: 600; font-size: 1rem;
#             transition: all 0.3s ease; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
#         }
#         .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.3); }
#         .tag {
#             display: inline-block; background: #e3f2fd; color: #1976d2;
#             padding: 5px 12px; border-radius: 20px; font-size: 0.85rem;
#             margin-right: 8px; margin-bottom: 8px; font-weight: 500;
#         }
#         .doc-type-badge {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white; padding: 5px 15px; border-radius: 20px;
#             font-size: 0.8rem; font-weight: 600; display: inline-block;
#         }
#         .status-published {
#             background: #4CAF50; color: white; padding: 5px 12px;
#             border-radius: 15px; font-size: 0.8rem; font-weight: 600;
#         }
#         .status-draft {
#             background: #FF9800; color: white; padding: 5px 12px;
#             border-radius: 15px; font-size: 0.8rem; font-weight: 600;
#         }
#         .custom-divider {
#             height: 3px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
#             border: none; margin: 30px 0; border-radius: 5px;
#         }
#         .question-block {
#             background: #f8f9ff; border-left: 4px solid #667eea;
#             padding: 15px 20px; border-radius: 8px; margin-bottom: 15px;
#         }
#         </style>
#     """, unsafe_allow_html=True)

# # ============================================
# # SESSION STATE INIT
# # ============================================
# def init_session():
#     defaults = {
#         "current_page": "Home",
#         "generation_step": 1,
#         "selected_industry": "SaaS",
#         "selected_department": None,
#         "selected_doc_type": None,
#         "question_answers": {},
#         "last_generated_doc": None,
#         "departments_cache": None,
#         "doc_types_cache": None,
#         "questionnaire_cache": {},
#     }
#     for k, v in defaults.items():
#         if k not in st.session_state:
#             st.session_state[k] = v

# # ============================================
# # CACHED API CALLS
# # ============================================
# @st.cache_data(ttl=300)
# def fetch_departments():
#     data = api_get("/templates/departments")
#     if data:
#         return data.get("departments", [])
#     return [
#         "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
#         "Engineering & Operations", "Product & Design", "Marketing & Content",
#         "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
#         "Platform & Infrastructure Operation", "Data & Analytics",
#         "QA & Testing", "Security & Information Assurance"
#     ]

# @st.cache_data(ttl=300)
# def fetch_document_types():
#     data = api_get("/templates/document-types")
#     if data:
#         return data.get("document_types", [])
#     return ["SOP", "Policy", "Proposal", "SOW", "Incident Report",
#             "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"]

# @st.cache_data(ttl=300)
# def fetch_questionnaire(department: str, document_type: str):
#     data = api_get("/questionnaires/by-type", params={
#         "department": department,
#         "document_type": document_type
#     })
#     if data and "questions" in data:
#         return data["questions"]
#     return []

# @st.cache_data(ttl=60)
# def fetch_stats():
#     return api_get("/system/stats")

# @st.cache_data(ttl=30)
# def fetch_documents(department=None, document_type=None):
#     params = {}
#     if department: params["department"] = department
#     if document_type: params["document_type"] = document_type
#     return api_get("/documents/", params=params) or []

# # ============================================
# # SIDEBAR
# # ============================================
# def render_sidebar():
#     with st.sidebar:
#         st.markdown("<h1 style='color:white;text-align:center;margin-bottom:20px;'>📄 DocForgeHub</h1>", unsafe_allow_html=True)

#         # Backend health check
#         health = api_get("/system/health")
#         if health and health.get("database") == "connected":
#             st.markdown("<div style='background:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;font-size:0.85rem;margin-bottom:15px;'>🟢 Backend Connected</div>", unsafe_allow_html=True)
#         else:
#             st.markdown("<div style='background:#f44336;padding:8px;border-radius:8px;text-align:center;color:white;font-size:0.85rem;margin-bottom:15px;'>🔴 Backend Offline</div>", unsafe_allow_html=True)

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,0.3);'>", unsafe_allow_html=True)

#         pages = {
#             "🏠 Home": "Home",
#             "✨ Generate Document": "Generate",
#             "📚 Document Library": "Library",
#             "🗂 Templates": "Templates",
#             "❓ Questionnaires": "Questionnaires",
#             "📊 System Stats": "Stats",
#         }

#         for label, key in pages.items():
#             if st.button(label, key=f"nav_{key}", use_container_width=True):
#                 st.session_state.current_page = key
#                 st.rerun()

#         st.markdown("<hr style='border:1px solid rgba(255,255,255,0.3);margin:20px 0;'>", unsafe_allow_html=True)

#         # Live stats from DB
#         stats = fetch_stats()
#         if stats:
#             st.markdown("<h3 style='color:white;'>📊 Live Stats</h3>", unsafe_allow_html=True)
#             st.metric("Templates", stats.get("templates", 0))
#             st.metric("Documents", stats.get("documents_generated", 0))
#             st.metric("Jobs Done", stats.get("jobs_completed", 0))

#         st.markdown("""
#             <div style='color:rgba(255,255,255,0.7);text-align:center;font-size:0.8rem;margin-top:30px;'>
#                 <p>Powered by Azure OpenAI + LangChain</p>
#                 <p>© 2026 DocForgeHub</p>
#             </div>
#         """, unsafe_allow_html=True)

# # ============================================
# # PAGE: HOME
# # ============================================
# def render_home():
#     st.markdown("<h1 class='main-header'>🚀 Welcome to DocForgeHub</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;font-size:1.2rem;color:#555;margin-bottom:30px;'>AI-Powered Enterprise Document Generation — Backed by PostgreSQL + Azure OpenAI</p>", unsafe_allow_html=True)

#     stats = fetch_stats()

#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('templates',0) if stats else 0}</div><div class='stat-label'>Templates</div></div>", unsafe_allow_html=True)
#     with col2:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('documents_generated',0) if stats else 0}</div><div class='stat-label'>Documents</div></div>", unsafe_allow_html=True)
#     with col3:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('departments',0) if stats else 0}</div><div class='stat-label'>Departments</div></div>", unsafe_allow_html=True)
#     with col4:
#         st.markdown(f"<div class='stat-box'><div class='stat-number'>{stats.get('document_types',0) if stats else 0}</div><div class='stat-label'>Doc Types</div></div>", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.markdown("""<div class='custom-card'><h3 style='color:#1e3c72;'>🤖 AI Generation</h3>
#         <p style='color:#555;'>Azure OpenAI + LangChain generates professional documents with your exact company context.</p></div>""", unsafe_allow_html=True)
#     with col2:
#         st.markdown("""<div class='custom-card' style='border-left-color:#764ba2'><h3 style='color:#1e3c72;'>🗄️ PostgreSQL Backend</h3>
#         <p style='color:#555;'>All templates, questionnaires, and documents stored in your PostgreSQL database.</p></div>""", unsafe_allow_html=True)
#     with col3:
#         st.markdown("""<div class='custom-card' style='border-left-color:#4facfe'><h3 style='color:#1e3c72;'>📋 Smart Q&A</h3>
#         <p style='color:#555;'>Dynamic questions per department × document type, loaded from your database.</p></div>""", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     col1, col2 = st.columns(2)
#     with col1:
#         if st.button("✨ Generate New Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.session_state.generation_step = 1
#             st.rerun()
#     with col2:
#         if st.button("📚 View Document Library", use_container_width=True):
#             st.session_state.current_page = "Library"
#             st.rerun()

#     # Recent documents
#     docs = fetch_documents()
#     if docs:
#         st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
#         for doc in docs[:5]:
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <div style='display:flex;justify-content:space-between;align-items:center;'>
#                     <div>
#                         <b style='color:#1e3c72;'>#{doc['id']} — {doc['document_type']} — {doc['department']}</b><br>
#                         <span style='color:#999;font-size:0.85rem;'>Industry: {doc['industry']} | Created: {doc['created_at'][:16]}</span>
#                     </div>
#                     <span class='status-{"published" if doc["status"]=="completed" else "draft"}'>{doc['status'].upper()}</span>
#                 </div>
#             </div>""", unsafe_allow_html=True)

# # ============================================
# # PAGE: GENERATE DOCUMENT
# # ============================================
# def render_generate():
#     st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)

#     step = st.session_state.generation_step
#     progress = (step - 1) / 3
#     st.progress(progress)

#     steps_labels = ["📋 Select Type", "❓ Answer Questions", "🎉 Generate & Review"]
#     cols = st.columns(3)
#     for idx, (col, label) in enumerate(zip(cols, steps_labels)):
#         with col:
#             if idx + 1 < step:
#                 st.markdown(f"<p style='text-align:center;color:#4CAF50;font-weight:600;'>✅ {label}</p>", unsafe_allow_html=True)
#             elif idx + 1 == step:
#                 st.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>▶️ {label}</p>", unsafe_allow_html=True)
#             else:
#                 st.markdown(f"<p style='text-align:center;color:#999;'>⏺️ {label}</p>", unsafe_allow_html=True)

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # ── STEP 1: Select Type ──
#     if step == 1:
#         st.markdown("<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True)

#         departments = fetch_departments()
#         doc_types   = fetch_document_types()

#         col1, col2, col3 = st.columns(3)
#         with col1:
#             industry = st.selectbox("🏢 Industry", ["SaaS"], key="s1_industry")
#         with col2:
#             department = st.selectbox("🏛️ Department", departments, key="s1_dept")
#         with col3:
#             doc_type = st.selectbox("📄 Document Type", doc_types, key="s1_type")

#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("➡️ Next: Answer Questions", use_container_width=True):
#             st.session_state.selected_industry   = industry
#             st.session_state.selected_department = department
#             st.session_state.selected_doc_type   = doc_type
#             st.session_state.generation_step     = 2
#             st.rerun()

#     # ── STEP 2: Answer Questions from DB ──
#     elif step == 2:
#         st.markdown("<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True)

#         dept     = st.session_state.selected_department
#         doc_type = st.session_state.selected_doc_type

#         st.markdown(f"""
#         <div class='info-box'>
#             <strong>Generating:</strong> {doc_type} for <strong>{dept}</strong>
#         </div>""", unsafe_allow_html=True)

#         # Fetch questions from DB
#         questions = fetch_questionnaire(dept, doc_type)

#         if not questions:
#             st.warning("No questionnaire found in DB. Using default questions.")
#             questions = [
#                 {"id": "company_name",    "question": "What is your company name?",            "type": "text",     "required": True,  "options": []},
#                 {"id": "company_size",    "question": "Company size?",                          "type": "select",   "required": True,  "options": ["1-10","11-50","51-200","201-500","1000+"]},
#                 {"id": "primary_product", "question": "What is your primary SaaS product?",     "type": "text",     "required": True,  "options": []},
#                 {"id": "specific_focus",  "question": "What specific topic should this cover?", "type": "text",     "required": False, "options": []},
#                 {"id": "tools_used",      "question": "Tools/systems used?",                    "type": "text",     "required": False, "options": []},
#                 {"id": "tone_preference", "question": "Preferred document tone?",               "type": "select",   "required": False, "options": ["Professional & Formal","Professional & Friendly","Technical & Detailed","Executive-level & Concise"]},
#                 {"id": "additional_context","question":"Any additional context?",               "type": "textarea", "required": False, "options": []},
#             ]

#         answers = {}

#         # Group questions by category
#         categories = {}
#         for q in questions:
#             cat = q.get("category", "common")
#             categories.setdefault(cat, []).append(q)

#         category_labels = {
#             "common": "📋 General Questions",
#             "document_type_specific": f"📄 {doc_type} Specific Questions",
#             "department_specific": f"🏛️ {dept} Specific Questions",
#         }

#         for cat_key, cat_questions in categories.items():
#             if cat_questions:
#                 st.markdown(f"<h3 style='color:#2a5298;margin-top:25px;'>{category_labels.get(cat_key, cat_key)}</h3>", unsafe_allow_html=True)

#                 for q in cat_questions:
#                     q_id   = q.get("id", "")
#                     q_text = q.get("question", "")
#                     q_type = q.get("type", "text")
#                     q_req  = q.get("required", False)
#                     q_opts = q.get("options", [])
#                     q_placeholder = q.get("placeholder", "")

#                     label = f"{'🔴 ' if q_req else ''}{q_text}"

#                     st.markdown(f"<div class='question-block'><b style='color:#1e3c72;'>{label}</b></div>", unsafe_allow_html=True)

#                     widget_key = f"q_{q_id}"

#                     if q_type == "text":
#                         answers[q_id] = st.text_input("", key=widget_key, placeholder=q_placeholder or "", label_visibility="collapsed")

#                     elif q_type == "textarea":
#                         answers[q_id] = st.text_area("", key=widget_key, height=100, placeholder=q_placeholder or "", label_visibility="collapsed")

#                     elif q_type == "select" and q_opts:
#                         answers[q_id] = st.selectbox("", ["(select)"] + q_opts, key=widget_key, label_visibility="collapsed")

#                     elif q_type == "multi_select" and q_opts:
#                         answers[q_id] = st.multiselect("", q_opts, key=widget_key, label_visibility="collapsed")

#                     else:
#                         answers[q_id] = st.text_input("", key=widget_key, label_visibility="collapsed")

#         st.markdown("<br>", unsafe_allow_html=True)
#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("⬅️ Back", use_container_width=True):
#                 st.session_state.generation_step = 1
#                 st.rerun()
#         with col2:
#             if st.button("🚀 Generate Document", use_container_width=True):
#                 # Validate required
#                 missing = []
#                 for q in questions:
#                     if q.get("required") and not answers.get(q.get("id", "")):
#                         missing.append(q.get("question", ""))
#                 if missing:
#                     for m in missing:
#                         st.error(f"Required: {m}")
#                 else:
#                     # Clean answers — remove empty/default
#                     clean_answers = {k: v for k, v in answers.items() if v and v != "(select)"}
#                     st.session_state.question_answers = clean_answers
#                     st.session_state.generation_step  = 3
#                     st.rerun()

#     # ── STEP 3: Generate via API ──
#     elif step == 3:
#         st.markdown("<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True)

#         if st.session_state.last_generated_doc is None:
#             progress_bar = st.progress(0)
#             status_text  = st.empty()

#             phases = [
#                 ("Connecting to FastAPI backend...", 0.15),
#                 ("Loading template from PostgreSQL...", 0.30),
#                 ("Loading questionnaire from DB...", 0.45),
#                 ("Building AI prompt...", 0.60),
#                 ("Calling Azure OpenAI...", 0.80),
#                 ("Saving document to database...", 0.95),
#             ]

#             for text, pct in phases:
#                 status_text.markdown(f"<p style='text-align:center;color:#667eea;font-weight:600;'>{text}</p>", unsafe_allow_html=True)
#                 progress_bar.progress(pct)
#                 time.sleep(0.4)

#             # Call FastAPI
#             payload = {
#                 "industry":         st.session_state.selected_industry,
#                 "department":       st.session_state.selected_department,
#                 "document_type":    st.session_state.selected_doc_type,
#                 "question_answers": st.session_state.question_answers,
#             }

#             result = api_post("/documents/generate", payload)

#             progress_bar.progress(1.0)
#             status_text.empty()
#             progress_bar.empty()

#             if result:
#                 st.session_state.last_generated_doc = result
#             else:
#                 st.error("Document generation failed. Check FastAPI logs.")
#                 if st.button("⬅️ Try Again"):
#                     st.session_state.generation_step = 2
#                     st.rerun()
#                 return

#         doc = st.session_state.last_generated_doc

#         st.markdown(f"""
#         <div class='success-box'>
#             ✅ Document Generated! ID: {doc.get('document_id')} | Job: {doc.get('job_id','')[:8]}...
#         </div>""", unsafe_allow_html=True)

#         # Show document details
#         st.markdown("<h3 style='color:#1e3c72;margin-top:30px;'>📄 Document Preview</h3>", unsafe_allow_html=True)

#         st.markdown(f"""
#         <div class='doc-card'>
#             <p><span class='doc-type-badge'>{st.session_state.selected_doc_type}</span></p>
#             <p style='color:#666;'><strong>Department:</strong> {st.session_state.selected_department}</p>
#             <p style='color:#666;'><strong>Industry:</strong> {st.session_state.selected_industry}</p>
#             <p style='color:#666;'><strong>Document ID:</strong> {doc.get('document_id')}</p>
#             <p style='color:#666;'><strong>Job ID:</strong> {doc.get('job_id')}</p>
#         </div>""", unsafe_allow_html=True)

#         with st.expander("📖 View Full Generated Content", expanded=True):
#             content = doc.get("document", "No content returned.")
#             st.markdown(content)

#         with st.expander("📋 Your Answers Submitted"):
#             st.json(st.session_state.question_answers)

#         # Download
#         st.download_button(
#             label="⬇️ Download Document (.md)",
#             data=doc.get("document", ""),
#             file_name=f"{st.session_state.selected_doc_type}_{st.session_state.selected_department.replace(' ','_')}.md",
#             mime="text/markdown",
#         )

#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("🔄 Generate Another", use_container_width=True):
#                 st.session_state.generation_step    = 1
#                 st.session_state.last_generated_doc = None
#                 st.session_state.question_answers   = {}
#                 st.rerun()
#         with col2:
#             if st.button("📚 Go to Library", use_container_width=True):
#                 st.session_state.current_page       = "Library"
#                 st.session_state.generation_step    = 1
#                 st.session_state.last_generated_doc = None
#                 st.rerun()

# # ============================================
# # PAGE: DOCUMENT LIBRARY
# # ============================================
# def render_library():
#     st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         f_dept = st.selectbox("Filter by Department", ["All"] + departments, key="lib_dept")
#     with col2:
#         f_type = st.selectbox("Filter by Document Type", ["All"] + doc_types, key="lib_type")
#     with col3:
#         st.markdown("<br>", unsafe_allow_html=True)
#         if st.button("🔄 Refresh", use_container_width=True):
#             fetch_documents.clear()
#             st.rerun()

#     docs = fetch_documents(
#         department=f_dept if f_dept != "All" else None,
#         document_type=f_type if f_type != "All" else None,
#     )

#     st.markdown(f"<p style='color:#666;'><strong>{len(docs)}</strong> documents found</p>", unsafe_allow_html=True)
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     if not docs:
#         st.markdown("""<div class='info-box'><h3>📭 No Documents Found</h3>
#         <p>Generate your first document using the Generate page.</p></div>""", unsafe_allow_html=True)
#         if st.button("✨ Generate Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
#         return

#     for doc in docs:
#         with st.container():
#             st.markdown(f"""
#             <div class='doc-card'>
#                 <div style='display:flex;justify-content:space-between;align-items:start;'>
#                     <div>
#                         <b style='color:#1e3c72;font-size:1.1rem;'>#{doc['id']} — {doc['document_type']}</b><br>
#                         <span style='color:#666;'>🏛️ {doc['department']} | 🏢 {doc['industry']}</span><br>
#                         <span style='color:#999;font-size:0.85rem;'>📅 {doc['created_at'][:16]}</span>
#                     </div>
#                     <span class='{"status-published" if doc["status"]=="completed" else "status-draft"}'>{doc['status'].upper()}</span>
#                 </div>
#             </div>""", unsafe_allow_html=True)

#             col1, col2 = st.columns([3, 1])
#             with col1:
#                 if st.button(f"📖 View Document #{doc['id']}", key=f"view_{doc['id']}", use_container_width=True):
#                     full = api_get(f"/documents/{doc['id']}")
#                     if full:
#                         with st.expander(f"📄 Document #{doc['id']} — Full View", expanded=True):
#                             st.markdown(f"**Type:** {full['document_type']}  |  **Department:** {full['department']}  |  **Industry:** {full['industry']}")
#                             if full.get("metadata"):
#                                 meta = full["metadata"]
#                                 st.markdown(f"**Word Count:** {meta.get('word_count','N/A')}  |  **Reading Time:** {meta.get('reading_time_minutes','N/A')} min  |  **Status:** {meta.get('doc_status','N/A')}")
#                             st.markdown("---")
#                             st.markdown(full.get("generated_content", "No content"))
#             with col2:
#                 if st.button(f"🗑️ Delete #{doc['id']}", key=f"del_{doc['id']}", use_container_width=True):
#                     result = api_delete(f"/documents/{doc['id']}")
#                     if result:
#                         st.success("Deleted!")
#                         fetch_documents.clear()
#                         time.sleep(1)
#                         st.rerun()

# # ============================================
# # PAGE: TEMPLATES
# # ============================================
# def render_templates():
#     st.markdown("<h1 class='main-header'>🗂 Templates</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;color:#555;'>All templates seeded from content.json via PostgreSQL</p>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2 = st.columns(2)
#     with col1:
#         f_dept = st.selectbox("Filter Department", ["All"] + departments, key="tmpl_dept")
#     with col2:
#         f_type = st.selectbox("Filter Document Type", ["All"] + doc_types, key="tmpl_type")

#     params = {}
#     if f_dept != "All": params["department"] = f_dept
#     if f_type != "All": params["document_type"] = f_type

#     templates = api_get("/templates/", params=params) or []

#     st.markdown(f"<p style='color:#666;'><strong>{len(templates)}</strong> templates found</p>", unsafe_allow_html=True)
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     for tmpl in templates:
#         with st.expander(f"🗂 {tmpl['department']} — {tmpl['document_type']}  (v{tmpl['version']})"):
#             full = api_get(f"/templates/{tmpl['id']}")
#             if full and full.get("structure"):
#                 sections = full["structure"].get("sections", [])
#                 st.markdown(f"**Total Sections:** {len(sections)}")
#                 for i, s in enumerate(sections, 1):
#                     st.markdown(f"  `{i}.` {s}")
#             st.markdown(f"**Active:** {'✅' if tmpl.get('is_active') else '❌'}  |  **Created:** {tmpl.get('created_at','')[:10]}")

# # ============================================
# # PAGE: QUESTIONNAIRES
# # ============================================
# def render_questionnaires():
#     st.markdown("<h1 class='main-header'>❓ Questionnaires</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align:center;color:#555;'>All Q&A seeded from Question_Answer.json via PostgreSQL</p>", unsafe_allow_html=True)

#     departments = fetch_departments()
#     doc_types   = fetch_document_types()

#     col1, col2 = st.columns(2)
#     with col1:
#         dept = st.selectbox("Department", departments, key="qa_dept")
#     with col2:
#         doc_type = st.selectbox("Document Type", doc_types, key="qa_type")

#     if st.button("🔍 Load Questions", use_container_width=True):
#         questions = fetch_questionnaire(dept, doc_type)

#         if not questions:
#             st.warning("No questionnaire found for this combination.")
#         else:
#             st.markdown(f"<div class='success-box'>✅ {len(questions)} questions loaded for {dept} — {doc_type}</div>", unsafe_allow_html=True)

#             categories = {}
#             for q in questions:
#                 cat = q.get("category", "common")
#                 categories.setdefault(cat, []).append(q)

#             for cat, qs in categories.items():
#                 st.markdown(f"<h3 style='color:#2a5298;margin-top:20px;'>{cat.replace('_',' ').title()} ({len(qs)} questions)</h3>", unsafe_allow_html=True)
#                 for q in qs:
#                     req_badge = "🔴 Required" if q.get("required") else "⚪ Optional"
#                     st.markdown(f"""
#                     <div class='question-block'>
#                         <b>{q.get('question','')}</b><br>
#                         <span style='color:#888;font-size:0.85rem;'>Type: {q.get('type','')} | {req_badge}</span>
#                         {f"<br><span style='color:#1976d2;font-size:0.8rem;'>💡 {q.get('used_in_prompt','')}</span>" if q.get('used_in_prompt') else ''}
#                     </div>""", unsafe_allow_html=True)

# # ============================================
# # PAGE: SYSTEM STATS
# # ============================================
# def render_stats():
#     st.markdown("<h1 class='main-header'>📊 System Statistics</h1>", unsafe_allow_html=True)

#     if st.button("🔄 Refresh Stats"):
#         fetch_stats.clear()
#         st.rerun()

#     stats = fetch_stats()
#     health = api_get("/system/health")

#     if health:
#         db_status = health.get("database", "unknown")
#         color = "#4CAF50" if db_status == "connected" else "#f44336"
#         st.markdown(f"<div style='background:{color};padding:15px;border-radius:10px;color:white;text-align:center;font-weight:600;margin-bottom:20px;'>Database: {db_status.upper()}</div>", unsafe_allow_html=True)

#     if stats:
#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.metric("📋 Templates",      stats.get("templates", 0))
#         with col2:
#             st.metric("❓ Questionnaires", stats.get("questionnaires", 0))
#         with col3:
#             st.metric("📄 Documents",      stats.get("documents_generated", 0))
#         with col4:
#             st.metric("⚙️ Total Jobs",     stats.get("total_jobs", 0))

#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.metric("✅ Jobs Completed", stats.get("jobs_completed", 0))
#         with col2:
#             st.metric("❌ Jobs Failed",    stats.get("jobs_failed", 0))
#         with col3:
#             st.metric("🏢 Departments",    stats.get("departments", 0))
#         with col4:
#             st.metric("📁 Document Types", stats.get("document_types", 0))

#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

#     # Recent jobs
#     st.markdown("<h2 class='sub-header'>⚙️ Recent Generation Jobs</h2>", unsafe_allow_html=True)
#     jobs = api_get("/documents/jobs") or []
#     if jobs:
#         df = pd.DataFrame(jobs)[["job_id", "status", "document_type", "department", "started_at"]]
#         df["job_id"] = df["job_id"].str[:12] + "..."
#         st.dataframe(df, use_container_width=True)
#     else:
#         st.info("No jobs yet.")

# # ============================================
# # MAIN
# # ============================================
# def main():
#     load_custom_css()
#     init_session()
#     render_sidebar()

#     page = st.session_state.current_page

#     if page == "Home":           render_home()
#     elif page == "Generate":     render_generate()
#     elif page == "Library":      render_library()
#     elif page == "Templates":    render_templates()
#     elif page == "Questionnaires": render_questionnaires()
#     elif page == "Stats":        render_stats()

# if __name__ == "__main__":
#     main()

#------------------------------------------------
# import streamlit as st
# import pandas as pd
# from datetime import datetime
# import time
# import json
# from typing import List, Dict, Optional
# import requests

# # ============================================
# # PAGE CONFIGURATION
# # ============================================
# st.set_page_config(
#     page_title="DocuGen Pro - AI Document Generator",
#     page_icon="📄",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # ============================================
# # CUSTOM CSS FOR PROFESSIONAL DESIGN
# # ============================================
# def load_custom_css():
#     st.markdown("""
#         <style>
#         /* Import Google Fonts */
#         @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
#         /* Global Styles */
#         * {
#             font-family: 'Inter', sans-serif;
#         }
        
#         /* Main Container */
#         .main {
#             background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
#         }
        
#         /* Sidebar Styling */
#         [data-testid="stSidebar"] {
#             background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
#         }
        
#         [data-testid="stSidebar"] .css-1d391kg {
#             color: white;
#         }
        
#         /* Card Styling */
#         .custom-card {
#             background: white;
#             padding: 25px;
#             border-radius: 15px;
#             box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
#             margin-bottom: 20px;
#             border-left: 5px solid #4CAF50;
#             transition: transform 0.3s ease, box-shadow 0.3s ease;
#         }
        
#         .custom-card:hover {
#             transform: translateY(-5px);
#             box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
#         }
        
#         /* Document Card */
#         .doc-card {
#             background: white;
#             padding: 20px;
#             border-radius: 12px;
#             box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
#             margin-bottom: 15px;
#             border: 2px solid #e0e0e0;
#             transition: all 0.3s ease;
#         }
        
#         .doc-card:hover {
#             border-color: #4CAF50;
#             box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
#         }
        
#         /* Header Styles */
#         .main-header {
#             font-size: 2.5rem;
#             font-weight: 700;
#             color: #1e3c72;
#             margin-bottom: 10px;
#             text-align: center;
#             text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
#         }
        
#         .sub-header {
#             font-size: 1.8rem;
#             font-weight: 600;
#             color: #2a5298;
#             margin-top: 30px;
#             margin-bottom: 20px;
#             border-bottom: 3px solid #4CAF50;
#             padding-bottom: 10px;
#         }
        
#         /* Stat Box */
#         .stat-box {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white;
#             padding: 20px;
#             border-radius: 12px;
#             text-align: center;
#             box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
#         }
        
#         .stat-number {
#             font-size: 2.5rem;
#             font-weight: 700;
#             margin-bottom: 5px;
#         }
        
#         .stat-label {
#             font-size: 0.9rem;
#             opacity: 0.9;
#             text-transform: uppercase;
#             letter-spacing: 1px;
#         }
        
#         /* Success Box */
#         .success-box {
#             background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
#             color: white;
#             padding: 20px;
#             border-radius: 12px;
#             margin: 20px 0;
#             text-align: center;
#             font-weight: 600;
#             box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
#         }
        
#         /* Warning Box */
#         .warning-box {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white;
#             padding: 20px;
#             border-radius: 12px;
#             margin: 20px 0;
#             text-align: center;
#             font-weight: 600;
#             box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
#         }
        
#         /* Info Box */
#         .info-box {
#             background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
#             color: white;
#             padding: 20px;
#             border-radius: 12px;
#             margin: 20px 0;
#             box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
#         }
        
#         /* Button Styling */
#         .stButton>button {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white;
#             border: none;
#             border-radius: 8px;
#             padding: 12px 30px;
#             font-weight: 600;
#             font-size: 1rem;
#             transition: all 0.3s ease;
#             box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
#         }
        
#         .stButton>button:hover {
#             transform: translateY(-2px);
#             box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
#         }
        
#         /* Progress Bar */
#         .stProgress > div > div > div > div {
#             background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
#         }
        
#         /* Tag Styling */
#         .tag {
#             display: inline-block;
#             background: #e3f2fd;
#             color: #1976d2;
#             padding: 5px 12px;
#             border-radius: 20px;
#             font-size: 0.85rem;
#             margin-right: 8px;
#             margin-bottom: 8px;
#             font-weight: 500;
#         }
        
#         /* Document Type Badge */
#         .doc-type-badge {
#             background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#             color: white;
#             padding: 5px 15px;
#             border-radius: 20px;
#             font-size: 0.8rem;
#             font-weight: 600;
#             display: inline-block;
#         }
        
#         /* Status Badge */
#         .status-published {
#             background: #4CAF50;
#             color: white;
#             padding: 5px 12px;
#             border-radius: 15px;
#             font-size: 0.8rem;
#             font-weight: 600;
#         }
        
#         .status-draft {
#             background: #FF9800;
#             color: white;
#             padding: 5px 12px;
#             border-radius: 15px;
#             font-size: 0.8rem;
#             font-weight: 600;
#         }
        
#         /* Divider */
#         .custom-divider {
#             height: 3px;
#             background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
#             border: none;
#             margin: 30px 0;
#             border-radius: 5px;
#         }
        
#         /* Input Field Styling */
#         .stTextInput>div>div>input {
#             border-radius: 8px;
#             border: 2px solid #e0e0e0;
#             padding: 10px;
#             transition: border-color 0.3s ease;
#         }
        
#         .stTextInput>div>div>input:focus {
#             border-color: #667eea;
#             box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
#         }
        
#         /* Select Box Styling */
#         .stSelectbox>div>div>select {
#             border-radius: 8px;
#             border: 2px solid #e0e0e0;
#         }
        
#         /* Metric Card */
#         .metric-card {
#             background: white;
#             padding: 20px;
#             border-radius: 12px;
#             box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
#             text-align: center;
#             border-top: 4px solid #4CAF50;
#         }
        
#         /* Sidebar Navigation */
#         .nav-item {
#             padding: 12px 20px;
#             margin: 8px 0;
#             border-radius: 8px;
#             cursor: pointer;
#             transition: all 0.3s ease;
#             color: white;
#         }
        
#         .nav-item:hover {
#             background: rgba(255, 255, 255, 0.1);
#             padding-left: 25px;
#         }
        
#         .nav-item-active {
#             background: rgba(255, 255, 255, 0.2);
#             border-left: 4px solid #4CAF50;
#         }
        
#         /* Loading Animation */
#         @keyframes pulse {
#             0%, 100% { opacity: 1; }
#             50% { opacity: 0.5; }
#         }
        
#         .loading {
#             animation: pulse 1.5s ease-in-out infinite;
#         }
        
#         </style>
#     """, unsafe_allow_html=True)

# # ============================================
# # MOCK DATA & CONFIGURATION
# # ============================================

# INDUSTRIES = ["SaaS", "E-commerce", "FinTech", "Healthcare"]

# DEPARTMENTS = {
#     "SaaS": [
#         "HR & People Operations",
#         "Legal & Compliance",
#         "Sales & Customer Facing",
#         "Engineering & Operations",
#         "Product & Design",
#         "Marketing & Content",
#         "Finance & Operations",
#         "Partnership & Alliances",
#         "IT & Internal Systems",
#         "Platform & Infrastructure Operations",
#         "Data & Analytics",
#         "QA & Testing",
#         "Security & Information Assurance"
#     ]
# }

# DOCUMENT_TYPES = [
#     "SOP", "Policy", "Proposal", "SOW", "Incident Report",
#     "FAQ", "Runbook", "Playbook", "RCA", "SLA",
#     "Change Management Document"
# ]

# # Sample questions based on document type
# QUESTIONS = {
#     "SOP": [
#         {"id": "q1", "text": "What is the name of this procedure?", "type": "text", "required": True},
#         {"id": "q2", "text": "Who are the primary stakeholders?", "type": "multiselect", "options": ["HR Team", "Managers", "All Employees", "IT Department"], "required": True},
#         {"id": "q3", "text": "What compliance frameworks apply?", "type": "multiselect", "options": ["GDPR", "SOC2", "ISO 27001", "HIPAA", "None"], "required": False},
#         {"id": "q4", "text": "Describe the main objective", "type": "textarea", "required": True},
#     ],
#     "Policy": [
#         {"id": "q1", "text": "Policy Title", "type": "text", "required": True},
#         {"id": "q2", "text": "Policy Scope", "type": "multiselect", "options": ["Company-wide", "Department-specific", "Role-specific"], "required": True},
#         {"id": "q3", "text": "Effective Date", "type": "date", "required": True},
#         {"id": "q4", "text": "Policy Owner", "type": "text", "required": True},
#     ],
#     "Proposal": [
#         {"id": "q1", "text": "Project/Proposal Name", "type": "text", "required": True},
#         {"id": "q2", "text": "Target Client/Stakeholder", "type": "text", "required": True},
#         {"id": "q3", "text": "Budget Range", "type": "select", "options": ["< $10K", "$10K - $50K", "$50K - $100K", "> $100K"], "required": True},
#         {"id": "q4", "text": "Project Timeline", "type": "select", "options": ["1-3 months", "3-6 months", "6-12 months", "> 12 months"], "required": True},
#     ]
# }

# # Initialize session state
# if 'generated_documents' not in st.session_state:
#     st.session_state.generated_documents = []

# if 'current_page' not in st.session_state:
#     st.session_state.current_page = "Home"

# # ============================================
# # HELPER FUNCTIONS
# # ============================================

# def render_stat_box(number: str, label: str):
#     """Render a statistics box"""
#     return f"""
#     <div class="stat-box">
#         <div class="stat-number">{number}</div>
#         <div class="stat-label">{label}</div>
#     </div>
#     """

# def render_card(title: str, content: str, border_color: str = "#4CAF50"):
#     """Render a custom card"""
#     return f"""
#     <div class="custom-card" style="border-left-color: {border_color}">
#         <h3 style="color: #1e3c72; margin-bottom: 15px;">{title}</h3>
#         <p style="color: #555; line-height: 1.6;">{content}</p>
#     </div>
#     """

# def generate_mock_document(industry: str, department: str, doc_type: str, answers: Dict) -> Dict:
#     """Generate a mock document (replace with actual LangChain generation)"""
#     doc = {
#         "id": f"DOC-{len(st.session_state.generated_documents) + 1:04d}",
#         "title": answers.get("q1", f"{doc_type} Document"),
#         "type": doc_type,
#         "industry": industry,
#         "department": department,
#         "content": f"# {answers.get('q1', doc_type)}\n\n## Generated Content\n\nThis is a professionally generated {doc_type} document for {department} in the {industry} industry.\n\n**Key Details:**\n" + "\n".join([f"- {k}: {v}" for k, v in answers.items()]),
#         "version": "1.0",
#         "tags": ["auto-generated", doc_type.lower(), department.lower()],
#         "created_by": "AI DocuGen Pro",
#         "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         "is_published": False,
#         "notion_page_id": None
#     }
#     return doc

# # ============================================
# # SIDEBAR NAVIGATION
# # ============================================

# def render_sidebar():
#     """Render sidebar navigation"""
#     with st.sidebar:
#         st.markdown("<h1 style='color: white; text-align: center; margin-bottom: 30px;'>📄 DocuGen Pro</h1>", unsafe_allow_html=True)
#         st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.3); margin-bottom: 20px;'>", unsafe_allow_html=True)
        
#         # Navigation buttons
#         pages = {
#             "🏠 Home": "Home",
#             "✨ Generate Document": "Generate",
#             "📚 Document Library": "Library",
#             "🚀 Publish to Notion": "Publish"
#         }
        
#         for icon_label, page_key in pages.items():
#             if st.button(icon_label, key=f"nav_{page_key}", use_container_width=True):
#                 st.session_state.current_page = page_key
        
#         st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.3); margin: 30px 0;'>", unsafe_allow_html=True)
        
#         # Statistics in sidebar
#         st.markdown("<h3 style='color: white;'>📊 Quick Stats</h3>", unsafe_allow_html=True)
#         st.metric("Total Documents", len(st.session_state.generated_documents), delta=None)
#         published = sum(1 for doc in st.session_state.generated_documents if doc.get('is_published', False))
#         st.metric("Published to Notion", published, delta=None)
        
#         st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.3); margin: 30px 0;'>", unsafe_allow_html=True)
        
#         # Footer
#         st.markdown("""
#             <div style='color: rgba(255,255,255,0.7); text-align: center; font-size: 0.8rem; margin-top: 50px;'>
#                 <p>Powered by AI</p>
#                 <p>© 2026 DocuGen Pro</p>
#             </div>
#         """, unsafe_allow_html=True)

# # ============================================
# # PAGE: HOME
# # ============================================

# def render_home_page():
#     """Render home page"""
#     st.markdown("<h1 class='main-header'>🚀 Welcome to DocuGen Pro</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #555; margin-bottom: 40px;'>AI-Powered Enterprise Document Generation System</p>", unsafe_allow_html=True)
    
#     # Stats Row
#     col1, col2, col3, col4 = st.columns(4)
    
#     with col1:
#         st.markdown(render_stat_box(f"{len(st.session_state.generated_documents)}", "Documents"), unsafe_allow_html=True)
    
#     with col2:
#         published = sum(1 for doc in st.session_state.generated_documents if doc.get('is_published', False))
#         st.markdown(render_stat_box(f"{published}", "Published"), unsafe_allow_html=True)
    
#     with col3:
#         st.markdown(render_stat_box("13", "Departments"), unsafe_allow_html=True)
    
#     with col4:
#         st.markdown(render_stat_box("11", "Doc Types"), unsafe_allow_html=True)
    
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
#     # Feature Cards
#     st.markdown("<h2 class='sub-header'>✨ Key Features</h2>", unsafe_allow_html=True)
    
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.markdown(render_card(
#             "🤖 AI-Powered Generation",
#             "Leverage advanced LLM models to generate professional, industry-ready documents in seconds.",
#             "#667eea"
#         ), unsafe_allow_html=True)
    
#     with col2:
#         st.markdown(render_card(
#             "📋 Smart Templates",
#             "Dynamic question-based workflows ensure every document meets compliance and quality standards.",
#             "#764ba2"
#         ), unsafe_allow_html=True)
    
#     with col3:
#         st.markdown(render_card(
#             "🔗 Notion Integration",
#             "Seamlessly publish documents to Notion with structured metadata and version control.",
#             "#4CAF50"
#         ), unsafe_allow_html=True)
    
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
#     # Quick Actions
#     st.markdown("<h2 class='sub-header'>🎯 Quick Actions</h2>", unsafe_allow_html=True)
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         if st.button("🆕 Create New Document", key="home_create", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
    
#     with col2:
#         if st.button("📚 Browse Library", key="home_browse", use_container_width=True):
#             st.session_state.current_page = "Library"
#             st.rerun()
    
#     # Recent Activity
#     if st.session_state.generated_documents:
#         st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
        
#         recent_docs = sorted(st.session_state.generated_documents, 
#                            key=lambda x: x['created_at'], reverse=True)[:3]
        
#         for doc in recent_docs:
#             status_badge = "status-published" if doc.get('is_published') else "status-draft"
#             status_text = "Published" if doc.get('is_published') else "Draft"
            
#             st.markdown(f"""
#             <div class="doc-card">
#                 <div style="display: flex; justify-content: space-between; align-items: center;">
#                     <div>
#                         <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
#                         <p style="margin: 5px 0; color: #666;">
#                             <span class="doc-type-badge">{doc['type']}</span>
#                             <span style="margin-left: 10px; color: #999;">📅 {doc['created_at']}</span>
#                         </p>
#                     </div>
#                     <span class="{status_badge}">{status_text}</span>
#                 </div>
#             </div>
#             """, unsafe_allow_html=True)

# # ============================================
# # PAGE: GENERATE DOCUMENT
# # ============================================

# def render_generate_page():
#     """Render document generation page"""
#     st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 30px;'>Follow the wizard to create professional documents</p>", unsafe_allow_html=True)
    
#     # Progress tracker
#     if 'generation_step' not in st.session_state:
#         st.session_state.generation_step = 1
    
#     # Progress bar
#     progress = (st.session_state.generation_step - 1) / 3
#     st.progress(progress)
    
#     steps = ["📋 Select Type", "❓ Answer Questions", "🎉 Generate & Review"]
#     cols = st.columns(3)
#     for idx, (col, step) in enumerate(zip(cols, steps)):
#         with col:
#             if idx + 1 < st.session_state.generation_step:
#                 st.markdown(f"<p style='text-align: center; color: #4CAF50; font-weight: 600;'>✅ {step}</p>", unsafe_allow_html=True)
#             elif idx + 1 == st.session_state.generation_step:
#                 st.markdown(f"<p style='text-align: center; color: #667eea; font-weight: 600;'>▶️ {step}</p>", unsafe_allow_html=True)
#             else:
#                 st.markdown(f"<p style='text-align: center; color: #999;'>⏺️ {step}</p>", unsafe_allow_html=True)
    
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
#     # STEP 1: Select Document Type
#     if st.session_state.generation_step == 1:
#         st.markdown("<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True)
        
#         col1, col2, col3 = st.columns(3)
        
#         with col1:
#             industry = st.selectbox("🏢 Industry", INDUSTRIES, key="gen_industry")
        
#         with col2:
#             department = st.selectbox("🏛️ Department", DEPARTMENTS.get(industry, []), key="gen_department")
        
#         with col3:
#             doc_type = st.selectbox("📄 Document Type", DOCUMENT_TYPES, key="gen_doc_type")
        
#         st.markdown("<br>", unsafe_allow_html=True)
        
#         if st.button("➡️ Next: Answer Questions", use_container_width=True):
#             st.session_state.selected_industry = industry
#             st.session_state.selected_department = department
#             st.session_state.selected_doc_type = doc_type
#             st.session_state.generation_step = 2
#             st.rerun()
    
#     # STEP 2: Answer Questions
#     elif st.session_state.generation_step == 2:
#         st.markdown("<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True)
        
#         st.markdown(f"""
#         <div class="info-box">
#             <strong>Generating:</strong> {st.session_state.selected_doc_type} for {st.session_state.selected_department} in {st.session_state.selected_industry}
#         </div>
#         """, unsafe_allow_html=True)
        
#         questions = QUESTIONS.get(st.session_state.selected_doc_type, QUESTIONS["SOP"])
#         answers = {}
        
#         for question in questions:
#             st.markdown(f"<p style='font-weight: 600; color: #1e3c72; margin-top: 20px;'>{question['text']} {'*' if question['required'] else ''}</p>", unsafe_allow_html=True)
            
#             if question['type'] == 'text':
#                 answers[question['id']] = st.text_input("", key=f"answer_{question['id']}", label_visibility="collapsed")
            
#             elif question['type'] == 'textarea':
#                 answers[question['id']] = st.text_area("", key=f"answer_{question['id']}", height=120, label_visibility="collapsed")
            
#             elif question['type'] == 'select':
#                 answers[question['id']] = st.selectbox("", question['options'], key=f"answer_{question['id']}", label_visibility="collapsed")
            
#             elif question['type'] == 'multiselect':
#                 answers[question['id']] = st.multiselect("", question['options'], key=f"answer_{question['id']}", label_visibility="collapsed")
            
#             elif question['type'] == 'date':
#                 answers[question['id']] = st.date_input("", key=f"answer_{question['id']}", label_visibility="collapsed")
        
#         st.markdown("<br>", unsafe_allow_html=True)
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             if st.button("⬅️ Back", use_container_width=True):
#                 st.session_state.generation_step = 1
#                 st.rerun()
        
#         with col2:
#             if st.button("➡️ Generate Document", use_container_width=True):
#                 # Validate required fields
#                 all_valid = True
#                 for question in questions:
#                     if question['required'] and not answers.get(question['id']):
#                         all_valid = False
#                         st.error(f"Please answer: {question['text']}")
                
#                 if all_valid:
#                     st.session_state.current_answers = answers
#                     st.session_state.generation_step = 3
#                     st.rerun()
    
#     # STEP 3: Generate & Review
#     elif st.session_state.generation_step == 3:
#         st.markdown("<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True)
        
#         # Simulate generation with progress
#         progress_bar = st.progress(0)
#         status_text = st.empty()
        
#         steps_simulation = [
#             ("Analyzing requirements...", 0.2),
#             ("Loading AI model...", 0.4),
#             ("Generating content...", 0.6),
#             ("Applying formatting...", 0.8),
#             ("Finalizing document...", 1.0),
#         ]
        
#         for step_text, progress_value in steps_simulation:
#             status_text.markdown(f"<p style='text-align: center; color: #667eea; font-weight: 600;'>{step_text}</p>", unsafe_allow_html=True)
#             progress_bar.progress(progress_value)
#             time.sleep(0.5)
        
#         # Generate document
#         document = generate_mock_document(
#             st.session_state.selected_industry,
#             st.session_state.selected_department,
#             st.session_state.selected_doc_type,
#             st.session_state.current_answers
#         )
        
#         st.session_state.generated_documents.append(document)
        
#         status_text.empty()
#         progress_bar.empty()
        
#         st.markdown(f"""
#         <div class="success-box">
#             ✅ Document Generated Successfully! ID: {document['id']}
#         </div>
#         """, unsafe_allow_html=True)
        
#         # Display document preview
#         st.markdown("<h3 style='color: #1e3c72; margin-top: 30px;'>📄 Document Preview</h3>", unsafe_allow_html=True)
        
#         st.markdown(f"""
#         <div class="doc-card">
#             <h2 style="color: #1e3c72;">{document['title']}</h2>
#             <p><span class="doc-type-badge">{document['type']}</span></p>
#             <p style="color: #666; margin-top: 15px;"><strong>Industry:</strong> {document['industry']}</p>
#             <p style="color: #666;"><strong>Department:</strong> {document['department']}</p>
#             <p style="color: #666;"><strong>Version:</strong> {document['version']}</p>
#             <p style="color: #666;"><strong>Created:</strong> {document['created_at']}</p>
#             <div style="margin-top: 20px;">
#                 <strong>Tags:</strong><br>
#                 {''.join([f'<span class="tag">{tag}</span>' for tag in document['tags']])}
#             </div>
#         </div>
#         """, unsafe_allow_html=True)
        
#         with st.expander("📖 View Full Content"):
#             st.markdown(document['content'])
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             if st.button("🔄 Generate Another", use_container_width=True):
#                 st.session_state.generation_step = 1
#                 st.rerun()
        
#         with col2:
#             if st.button("📚 Go to Library", use_container_width=True):
#                 st.session_state.current_page = "Library"
#                 st.session_state.generation_step = 1
#                 st.rerun()

# # ============================================
# # PAGE: DOCUMENT LIBRARY
# # ============================================

# def render_library_page():
#     """Render document library page"""
#     st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 30px;'>Browse and manage all generated documents</p>", unsafe_allow_html=True)
    
#     if not st.session_state.generated_documents:
#         st.markdown("""
#         <div class="info-box">
#             <h3>📭 No Documents Yet</h3>
#             <p>Start by generating your first document!</p>
#         </div>
#         """, unsafe_allow_html=True)
        
#         if st.button("✨ Generate First Document", use_container_width=True):
#             st.session_state.current_page = "Generate"
#             st.rerun()
#         return
    
#     # Filters
#     st.markdown("<h3 style='color: #1e3c72;'>🔍 Filters</h3>", unsafe_allow_html=True)
    
#     col1, col2, col3, col4 = st.columns(4)
    
#     with col1:
#         filter_type = st.multiselect("Document Type", 
#                                      options=list(set([doc['type'] for doc in st.session_state.generated_documents])),
#                                      default=[])
    
#     with col2:
#         filter_industry = st.multiselect("Industry",
#                                         options=list(set([doc['industry'] for doc in st.session_state.generated_documents])),
#                                         default=[])
    
#     with col3:
#         filter_status = st.selectbox("Status", ["All", "Published", "Draft"])
    
#     with col4:
#         search_term = st.text_input("🔎 Search", placeholder="Search by title...")
    
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
#     # Filter documents
#     filtered_docs = st.session_state.generated_documents
    
#     if filter_type:
#         filtered_docs = [doc for doc in filtered_docs if doc['type'] in filter_type]
    
#     if filter_industry:
#         filtered_docs = [doc for doc in filtered_docs if doc['industry'] in filter_industry]
    
#     if filter_status == "Published":
#         filtered_docs = [doc for doc in filtered_docs if doc.get('is_published', False)]
#     elif filter_status == "Draft":
#         filtered_docs = [doc for doc in filtered_docs if not doc.get('is_published', False)]
    
#     if search_term:
#         filtered_docs = [doc for doc in filtered_docs if search_term.lower() in doc['title'].lower()]
    
#     # Display count
#     st.markdown(f"<p style='color: #666; font-size: 1.1rem;'>Showing <strong>{len(filtered_docs)}</strong> of <strong>{len(st.session_state.generated_documents)}</strong> documents</p>", unsafe_allow_html=True)
    
#     # Display documents
#     for idx, doc in enumerate(filtered_docs):
#         status_badge = "status-published" if doc.get('is_published') else "status-draft"
#         status_text = "Published" if doc.get('is_published') else "Draft"
        
#         with st.container():
#             st.markdown(f"""
#             <div class="doc-card">
#                 <div style="display: flex; justify-content: space-between; align-items: start;">
#                     <div style="flex: 1;">
#                         <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
#                         <p style="margin: 10px 0; color: #666;">
#                             <span class="doc-type-badge">{doc['type']}</span>
#                             <span style="margin-left: 10px;">🏢 {doc['industry']}</span>
#                             <span style="margin-left: 10px;">🏛️ {doc['department']}</span>
#                         </p>
#                         <p style="margin: 5px 0; color: #999; font-size: 0.9rem;">
#                             📅 {doc['created_at']} • 👤 {doc['created_by']} • 📌 v{doc['version']}
#                         </p>
#                         <div style="margin-top: 10px;">
#                             {''.join([f'<span class="tag">{tag}</span>' for tag in doc['tags']])}
#                         </div>
#                     </div>
#                     <div style="text-align: right;">
#                         <span class="{status_badge}">{status_text}</span>
#                     </div>
#                 </div>
#             </div>
#             """, unsafe_allow_html=True)
            
#             col1, col2, col3 = st.columns([2, 1, 1])
            
#             with col1:
#                 if st.button("📖 View Details", key=f"view_{idx}", use_container_width=True):
#                     st.session_state.selected_doc_for_view = doc
#                     st.session_state.show_doc_modal = True
            
#             with col2:
#                 if not doc.get('is_published'):
#                     if st.button("🚀 Publish", key=f"publish_{idx}", use_container_width=True):
#                         doc['is_published'] = True
#                         doc['notion_page_id'] = f"NOTION-{doc['id']}"
#                         st.success(f"✅ Published to Notion!")
#                         time.sleep(1)
#                         st.rerun()
            
#             with col3:
#                 if st.button("🗑️ Delete", key=f"delete_{idx}", use_container_width=True):
#                     st.session_state.generated_documents.remove(doc)
#                     st.success("Document deleted!")
#                     time.sleep(1)
#                     st.rerun()
    
#     # Document detail modal
#     if st.session_state.get('show_doc_modal', False):
#         doc = st.session_state.selected_doc_for_view
#         st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
#         st.markdown("<h2 style='color: #1e3c72;'>📄 Document Details</h2>", unsafe_allow_html=True)
        
#         st.markdown(f"""
#         <div class="doc-card">
#             <h2 style="color: #1e3c72;">{doc['title']}</h2>
#             <p><span class="doc-type-badge">{doc['type']}</span></p>
#             <hr>
#             <p><strong>Industry:</strong> {doc['industry']}</p>
#             <p><strong>Department:</strong> {doc['department']}</p>
#             <p><strong>Version:</strong> {doc['version']}</p>
#             <p><strong>Created By:</strong> {doc['created_by']}</p>
#             <p><strong>Created At:</strong> {doc['created_at']}</p>
#             <p><strong>Status:</strong> {'Published ✅' if doc.get('is_published') else 'Draft 📝'}</p>
#             {f"<p><strong>Notion Page ID:</strong> {doc['notion_page_id']}</p>" if doc.get('notion_page_id') else ''}
#             <div style="margin-top: 20px;">
#                 <strong>Tags:</strong><br>
#                 {''.join([f'<span class="tag">{tag}</span>' for tag in doc['tags']])}
#             </div>
#         </div>
#         """, unsafe_allow_html=True)
        
#         st.markdown("<h3 style='color: #1e3c72; margin-top: 20px;'>📝 Content</h3>", unsafe_allow_html=True)
#         st.markdown(doc['content'])
        
#         if st.button("✖️ Close", use_container_width=True):
#             st.session_state.show_doc_modal = False
#             st.rerun()

# # ============================================
# # PAGE: PUBLISH TO NOTION
# # ============================================

# def render_publish_page():
#     """Render Notion publishing page"""
#     st.markdown("<h1 class='main-header'>🚀 Publish to Notion</h1>", unsafe_allow_html=True)
#     st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 30px;'>Manage document publishing to Notion workspace</p>", unsafe_allow_html=True)
    
#     # Unpublished documents
#     unpublished = [doc for doc in st.session_state.generated_documents if not doc.get('is_published', False)]
#     published = [doc for doc in st.session_state.generated_documents if doc.get('is_published', False)]
    
#     # Stats
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.markdown(render_stat_box(f"{len(st.session_state.generated_documents)}", "Total Docs"), unsafe_allow_html=True)
    
#     with col2:
#         st.markdown(render_stat_box(f"{len(unpublished)}", "Ready to Publish"), unsafe_allow_html=True)
    
#     with col3:
#         st.markdown(render_stat_box(f"{len(published)}", "Published"), unsafe_allow_html=True)
    
#     st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
#     # Bulk publish
#     if unpublished:
#         st.markdown("<h2 class='sub-header'>📤 Ready to Publish</h2>", unsafe_allow_html=True)
        
#         if st.button("🚀 Publish All to Notion", use_container_width=True):
#             progress_bar = st.progress(0)
#             status = st.empty()
            
#             for idx, doc in enumerate(unpublished):
#                 status.markdown(f"<p style='text-align: center; color: #667eea;'>Publishing: {doc['title']}...</p>", unsafe_allow_html=True)
#                 time.sleep(0.3)  # Simulate API call
#                 doc['is_published'] = True
#                 doc['notion_page_id'] = f"NOTION-{doc['id']}"
#                 progress_bar.progress((idx + 1) / len(unpublished))
            
#             st.markdown("""
#             <div class="success-box">
#                 🎉 All documents published successfully!
#             </div>
#             """, unsafe_allow_html=True)
#             time.sleep(2)
#             st.rerun()
        
#         st.markdown("<br>", unsafe_allow_html=True)
        
#         # Individual publish
#         for idx, doc in enumerate(unpublished):
#             st.markdown(f"""
#             <div class="doc-card">
#                 <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
#                 <p style="margin: 5px 0; color: #666;">
#                     <span class="doc-type-badge">{doc['type']}</span>
#                     <span style="margin-left: 10px;">📅 {doc['created_at']}</span>
#                 </p>
#             </div>
#             """, unsafe_allow_html=True)
            
#             if st.button(f"🚀 Publish '{doc['title']}'", key=f"pub_{idx}", use_container_width=True):
#                 with st.spinner(f"Publishing {doc['title']}..."):
#                     time.sleep(1)
#                     doc['is_published'] = True
#                     doc['notion_page_id'] = f"NOTION-{doc['id']}"
#                 st.success("✅ Published!")
#                 time.sleep(1)
#                 st.rerun()
#     else:
#         st.markdown("""
#         <div class="info-box">
#             <h3>✅ All Caught Up!</h3>
#             <p>No documents waiting to be published.</p>
#         </div>
#         """, unsafe_allow_html=True)
    
#     # Published documents
#     if published:
#         st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
#         st.markdown("<h2 class='sub-header'>✅ Published Documents</h2>", unsafe_allow_html=True)
        
#         for doc in published:
#             st.markdown(f"""
#             <div class="doc-card">
#                 <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
#                 <p style="margin: 5px 0; color: #666;">
#                     <span class="status-published">Published</span>
#                     <span style="margin-left: 10px;">🔗 Notion ID: {doc['notion_page_id']}</span>
#                 </p>
#             </div>
#             """, unsafe_allow_html=True)

# # ============================================
# # MAIN APP
# # ============================================

# def main():
#     """Main application"""
#     load_custom_css()
#     render_sidebar()
    
#     # Route to pages
#     if st.session_state.current_page == "Home":
#         render_home_page()
#     elif st.session_state.current_page == "Generate":
#         render_generate_page()
#     elif st.session_state.current_page == "Library":
#         render_library_page()
#     elif st.session_state.current_page == "Publish":
#         render_publish_page()

# if __name__ == "__main__":
#     main()

    
