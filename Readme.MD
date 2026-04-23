# 📄 DocForgeHub — Enterprise AI Document Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4.1-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=for-the-badge)
![LangGraph](https://img.shields.io/badge/LangGraph-0.1.5-412991?style=for-the-badge)
![Notion](https://img.shields.io/badge/Notion-API-000000?style=for-the-badge&logo=notion&logoColor=white)

**An end-to-end enterprise AI platform combining intelligent document generation, a Notion-backed RAG knowledge base, and a stateful LangGraph assistant with Notion ticket escalation.**

[Features](#-features) • [Architecture](#-system-architecture) • [Project 1](#-project-1--docforge-hub) • [Project 2](#-project-2--citerag-lab) • [Project 3](#-project-3--statecase-assistant) • [Quick Start](#-quick-start)

</div>

---

## 📌 Platform Overview

| | Project 1 | Project 2 | Project 3 |
|---|---|---|---|
| **Name** | DocForge Hub | CiteRAG Lab | StateCase Assistant |
| **Purpose** | AI document generation + Notion publish | Grounded Q&A over Notion knowledge base | Stateful chat + Notion ticket escalation |
| **Core Tech** | Azure OpenAI · LangChain · PostgreSQL | ChromaDB · Redis · RAGAS | LangGraph · Redis · PostgreSQL |
| **Endpoints** | `/documents/*` `/templates/*` `/export/*` | `/rag/*` — 11 endpoints | `/assistant/*` `/tickets/*` |

---

## ✨ Features

### 🏗️ Project 1 — DocForge Hub
- 🤖 **AI Generation** — Azure OpenAI GPT-4.1-Mini, section-by-section, Temp 0.7
- 📋 **130 Templates** — 13 departments × 10 doc types
- ✅ **Quality Validation** — Score 0–100, Grade A–F, 5 checks, auto-retry if < 60
- 📤 **Export** — PDF (ReportLab) · DOCX (python-docx) · Markdown
- 🚀 **Notion Publishing** — Auto-versioning v1 → v2 → v3

### 🔍 Project 2 — CiteRAG Lab
- 💬 **Grounded Q&A** — Answers from 910+ Notion chunks with citations
- ✨ **Query Refiner** — GPT rewrites vague queries + keywords + suggestions
- ⚖️ **Doc Comparison** — Side-by-side `doc_a_points` vs `doc_b_points`
- 📊 **RAGAS Evaluation** — Faithfulness · Relevancy · Precision · Recall
- ⚡ **Redis Cache** — 6 types · TTL 30 min–24h

### 🤖 Project 3 — StateCase Assistant
- 🔷 **LangGraph StateGraph** — 7 nodes with conditional edges
- 🧠 **Intent Classification** — retrieve · clarify · ticket
- 🎫 **Notion Ticket Creation** — Auto-escalation when evidence_score < 0.45
- 💾 **Dual Memory** — Redis (fast, 2h) + PostgreSQL (durable, permanent)
- 🔒 **Idempotency** — Redis lock prevents duplicate ticket creation

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Streamlit UI — localhost:8501                       │
│   DocForge Hub · CiteRAG Lab · Stateful Assistant               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────────┐
│           FastAPI Backend — localhost:8000                       │
│   25+ endpoints · Swagger /docs · Async · CORS enabled          │
├──────────────┬──────────────────────┬────────────────────────────┤
│  /documents/*│      /rag/*          │  /assistant/* + /tickets/* │
│  /templates/*│   api/retrieve.py   │   api/assistant.py          │
│  /export/*   │   11 endpoints       │   6 endpoints               │
└──────┬───────┴──────────┬───────────┴─────────┬──────────────────┘
       │                  │                      │
┌──────▼──────┐  ┌────────▼────────┐  ┌─────────▼─────────┐
│ PostgreSQL  │  │   ChromaDB      │  │      Redis         │
│ 9 tables    │  │ 910 chunks      │  │ 6 cache types      │
│ 230+ docs   │  │ 384-dim embed   │  │ TTL 30min–24h      │
└─────────────┘  └────────┬────────┘  └────────────────────┘
                           │
                  ┌────────▼────────┐
                  │  Notion API     │
                  │ 129 KB pages    │
                  │ Ticket DB       │
                  └─────────────────┘
```

---

## 📊 Complete Backend Architecture

> Full three-project backend flow with shared data layer

![DocForgeHub Backend Flow](./docs/diagrams/Docforgehub_backend_flow.png)

> *Left column: Project 1 document generation pipeline · Centre: Project 2 RAG pipeline · Right: Project 3 LangGraph agent*

---

## 📄 Project 1 — DocForge Hub

### Flow Diagram

![DocForge Hub Flow](./docs/diagrams/docforge_hub_flow.svg)

### Step-by-step
```
User selects Dept + Doc Type
         ↓
Load Template (PostgreSQL JSONB sections)
         ↓
Answer Questionnaire (Common · Metadata · Doc-specific)
         ↓
LangChain Prompt Builder (Context + Sections + Constraints)
         ↓
Azure OpenAI GPT-4.1-mini (Section-by-section · Temp 0.7)
         ↓
Quality Validator (0–100 · Grade A–F · retry if < 60)
         ↓
Save to PostgreSQL (generated_documents + metadata)
         ↓
    ┌────┴────┐──────────────┐
   PDF      DOCX          Notion
(ReportLab)(python-docx) (v1→v2→v3)
```

### Supported Departments (13 × 10 = 130 Templates)

| Department | Document Types |
|---|---|
| HR & People Operations | Offer Letter, Employment Contract, Employee Handbook, HR Policy Manual, Onboarding Checklist, Performance Appraisal, Leave Policy, Code of Conduct, Exit Interview, Training Plan |
| Legal & Compliance | MSA, NDA, DPA, Privacy Policy, Terms of Service, Compliance Audit, Risk Assessment, IP Agreement, Vendor Contract, Regulatory Checklist |
| Sales & Customer Facing | Sales Proposal, Sales Playbook, Customer Onboarding, SLA, Pricing Strategy, Case Study, Sales Contract, CRM Guidelines, Quarterly Report, Customer Feedback |
| Engineering & Operations | SRS, TDD, API Documentation, Deployment Guide, Release Notes, System Architecture, Incident Report, RCA, DevOps Runbook, Change Management |
| Finance & Operations | Budget Plan, Financial Statement, Expense Policy, Invoice Template, Procurement Policy, Revenue Forecast, Cash Flow, Vendor Payment, Cost Analysis, Financial Risk |
| + 8 more | Product, Marketing, Partnership, IT, Platform & Infra, Data & Analytics, QA & Testing, Security |

---

## 🔍 Project 2 — CiteRAG Lab

### RAG Pipeline Diagram

![CiteRAG Lab Flow](/home/rensis/Downloads/citerag_lab_flow (1).svg)

### Pipeline Detail

```
INGESTION (one-time)
Notion Pages → Extract Blocks → Chunk 500w → Embed 384-dim → ChromaDB
                                                               ↑
                                              Redis dedup (ingested:{page_id} 24h)

QUERY PIPELINE (every question)
User Question
     ↓
refine_query()  ←── GPT rewrites + extracts keywords
     ↓
Redis Cache check (answer:{hash} 30min)
     ↓ MISS
search_docs()   ←── ChromaDB cosine similarity, Top-5 chunks
     ↓
evidence_score  ←── avg(top-3 scores) — anti-hallucination gate
     ↓
ask()           ←── GPT · Temp 0.2 · context-only prompt
     ↓
Answer + Citations ["Doc Title › Section · 94%"]
```

### RAGAS Evaluation Results

| Metric | Score | Description |
|---|---|---|
| **Faithfulness** | **87%** | Answer grounded in retrieved chunks |
| **Answer Relevancy** | **83%** | Answer addresses the question |
| **Context Precision** | **91%** | Retrieved chunks are relevant (low noise) |
| **Context Recall** | **79%** | All needed chunks retrieved |
| **Overall** | **85%** | Arithmetic mean of four metrics |

### Redis Cache Strategy

| Key Pattern | TTL | Purpose |
|---|---|---|
| `retrieval: MD5(q+f)` | 1 hour | ChromaDB retrieval results |
| `refine: hash(q)` | 1 hour | Refined query + keywords |
| `answer: hash` | 30 min | Full LLM answer + citations |
| `session:{id}` | 30 min | Multi-turn conversation history |
| `ingested:{page}` | 24 hours | Notion page deduplication |
| `notion_rate` | 60 sec | Rate limiting |

---

## 🤖 Project 3 — StateCase Assistant

### LangGraph Flow Diagram

![StateCase Assistant Flow](./docs/diagrams/statecase_flow.png)

### State Machine

```
User Message → POST /assistant/chat
         ↓
context_loader      [Redis → PostgreSQL fallback]
         ↓
intent_classifier   [retrieve · clarify · ticket]
         ↓
    ┌────┼──────────────────────┐
 ticket  retrieve            clarify
    │       ↓                   ↓
    │   rag_retrieval       clarify_node
    │   evidence_score          ↓
    │   avg top-3           Ask follow-up Q
    │       ↓
    │   score ≥ 0.20 → answer_node  [Azure OpenAI · Temp 0.2]
    │   score < 0.20 → ticket_node
    │                      ↓
    └──────────────→  ticket_node  [Notion ticket + idempotency]
                           ↓
                      memory_save  [PostgreSQL + Redis session]
                           ↓
                   Response to User
                   [Answer + Citations / Ticket URL]
```

### All 7 Nodes

| Node | File | What it does |
|---|---|---|
| `context_loader` | `assistant/nodes.py` | Load Redis (fast) → PostgreSQL fallback. Restores industry, dept, last 10 messages |
| `intent_classifier` | `assistant/nodes.py` | Keyword shortcuts + LLM classify: retrieve / clarify / ticket. Sets priority |
| `clarify_node` | `assistant/nodes.py` | Generate ONE targeted follow-up question. Waits for user reply |
| `rag_retrieval` | `assistant/nodes.py` | Calls `rag/tools.py` (P2 reuse). refine_query() + search_docs(). Computes evidence_score |
| `answer_node` | `assistant/nodes.py` | Calls `rag/chain.py:ask()` (P2 reuse). Returns grounded answer + citations |
| `ticket_node` | `assistant/ticket.py` | Check Redis idempotency lock. Create Notion ticket. Set 1h lock |
| `memory_save` | `assistant/memory.py` | Save messages to PostgreSQL. Update Redis msgs (2h) + ctx (24h) |

### Cannot-Answer Detection

| Rule | Trigger | Action |
|---|---|---|
| Low evidence | `evidence_score < 0.45` after retrieval | → `ticket_node` |
| Zero chunks | Nothing found in ChromaDB | → `ticket_node` (score = 0.0) |
| Policy keywords | "rate card", "pricing table", "contract value" | → Direct ticket, skip retrieval |
| User explicit | "raise a ticket", "escalate", "create ticket" | → Direct ticket |

### Notion Ticket Schema

| Property | Type | Value |
|---|---|---|
| Title | title | First 80 chars of question |
| Status | select | Open → In Progress → Resolved → Closed |
| Priority | select | Low / Medium / High / Critical (auto-assigned) |
| Department | select | From assistant state |
| Assigned To | rich_text | Auto-mapped by department |
| Thread ID | rich_text | Idempotency key |
| Evidence Score | number | Score that triggered ticket |
| Sources Tried | rich_text | Top-3 docs attempted |

### Redis Keys — Project 3

| Key Pattern | TTL | Purpose |
|---|---|---|
| `thread:{id}:msgs` | 30 min | Last 20 conversation messages |
| `thread:{id}:ctx` | 30 min | User context: industry, department |
| `asst:idem:{thread}` | 1 hour | Idempotency lock — no duplicate tickets |
| `rl:assistant:{user}` | 1 min | Rate limit 30 req/min |

---

## 🗄️ Shared Data Layer

### PostgreSQL Tables (9 tables)

| Table | Rows | Purpose |
|---|---|---|
| `departments` | 13 | Department registry |
| `document_types` | 130 | Document type registry |
| `templates` | 130 | JSONB sections array |
| `generated_documents` | 230+ | All generated docs + Notion metadata |
| `document_metadata` | — | Extended metadata |
| `generation_jobs` | — | Async job tracking |
| `assistant_threads` | — | P3 conversation threads |
| `assistant_messages` | — | All messages with citations, intent, trace_id |
| `assistant_tickets` | — | Support tickets with status, evidence, sources |

### ChromaDB Vector Store

| Property | Value |
|---|---|
| Total chunks | 910 |
| Embedding model | SentenceTransformer all-MiniLM-L6-v2 (384-dim) |
| Similarity | Cosine |
| Metadata fields | `doc_type` · `department` · `industry` · `section` · `page_id` |

### Azure OpenAI

| Usage | Model | Temp |
|---|---|---|
| Document generation | GPT-4.1-mini | 0.7 |
| Q&A + classification | GPT-4.1-mini | 0.2 |
| Query refinement + comparison | GPT-4.1-mini | 0.2 |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+, PostgreSQL 15+, Redis 7.0+
- Azure OpenAI access, Notion integration token

### 1. Clone & Setup
```bash
git clone https://github.com/Rrensisorathiya/DocForgeHub.git
cd DocForgeHub
git checkout AssistantStateFlow
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env`
```env
# Azure OpenAI — LLM
AZURE_OPENAI_LLM_KEY=your_key
AZURE_LLM_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_LLM_API_VERSION=2024-02-15-preview
AZURE_LLM_DEPLOYMENT_41_MINI=gpt-4.1-mini

# Azure OpenAI — Embeddings
AZURE_OPENAI_EMB_KEY=your_key
AZURE_EMB_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_EMB_API_VERSION=2024-02-15-preview
AZURE_EMB_DEPLOYMENT=text-embedding-ada-002

# PostgreSQL
DB_HOST=localhost
DB_NAME=saas_doc_engine
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_URL=redis://localhost:6379

# Notion
NOTION_TOKEN=ntn_xxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=your_database_id
NOTION_TICKET_DATABASE_ID=your_ticket_db_id

# RAG
CHROMA_DIR=./chroma_db
```

### 3. Start Services
```bash
# Database + Redis
sudo systemctl start postgresql redis

# Run migrations
python3 migrations/seed_from_json.py
python3 migrations/add_assistant_tables.py

# Backend
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
streamlit run document_app.py
```

### 4. Ingest Notion Documents
```bash
curl -X POST http://localhost:8000/rag/ingest \
     -H "Content-Type: application/json" \
     -d '{"token":"your_token","database_id":"your_db_id"}'
```

### 5. Access
| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI Backend | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

---

## 📡 API Reference

### Documents
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/generate` | Generate document via LLM |
| `GET` | `/documents/` | List all documents |
| `GET` | `/documents/{id}` | Get single document |
| `DELETE` | `/documents/{id}` | Delete document |
| `POST` | `/documents/regenerate/{id}` | Regenerate with same answers |
| `GET` | `/export/{id}/pdf` | Export as PDF |
| `GET` | `/export/{id}/docx` | Export as DOCX |

### RAG
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/rag/answer` | Grounded Q&A with citations |
| `POST` | `/rag/retrieve` | Raw chunk retrieval + scores |
| `POST` | `/rag/refine` | AI query refinement |
| `POST` | `/rag/compare` | Compare two document types |
| `POST` | `/rag/ingest` | Ingest Notion docs to ChromaDB |
| `GET` | `/rag/stats` | Vector store stats |
| `POST` | `/rag/eval/run` | Run RAGAS evaluation |
| `GET` | `/rag/eval/results` | Latest evaluation results |

### Assistant
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/assistant/threads` | Create conversation thread |
| `POST` | `/assistant/chat` | Send message — full LangGraph run |
| `GET` | `/assistant/threads/{id}` | Get thread history |
| `DELETE` | `/assistant/threads/{id}` | Clear thread + Redis |
| `GET` | `/tickets/` | List support tickets |
| `PUT` | `/tickets/{id}/status` | Update status (syncs Notion) |

---

## 📦 Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | Streamlit | 1.28+ |
| API | FastAPI + Uvicorn | 0.104+ |
| LLM | Azure OpenAI GPT-4.1-Mini | gpt-4.1-mini |
| LLM Framework | LangChain | 0.1+ |
| Stateful Agent | LangGraph | 0.1.5 |
| Embeddings | SentenceTransformer all-MiniLM-L6-v2 | 384-dim |
| Vector Store | ChromaDB | 0.4+ |
| Cache | Redis | 7.0+ |
| Database | PostgreSQL | 15+ |
| Notion | Notion API | 2022-06-28 |
| Export | ReportLab + python-docx | Latest |
| Validation | Pydantic | v2 |
| Container | Docker + Compose | Latest |

---

## 🔐 Security

- `.env` never committed — all secrets via `python-dotenv`
- API request validation via Pydantic v2
- Rate limiting on assistant endpoints via Redis (30 req/min)
- Idempotency lock prevents duplicate Notion tickets
- Anti-hallucination: evidence_score threshold + explicit refusal prompt
- PostgreSQL connection managed with proper open/close lifecycle

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">

**Built with Azure OpenAI · LangChain · LangGraph · FastAPI · Streamlit · ChromaDB · Redis · Notion**

⭐ Star this repo if it helped you!

[GitHub](https://github.com/Rrensisorathiya/DocForgeHub) · [Issues](https://github.com/Rrensisorathiya/DocForgeHub/issues)

</div>


#-------------------------------------------------------------------------------

<!-- # DocForgeHub — CiteRAG+

<div align="center">

![DocForgeHub Banner](https://img.shields.io/badge/DocForgeHub-CiteRAG%2B-1e3c72?style=for-the-badge&logo=openai&logoColor=white)

**AI-Powered Enterprise Document Generation & RAG Intelligence Platform**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4.1--mini-0078D4?style=flat-square&logo=microsoftazure)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?style=flat-square&logo=postgresql)](https://postgresql.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=flat-square)](https://trychroma.com)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?style=flat-square&logo=redis)](https://redis.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful_Agent-1C3C3C?style=flat-square&logo=langchain)](https://langchain-ai.github.io/langgraph)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Developed during internship at **Turabit AI** · April 2026*

</div>

---

## What is DocForgeHub?

DocForgeHub is a **production-ready enterprise AI platform** that solves two critical business problems:

1. **Document Creation** takes 4–6 hours manually → DocForgeHub generates in **under 60 seconds** with consistent quality, compliance language, and proper formatting
2. **Knowledge Retrieval** requires manually reading hundreds of pages → CiteRAG+ answers questions **instantly** with citations from your document library

The platform consists of **three integrated projects** running on a shared codebase:

| | Project | What it does |
|---|---|---|
| 📄 | **DocForge Hub** | AI document generation — 13 departments, 130 document types |
| 🔍 | **CiteRAG Lab** | RAG-powered Q&A with citations from Notion knowledge base |
| 🤖 | **Stateful Assistant** | LangGraph agent with memory, Notion ticketing, multi-turn context |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit UI  :8501                          │
│   DocForge Hub │ CiteRAG Lab │ Stateful Assistant (LangGraph)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP
┌──────────────────────────▼──────────────────────────────────────┐
│                   FastAPI Backend  :8000                        │
│  /documents/*  │  /rag/*  │  /assistant/*  │  /tickets/*       │
└───┬─────────┬──────────┬────────────┬────────────┬─────────────┘
    │         │          │            │            │
┌───▼──┐ ┌───▼──┐ ┌─────▼────┐ ┌────▼────┐ ┌────▼────┐
│ PG   │ │Redis │ │ChromaDB  │ │ Azure   │ │ Notion  │
│ SQL  │ │Cache │ │910 chunks│ │ OpenAI  │ │   API   │
└──────┘ └──────┘ └──────────┘ └─────────┘ └─────────┘
```

---

## Project 1 — DocForge Hub: Document Generation

### How it works

```
User selects Department + Document Type
            │
            ▼
    FastAPI loads Template (PostgreSQL JSONB sections)
            │
            ▼
    Dynamic Questionnaire (Common + Metadata + Doc-specific)
            │
            ▼
    LangChain builds structured prompt
            │
            ▼
    Azure OpenAI GPT-4.1-mini generates section by section
            │
            ▼
    Quality Validator scores 0–100 (grade A–F)
       ┌────┴────┐
   score < 60   score ≥ 60
       │             │
   Regenerate    Save to PostgreSQL
                      │
            ┌─────────┼──────────┐
            ▼         ▼          ▼
          Export   Publish    Library
        PDF/DOCX  to Notion   View
        Markdown  v1→v2→v3
```

### Coverage

| Department | Document Types | Examples |
|---|---|---|
| HR & People Operations | 10 | Offer Letter, Employment Contract, HR Policy Manual, Code of Conduct |
| Legal & Compliance | 10 | NDA, MSA, DPA, Privacy Policy, Terms of Service |
| Sales & Customer Facing | 10 | Sales Proposal, SLA, Customer Onboarding Guide |
| Engineering & Operations | 10 | SRS, TDD, API Documentation, DevOps Runbook |
| Product & Design | 10 | PRD, Product Roadmap, UX Research, Design System |
| Marketing & Content | 10 | Marketing Strategy, Brand Guidelines, SEO Strategy |
| Finance & Operations | 10 | Budget Plan, Revenue Forecast, Cash Flow Statement |
| Partnership & Alliances | 10 | Partnership Agreement, MoU, Channel Partner Agreement |
| IT & Internal Systems | 10 | IT Policy Manual, Access Control Policy, Disaster Recovery |
| Platform & Infrastructure | 10 | Infrastructure Architecture, Cloud Deployment Guide |
| Data & Analytics | 10 | Data Governance Policy, BI Report, KPI Dashboard |
| QA & Testing | 10 | Test Plan, Bug Report, Automation Test Plan |
| Security & Information | 10 | Information Security Policy, Penetration Testing Report |
| **Total** | **130** | **230+ documents generated** |

### Quality Validation

```
Document Generated
        │
        ▼
┌───────────────────────────────────┐
│  Quality Checks (Weighted Score)  │
│  ─────────────────────────────── │
│  Word Count Check        20%      │
│  Section Coverage        25%      │
│  Content Relevance       25%      │
│  Professional Tone       15%      │
│  Compliance Markers      15%      │
└───────────────┬───────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
A (90-100)  B (75-89)  C/D/F (<75)
   ✅ Ship   ✅ OK      🔄 Regenerate
```

---

## Project 2 — CiteRAG Lab: RAG AI Assistant

### Ingestion Pipeline

```
Notion Database (129 documents)
        │
        ▼ Notion API (paginated 100/req)
Content Extraction
(headings, paragraphs, tables, bullets)
        │
        ▼ Section-aware splitter
Chunking: 500 words, 50-word overlap
→ 910 chunks total
        │
        ▼ SentenceTransformer all-MiniLM-L6-v2
Embeddings: 384 dimensions
        │
        ▼ Cosine similarity
ChromaDB Vector Store
(persistent, with metadata filters)
        │
        ▼ Redis
Ingestion Cache (TTL: 24h)
Skip already-processed pages
```

### Q&A Pipeline

```
User Question
     │
     ▼ Tool 1
refine_query ──► Azure OpenAI rewrites query
     │           Returns: refined + keywords + suggestions
     ▼ Tool 2
search_docs ───► ChromaDB similarity search
     │           Filters: doc_type, department, industry, version
     │           Returns: top-5 chunks with citations
     ▼ Redis
Cache Check ───► HIT: <100ms response
     │           MISS: continue to generation
     ▼ Anti-hallucination
Answer Generation
"Answer ONLY from context. If missing, say so."
Temperature: 0.2, Max tokens: 800
     │
     ▼
Grounded Answer + Citations
Format: "Doc Title → Section Name"
     │
     ▼ Redis
Cache Answer (TTL: 30min)
Save to Session History
```

### Tool 3: compare_docs

```
Query + Doc Type A + Doc Type B
        │
        ├──► Retrieve top-4 chunks from Doc A
        ├──► Retrieve top-4 chunks from Doc B
        │
        ▼
Azure OpenAI structured comparison
Returns JSON:
{
  "doc_a_points": [...],   ← unique to Doc A
  "doc_b_points": [...],   ← unique to Doc B
  "similarities": [...],
  "differences": [...],
  "recommendation": "..."
}
```

### Redis Caching Strategy

| Cache | Key | TTL | Purpose |
|---|---|---|---|
| Retrieval results | `retrieval:MD5(query+filters)` | 1 hour | Avoid duplicate vector searches |
| Query refinements | `refine:hash(query)` | 1 hour | Reuse LLM rewrites |
| Q&A answers | `answer:hash(question+filters)` | 30 min | Instant repeated queries |
| Session history | `session:{session_id}` | 30 min | Multi-turn context |
| Notion rate limit | `notion_rate:{db_id}:{minute}` | 60 sec | Max 90 API calls/min |
| Ingestion status | `ingested:{page_id}` | 24 hours | Skip re-processing |

### RAGAS Evaluation

```
Test Dataset (5 questions)
        │
        ▼
RAG Pipeline runs each question
        │
        ▼
RAGAS scores 4 metrics:

Faithfulness        → Is answer grounded in context?
Answer Relevancy    → Does answer address the question?
Context Precision   → Are retrieved chunks relevant?
Context Recall      → Is all necessary info retrieved?

        │
        ▼
Results saved: eval/results/ragas_TIMESTAMP.json
(full dataset + per-question + config + scores)
```

---

## Project 3 — Stateful Assistant: LangGraph Agent

### Architecture

```
User Message
     │
     ▼
LangGraph StateGraph
     │
     ├──► Node: load_context
     │    Load thread history from Redis + PostgreSQL
     │
     ├──► Node: retrieve
     │    ChromaDB vector search with thread context
     │
     ├──► Node: grade_documents
     │    Score retrieved chunks for relevance (0.0–1.0)
     │    evidence_score threshold: 0.3
     │
     ├──► Node: generate
     │    Azure OpenAI with full conversation history
     │    Anti-hallucination enforced
     │
     ├──► Node: check_answer_quality
     │    Is the answer grounded and complete?
     │          │
     │    ┌─────┴─────┐
     │    ▼           ▼
     │  Good       Insufficient
     │    │             │
     │    ▼             ▼
     │  Return       Node: create_ticket
     │  Answer       Create Notion ticket with:
     │               - Original question
     │               - Department + priority
     │               - Evidence score
     │               - Assigned owner
     │               Returns Notion URL to user
     │
     └──► Node: save_state
          Save to PostgreSQL + Redis (thread memory)
```

### Thread Memory

```
Thread Created (UUID)
     │
     ├── PostgreSQL: assistant_threads table
     │   (thread_id, user_id, industry, department, created_at)
     │
     ├── PostgreSQL: assistant_messages table
     │   (thread_id, role, content, citations, ticket_url)
     │
     └── Redis: session:{thread_id}
         (last 20 messages, TTL: 30 min)
```

### Notion Ticket System

```
Answer quality insufficient
     │
     ▼
Ticket created in Notion database:
{
  "Question":         user's original query,
  "Department":       detected from context,
  "Priority":         auto-assigned (high/medium/low),
  "Status":           "open",
  "Assigned Owner":   department head,
  "Evidence Score":   0.0–1.0,
  "Notion URL":       shareable link
}
     │
     ▼
Ticket returned to user in chat
Status can be updated: open → in_progress → resolved → closed
```

---

## Tech Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | Streamlit | 1.32+ | Interactive UI for all 3 projects |
| Backend | FastAPI | 0.110+ | REST API — 25+ endpoints |
| LLM | Azure OpenAI GPT-4.1-mini | 2025-01-01 | Generation, Q&A, evaluation |
| Embeddings | SentenceTransformer all-MiniLM-L6-v2 | 2.x | 384-dim text embeddings |
| Vector DB | ChromaDB | 0.4+ | Semantic chunk storage + search |
| Cache | Redis | 7.0+ | Session, retrieval, rate limiting |
| Relational DB | PostgreSQL | 14+ | Documents, templates, threads, tickets |
| Knowledge Base | Notion API | 2022-06-28 | Document publishing + RAG source |
| Agent Framework | LangGraph | 0.1+ | Stateful multi-node agent graph |
| RAG Framework | LangChain | 0.1+ | Pipeline orchestration |
| Evaluation | RAGAS | 0.1+ | Automated RAG quality measurement |
| PDF Export | ReportLab | 4.x | Professional PDF generation |
| DOCX Export | python-docx | 1.x | Word document generation |
| HTTP Client | httpx | 0.27+ | Azure OpenAI proxy bypass |

---

## Database Schema

```
departments ──(1:N)──► templates ──(1:N)──► generated_documents
                                                    │
document_types ──(1:N)──► templates        document_metadata
                                                    │
questionnaires ◄──(1:N)── departments      generation_jobs
                                                    │
assistant_threads ──(1:N)──► assistant_messages   document_versions

assistant_tickets (Notion-synced)
  thread_id | question | department | priority | status | evidence_score | notion_url
```

---

## API Reference

### Project 1 — Document Generation
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/generate` | Generate document with AI |
| `GET` | `/documents/` | List with filters |
| `GET` | `/documents/{id}` | Get with full content |
| `DELETE` | `/documents/{id}` | Delete document |
| `POST` | `/documents/regenerate/{id}` | Regenerate document |
| `GET` | `/export/{id}/{format}` | Export PDF/DOCX/MD |
| `PUT` | `/templates/{id}/sections` | Edit template sections |
| `POST` | `/documents/{id}/mark-notion` | Mark as published |

### Project 2 — RAG
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/rag/retrieve` | Vector search with filters |
| `POST` | `/rag/answer` | Grounded Q&A with citations |
| `POST` | `/rag/compare` | Compare two document types |
| `POST` | `/rag/refine` | AI query optimization |
| `POST` | `/rag/ingest` | Ingest Notion docs (background) |
| `GET` | `/rag/stats` | Vector store + Redis stats |
| `POST` | `/rag/eval/run` | Trigger RAGAS evaluation |
| `GET` | `/rag/eval/results` | Latest evaluation results |

### Project 3 — Assistant
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/assistant/threads` | Create new conversation thread |
| `POST` | `/assistant/chat` | Send message to LangGraph agent |
| `GET` | `/tickets/` | List tickets with filters |
| `GET` | `/tickets/stats` | Ticket statistics by status |
| `PUT` | `/tickets/{id}/status` | Update ticket status |

---

## Quick Start

### Prerequisites

```bash
Python 3.10+  |  PostgreSQL 14+  |  Redis 7.0+  |  Node.js 18+
Azure OpenAI API access  |  Notion Integration Token
```

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Rrensisorathiya/DocForgeHub.git
cd DocForgeHub
git checkout AssistantStateFlow

# 2. Virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Configure .env
cp .env.example .env
# Fill in your Azure OpenAI, PostgreSQL, Notion, Redis credentials

# 5. Database setup
psql -U postgres -f Schema/schema.sql
python3 migrations/add_assistant_tables.py

# 6. Ingest Notion documents
python3 -c "
import os; from dotenv import load_dotenv; load_dotenv()
from rag.ingestion import ingest_notion_documents
r = ingest_notion_documents(os.getenv('NOTION_TOKEN'), os.getenv('NOTION_DATABASE_ID'))
print(f'Ingested: {r[\"total_chunks\"]} chunks from {r[\"total_pages\"]} pages')
"
```

### Running

```bash
# Terminal 1: Redis
sudo systemctl start redis && redis-cli ping   # → PONG

# Terminal 2: FastAPI backend
uvicorn main:app --reload --port 8000 --timeout-keep-alive 600

# Terminal 3: Streamlit frontend
streamlit run document_app.py --server.port 8501
```

### Health Check

```bash
redis-cli ping                              # PONG
curl http://localhost:8000/system/health    # {"status":"ok","database":"connected"}
curl http://localhost:8000/rag/stats        # {"total_chunks":910,...}
# Browser: http://localhost:8501
```

---

## Environment Variables

```env
# Azure OpenAI
AZURE_LLM_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_LLM_KEY=your_api_key
AZURE_LLM_DEPLOYMENT_41_MINI=gpt-4.1-mini
AZURE_LLM_API_VERSION=2025-01-01-preview

# PostgreSQL
DB_HOST=localhost
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432

# Notion
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=your_database_id

# Redis + ChromaDB
REDIS_URL=redis://localhost:6379
CHROMA_PERSIST_DIR=./chroma_db
```

---

## Project Structure

```
DocForgeHub/
├── main.py                      # FastAPI app — router registration
├── document_app.py              # Streamlit UI — all pages (~5000 lines)
├── db.py                        # PostgreSQL connection manager
├── requirements.txt
│
├── api/                         # FastAPI route handlers
│   ├── documents.py             # Document CRUD + generation
│   ├── templates.py             # Template management
│   ├── questionnaires.py        # Question fetching
│   ├── retrieve.py              # RAG endpoints /rag/*
│   ├── assistant.py             # LangGraph assistant + tickets
│   ├── export.py                # PDF/DOCX/MD export
│   └── system.py                # Health + stats
│
├── services/                    # Business logic
│   ├── document_generator.py    # Azure OpenAI generation pipeline
│   ├── notion_service.py        # Notion publish + version control
│   └── export_service.py        # Export formatting
│
├── rag/                         # Project 2 — RAG pipeline
│   ├── vector_store.py          # ChromaDB wrapper
│   ├── ingestion.py             # Notion → chunks → ChromaDB
│   ├── tools.py                 # search_docs, refine_query, compare_docs
│   └── chain.py                 # LangChain Q&A + session
│
├── assistant/                   # Project 3 — LangGraph agent
│   ├── graph.py                 # StateGraph definition + nodes
│   ├── memory.py                # Thread + message persistence
│   ├── tools.py                 # Agent tools
│   └── ticketing.py             # Notion ticket creation
│
├── cache/
│   └── redis_service.py         # Unified cache service
│
├── eval/
│   ├── ragas_eval.py            # RAGAS evaluation runner
│   └── results/                 # Saved evaluation JSON files
│
├── migrations/
│   └── add_assistant_tables.py  # Project 3 DB migration
│
├── utils/
│   └── logger.py                # Centralized logging
│
└── Schema/
    ├── schema.sql               # PostgreSQL DDL
    └── new_content.json         # Template sections data
```

---

## Key Metrics

| Metric | Value |
|---|---|
| Departments covered | 13 |
| Document types | 130 |
| Documents generated | 230+ |
| Notion pages in knowledge base | 129 |
| ChromaDB chunks | 910 |
| API endpoints | 25+ |
| Average quality score | 85+/100 |
| RAG tools implemented | 3 |
| Cache hit rate (after 1h) | ~40% |
| Document generation time | < 90 seconds |
| Manual baseline | 4–6 hours |
| **Time saved per document** | **~97%** |

---

## UI Pages

| Page | Project | Features |
|---|---|---|
| Home | P1 | System stats, recent documents, quick navigation |
| Generate | P1 | 3-step wizard: type → questionnaire → AI generation |
| Library | P1 | View, regenerate, delete, download (PDF/DOCX/MD) |
| Templates | P1 | Edit template sections — add, remove, reorder |
| Questionnaires | P1 | Preview questions by dept + type |
| Publish to Notion | P1 | Individual + bulk publishing, version control |
| Stats | P1 | System metrics, job history, department map |
| AI Assistant | P2 | Chat + Search Inspector + Compare Docs + RAGAS |
| Stateful Assistant | P3 | LangGraph agent + conversation threads + tickets |

---

## Anti-Hallucination Design

```
System Prompt (enforced on every generation):
"ALWAYS base your answer on the provided context chunks.
NEVER make up information not present in the context.
If the context does not contain enough information,
explicitly say: 'I don't have enough information in
the knowledge base to answer this accurately.'"

Additional safeguards:
→ Temperature: 0.2 (factual, not creative)
→ Context limit: 4000 chars (focused retrieval)
→ LangGraph evidence scoring: threshold 0.3
→ Automatic Notion ticket when evidence insufficient
```

---

## Branch Guide

| Branch | Description |
|---|---|
| `main` | Stable — Project 1 (document generation) |
| `rag-pipeline` | Project 2 — CiteRAG Lab |
| `AssistantStateFlow` | Project 3 — LangGraph stateful assistant |

---

## Developed By

**Rensi Soratiya** — *NLP Intern, Turabit AI*

> This project was developed as part of an internship at Turabit AI, demonstrating production-grade AI engineering across document automation, retrieval-augmented generation, and stateful LLM agent design.

---

<div align="center">

**DocForgeHub · CiteRAG+ · Stateful Assistant**

*Built with Azure OpenAI · LangGraph · ChromaDB · Redis · PostgreSQL · Notion*

*Turabit AI · 2026*



</div>
<!-- # 🚀 DocForgeHub — AI-Powered Enterprise Document Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=for-the-badge)
![Notion](https://img.shields.io/badge/Notion-API-000000?style=for-the-badge&logo=notion&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**An intelligent, end-to-end enterprise document platform combining AI-powered generation with a Notion-backed RAG knowledge base — built for 13 SaaS departments, 130 templates, and production-grade reliability.**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [API Reference](#-api-endpoints) • [RAG Assistant](#-project-2--rag-assistant)

</div>

---

## 📌 Overview

DocForgeHub is a **two-project enterprise platform**:

| | Project 1 | Project 2 |
|---|---|---|
| **Name** | Document Generator | RAG Assistant |
| **Purpose** | AI document generation + Notion publishing | Grounded Q&A over Notion knowledge base |
| **Stack** | FastAPI + Streamlit + PostgreSQL + Azure OpenAI | ChromaDB + Redis + LangChain + RAGAS |
| **Key output** | PDF / DOCX / Markdown documents | Cited answers + comparison + evaluation |

---

## ✨ Features

### 🏗️ Project 1 — Document Generator

| Feature | Description |
|---|---|
| 🤖 **AI Generation** | LangChain + Azure OpenAI (GPT-4) multi-step document generation |
| 📄 **130 Templates** | 13 departments × 10 doc types — NDA, SLA, HR Policy, TDD, and more |
| ✏️ **Section Editor** | Add / remove / reorder template sections — live in PostgreSQL |
| 📋 **Smart Questionnaires** | Structured input collection per department + doc type |
| 🔢 **Auto Versioning** | Same dept + doc type → version auto-increments in Notion |
| 📓 **Notion Publishing** | One-click publish with full metadata + open-in-Notion link |
| 📤 **Export Formats** | PDF (ReportLab), DOCX (python-docx), Markdown |
| ✅ **Quality Validation** | Score 0–100, Grade A–D, pass/fail checks, word count |
| 🔄 **Regenerate** | Re-run generation on same answers for quality improvement |
| 📊 **Live Stats** | Real-time dashboard — templates, documents, jobs, departments |

### 🤖 Project 2 — RAG Assistant

| Feature | Description |
|---|---|
| 💬 **Grounded Q&A** | Answers from Notion knowledge base with citations |
| 🔍 **Retrieval Inspector** | See exact chunks, scores, metadata per search |
| ✨ **Query Refiner** | AI rewrites vague queries for better retrieval |
| ⚖️ **Doc Comparison** | Side-by-side compare two document types on any question |
| 📈 **RAGAS Evaluation** | Faithfulness, Answer Relevancy, Context Precision, Context Recall |
| 🗄️ **Redis Caching** | Cache retrieval results + session context + rate limiting |
| 🚫 **Anti-Hallucination** | Explicit "not available" when info is missing |
| 🏷️ **Metadata Filters** | Filter by industry, department, doc type, version |
| 💾 **Session Memory** | Multi-turn conversation with Redis-backed history |
| 📊 **Evaluation History** | Reproducible: config + dataset + outputs + scores stored |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT FRONTEND                        │
│  Home │ Generate │ Library │ Templates │ Notion │ AI Assistant  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────────┐
│                       FASTAPI BACKEND                            │
│                                                                  │
│  /documents/*    /templates/*    /rag/*    /system/*            │
│                                                                  │
│  ┌─────────────┐  ┌────────────┐  ┌──────────────────────────┐ │
│  │  Document   │  │  Template  │  │      RAG Pipeline        │ │
│  │  Generator  │  │  Section   │  │                          │ │
│  │             │  │  Editor    │  │  refine → retrieve →     │ │
│  │ LangChain + │  │            │  │  generate → cite         │ │
│  │ Azure OpenAI│  │ PostgreSQL │  │                          │ │
│  └──────┬──────┘  └─────┬──────┘  └───────┬──────────────────┘ │
└─────────┼───────────────┼─────────────────┼────────────────────┘
          │               │                 │
   ┌──────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
   │ PostgreSQL  │  │ PostgreSQL │  │  ChromaDB   │
   │ Documents   │  │ Templates  │  │ 1440 Chunks │
   │ Jobs        │  │ Questions  │  │ Embeddings  │
   └─────────────┘  └────────────┘  └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │    Redis    │
                                    │ Cache+Rate  │
                                    │ Sessions    │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │   Notion    │
                                    │  Knowledge  │
                                    │    Base     │
                                    └─────────────┘
```

---

## 🗂️ Project Structure

```
DocForgeHub/
│
├── api/                          # FastAPI route handlers
│   ├── documents.py              # Document generation & retrieval
│   ├── export.py                 # PDF / DOCX export
│   ├── notion_api.py             # Notion publishing
│   ├── questionnaires.py         # Questionnaire CRUD
│   ├── retrieve.py               # RAG endpoints (Project 2)
│   ├── system.py                 # Health + stats
│   └── templates.py              # Template management + section editor
│
├── rag/                          # RAG Pipeline (Project 2)
│   ├── __init__.py
│   ├── chain.py                  # ask() + compare() — LLM generation
│   ├── ingestion.py              # Notion → ChromaDB ingestion
│   ├── tools.py                  # search_docs() + refine_query()
│   └── vector_store.py           # ChromaDB wrapper
│
├── cache/                        # Redis layer
│   ├── __init__.py
│   └── redis_service.py          # Cache + rate limiting + sessions
│
├── eval/                         # RAGAS Evaluation (Project 2)
│   ├── __init__.py
│   └── ragas_eval.py             # Faithfulness, Relevancy, Recall, Precision
│
├── eval_results/                 # Stored evaluation runs (JSON)
│
├── services/                     # Core service layer
│   ├── azure_client.py           # Azure OpenAI config
│   ├── document_exporter.py      # PDF/DOCX — cover page, sections
│   ├── document_generator.py     # LLM generation logic
│   ├── document_repository.py    # Document CRUD
│   ├── document_validator.py     # Quality score + grade
│   ├── langchain_service.py      # LangChain wrapper
│   ├── notion_service.py         # Notion API + version control
│   ├── prompt_builder.py         # Dynamic prompt construction
│   ├── questionnaire_repository.py
│   └── template_repository.py
│
├── migrations/                   # DB migrations + seeders
│   └── seed_from_json.py
│
├── Schema/                       # JSON data schemas
│   ├── new_content.json          # 13 dept × 10 doc type templates
│   ├── new_Question_Answer.json  # Questionnaire definitions
│   └── new_metadata.json
│
├── utils/
│   └── logger.py
│
├── chroma_db/                    # ChromaDB vector store (1440+ chunks)
├── main.py                       # FastAPI entry point
├── document_app.py               # Streamlit frontend
├── db.py                         # PostgreSQL connection
├── requirements.txt
├── .env                          # Environment variables (not committed)
├── .gitignore
└── Readme.MD
```

---

## 🔄 How It Works

### Project 1 — Document Generation Flow

```
User fills Questionnaire
         │
         ▼
Fetch Template sections    ◄── template_repository.py
         │
         ▼
Build LLM Prompt           ◄── prompt_builder.py
         │
         ▼
Azure OpenAI generates     ◄── langchain_service.py
content per section             azure_client.py
         │
         ▼
Validate document          ◄── document_validator.py
(Score, Grade, Checks)
         │
         ▼
Export PDF / DOCX          ◄── document_exporter.py
         │
         ▼
Publish to Notion          ◄── notion_service.py
(Auto-version control)
```

### Project 2 — RAG Pipeline Flow

```
User asks a question
         │
         ▼
refine_query()             ◄── rag/tools.py (Azure OpenAI)
         │
         ▼
search_docs()              ◄── rag/tools.py → ChromaDB
(with metadata filters)
         │
         ▼
Redis cache check          ◄── cache/redis_service.py
         │
         ▼
ask() → LLM generates      ◄── rag/chain.py (Azure OpenAI)
grounded answer
         │
         ▼
Return answer +            ◄── api/retrieve.py
citations + rationale
```

---

## 🏢 Supported Departments & Documents

| Department | Doc Types |
|---|---|
| HR & People Operations | Offer Letter, Employment Contract, Employee Handbook, HR Policy Manual, Onboarding Checklist, Performance Appraisal Form, Leave Policy, Code of Conduct, Exit Interview, Training Plan |
| Legal & Compliance | MSA, NDA, DPA, Privacy Policy, Terms of Service, Compliance Audit, Risk Assessment, IP Agreement, Vendor Contract, Regulatory Checklist |
| Sales & Customer Facing | Sales Proposal, Sales Playbook, Customer Onboarding Guide, SLA, Pricing Strategy, Case Study, Sales Contract, CRM Guidelines, Quarterly Report, Customer Feedback |
| Engineering & Operations | SRS, TDD, API Documentation, Deployment Guide, Release Notes, System Architecture, Incident Report, RCA, DevOps Runbook, Change Management Log |
| Product & Design | PRD, Product Roadmap, Feature Specification, UX Research, Wireframe Documentation, Design System Guide, User Persona, A/B Testing Report, Product Strategy, Competitive Analysis |
| Marketing & Content | Marketing Strategy, Content Calendar, Brand Guidelines, SEO Strategy, Campaign Report, Social Media Strategy, Email Plan, Press Release, Market Research, Lead Generation |
| Finance & Operations | Budget Plan, Financial Statement, Expense Policy, Invoice Template, Procurement Policy, Revenue Forecast, Cash Flow, Vendor Payment Policy, Cost Analysis, Financial Risk |
| + 6 more departments | Partnership, IT, Platform & Infra, Data & Analytics, QA & Testing, Security & Assurance |

**Total: 13 Departments × ~10 Doc Types = 130 Templates**

---

## ⚙️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.10+ | Core runtime |
| **Frontend** | Streamlit 1.28+ | Interactive UI |
| **API** | FastAPI + Uvicorn | REST backend |
| **LLM** | Azure OpenAI GPT-4.1 Mini | Document generation + RAG |
| **LLM Framework** | LangChain + LangGraph | Pipelines + agents |
| **Vector Store** | ChromaDB | RAG chunk storage |
| **Embeddings** | Azure OpenAI text-embedding-ada-002 | Semantic search |
| **Cache / Sessions** | Redis 7.0+ | Retrieval cache + rate limiting |
| **Database** | PostgreSQL 15+ | Templates, documents, jobs |
| **Notion** | Notion API v2022-06-28 | Knowledge base + publishing |
| **Export** | ReportLab + python-docx | PDF + DOCX |
| **Evaluation** | RAGAS-style scoring | RAG quality metrics |
| **Validation** | Pydantic v2 | Schema validation |
| **Containerisation** | Docker + docker-compose | Deployment |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Redis 7.0+
- Azure OpenAI access (API key + endpoint + deployments)
- Notion integration token

### 1. Clone & Setup

```bash
git clone https://github.com/Rrensisorathiya/DocForgeHub.git
cd DocForgeHub
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in the project root:

```env
# ── Azure OpenAI — LLM ──────────────────────────────────
AZURE_OPENAI_LLM_KEY=your_llm_api_key
AZURE_LLM_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_LLM_API_VERSION=2024-02-15-preview
AZURE_LLM_DEPLOYMENT_41_MINI=gpt-4.1-mini

# ── Azure OpenAI — Embeddings ───────────────────────────
AZURE_OPENAI_EMB_KEY=your_embedding_api_key
AZURE_EMB_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_EMB_API_VERSION=2024-02-15-preview
AZURE_EMB_DEPLOYMENT=text-embedding-ada-002

# ── PostgreSQL ──────────────────────────────────────────
DB_HOST=localhost
DB_NAME=saas_doc_engine
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432

# ── Redis ───────────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ── Notion ──────────────────────────────────────────────
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=your_database_id

# ── RAG ─────────────────────────────────────────────────
CHROMA_DIR=./chroma_db
EVAL_RESULTS_DIR=./eval_results
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=64

# ── App ─────────────────────────────────────────────────
APP_ENV=development
DEBUG=false
```

### 3. Start Services

```bash
# Start Redis
sudo systemctl start redis

# Verify Redis
redis-cli ping   # → PONG
```

### 4. Setup Database

```bash
# Create tables + seed data
python migrations/seed_from_json.py
```

### 5. Start Backend

```bash
uvicorn main:app --reload --port 8000
```

### 6. Start Frontend

```bash
# New terminal
streamlit run document_app.py
```

### 7. Ingest Notion Documents (RAG Setup)

```bash
curl -X POST http://localhost:8000/rag/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "token": "your_notion_token",
       "database_id": "your_database_id"
     }'

# Verify ingestion
curl http://localhost:8000/rag/stats
```

### Access

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI Backend | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

---

## 📡 API Endpoints

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/system/health` | Health check + DB status |
| `GET` | `/system/stats` | Templates, docs, jobs count |

### Templates

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/templates/` | List all templates |
| `GET` | `/templates/{id}` | Get single template |
| `PUT` | `/templates/{id}/sections` | Update template sections |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/generate` | Generate document via LLM |
| `GET` | `/documents/` | List all documents |
| `GET` | `/documents/{id}` | Get document by ID |
| `DELETE` | `/documents/{id}` | Delete document |
| `POST` | `/documents/regenerate/{id}` | Regenerate with same answers |
| `POST` | `/documents/{id}/mark-notion` | Mark as published in Notion |

### Export

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/export/{id}/pdf` | Export document as PDF |
| `GET` | `/export/{id}/docx` | Export document as DOCX |

### RAG (Project 2)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/rag/answer` | Grounded Q&A with citations |
| `POST` | `/rag/retrieve` | Raw chunk retrieval + scores |
| `POST` | `/rag/refine` | AI query refinement |
| `POST` | `/rag/compare` | Compare two doc types |
| `POST` | `/rag/ingest` | Ingest Notion docs to ChromaDB |
| `GET` | `/rag/stats` | Vector store + Redis stats |
| `GET` | `/rag/session/{id}` | Get session history |
| `DELETE` | `/rag/session/{id}` | Clear session |
| `POST` | `/rag/eval/run` | Run RAGAS evaluation |
| `GET` | `/rag/eval/results` | Latest eval results |
| `GET` | `/rag/eval/history` | All evaluation history |
| `DELETE` | `/rag/cache` | Clear Redis cache |

---

## 🤖 Project 2 — RAG Assistant

### Overview

The RAG Assistant uses the Notion document library (published from Project 1) as its knowledge base, enabling:

- **Grounded Q&A** — "What are the NDA confidentiality obligations?" → answer with source citations
- **Retrieval Inspector** — See which chunks were retrieved, their scores, and metadata
- **Query Refiner** — Vague query → precise legal/business search phrase
- **Doc Comparison** — "Compare MSA vs SLA termination clauses" → side-by-side with AI summary
- **RAGAS Evaluation** — Measure pipeline quality across 4 metrics

### RAG Pipeline

```
Question → refine_query() → search_docs() → Redis cache
                                  ↓
                           ChromaDB (1440+ chunks)
                                  ↓
                    ask() → Azure OpenAI → Grounded answer
                                  ↓
                    citations + rationale + session save
```

### Metadata Filters

Filter retrieval by:

```python
{
  "industry":   "SaaS",
  "doc_type":   "Master Service Agreement (MSA)",
  "department": "Legal & Compliance",
  "version":    "v1"
}
```

### RAGAS Metrics

| Metric | Measures |
|---|---|
| **Faithfulness** | Is the answer grounded in retrieved chunks? (no hallucination) |
| **Answer Relevancy** | Does the answer address the question? |
| **Context Precision** | Are retrieved chunks relevant? (no noise) |
| **Context Recall** | Were all needed chunks retrieved? |

### Redis Usage

| Key Pattern | Purpose | TTL |
|---|---|---|
| `search:{hash}` | Retrieval result cache | 5 min |
| `answer:{hash}` | Answer cache | 5 min |
| `refine:{hash}` | Refined query cache | 10 min |
| `session:{id}` | Conversation history | 1 hour |
| `ingested:{page_id}` | Ingestion dedup | 24 hours |
| `rl:{session_id}` | Rate limiting | 1 min |

---

## 📊 Document Quality Validation

Every generated document is automatically validated:

| Metric | Description |
|---|---|
| **Quality Score** | 0–100 based on content completeness |
| **Grade** | A (90+) / B (75+) / C (60+) / D (<60) |
| **Word Count** | Total words in generated document |
| **Checks** | Pass/Fail count with visual indicators |

---

## 🔢 Notion Version Control

```
Publish: Dept = HR, Doc Type = Offer Letter
         │
         ▼
Check existing in Notion
         │
    ┌────┴────┐
  Found    Not found
    │          │
    ▼          ▼
version+1     v1
```

| Publish # | Department | Doc Type | Notion Version |
|---|---|---|---|
| 1st | HR | Offer Letter | v1 |
| 2nd | HR | Offer Letter | v2 |
| 1st | Finance | Invoice Template | v1 |

---

## 🗃️ Database Schema

### PostgreSQL Tables

| Table | Purpose |
|---|---|
| `templates` | Document templates with section structures |
| `questionnaires` | Questions per department + doc type |
| `generated_documents` | All generated documents + Notion metadata |
| `generation_jobs` | Background job tracking |
| `departments` | Department registry |
| `document_types` | Document type registry |

### Notion Database Properties

| Property | Type | Description |
|---|---|---|
| Title | Title | `{Doc Type} — {Company}` |
| Department | Select | HR, Finance, Legal, etc. |
| Document Type | Select | Document type |
| Industry | Select | Company industry |
| Version | Rich Text | v1, v2, v3... |
| Status | Select | Published / Draft |
| Company | Rich Text | Company name |
| Word Count | Number | Auto-calculated |
| Published At | Date | Publication date |

---

## 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Services started:
# - streamlit:  http://localhost:8501
# - fastapi:    http://localhost:8000
# - postgres:   localhost:5432
# - redis:      localhost:6379
```

---

## 🔐 Security & Best Practices

- `.env` file never committed (see `.gitignore`)
- API keys loaded via `python-dotenv`
- Rate limiting on RAG endpoints via Redis
- Anti-hallucination: explicit "not in documents" response
- PostgreSQL connection pooling via `psycopg2`
- Input validation via Pydantic v2 models

---

## 📦 Key Dependencies

```txt
# Core
fastapi>=0.104.0
uvicorn>=0.24.0
streamlit>=1.28.0
python-dotenv>=1.0.0
pydantic>=2.0.0

# LLM & RAG
langchain>=0.1.0
langchain-openai>=0.1.0
langchain-community>=0.1.0
langgraph>=0.1.0
openai>=1.0.0
chromadb>=0.4.0
tiktoken>=0.5.0

# Database
psycopg2-binary>=2.9.0
redis>=5.0.0

# Export
reportlab>=4.0.0
python-docx>=1.0.0

# Notion
notion-client>=2.0.0
requests>=2.31.0
```

```bash
pip install -r requirements.txt
```

---

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/system/health

# RAG answer test
curl -X POST http://localhost:8000/rag/answer \
     -H "Content-Type: application/json" \
     -d '{"question": "What are NDA confidentiality obligations?", "session_id": "test"}'

# RAG stats
curl http://localhost:8000/rag/stats

# Run evaluation
curl -X POST http://localhost:8000/rag/eval/run \
     -H "Content-Type: application/json" \
     -d '{"top_k": 5, "use_refine": true}'
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "feat: add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 📬 Contact

For questions or support, open an issue on [GitHub](https://github.com/Rrensisorathiya/DocForgeHub).

---

<div align="center">

**Built with ❤️ using Azure OpenAI, LangChain, FastAPI, Streamlit, ChromaDB & Redis**

⭐ Star this repo if it helped you!

</div> -->

#-----------------------------------------------------------------------------------------------

<!-- # DocForgeHub — AI-Powered Document Generator

> An intelligent, template-driven document generation system that transforms structured questionnaire inputs into polished, department-specific documents — powered by **LangChain**, **LangGraph**, and **Azure OpenAI** — with one-click **Notion publishing**, automatic version control, and a modern Streamlit UI.

---

## ✨ Features

- 🤖 **AI-Powered Generation** — LangChain + LangGraph pipelines with Azure OpenAI (GPT-4) for context-aware, multi-step document generation
- 📄 **Template-Based Generation** — Fetches document templates by type and auto-renders structured sections
- ✏️ **Template Section Editor** — Users can add, remove, or reorder sections directly — changes reflect instantly in generation
- 📋 **Questionnaire-Driven Input** — Collects structured data via questionnaires to populate documents intelligently
- 🏢 **Multi-Department Support** — HR, Finance, Legal, Sales, IT, Operations, Security, QA, Data & Analytics, and more
- 📓 **One-Click Notion Publishing** — Publishes documents with full metadata (title, type, department, version, word count)
- 🔢 **Automatic Version Control** — Same Department + Doc Type → version auto-increments in Notion
- 🔗 **Open in Notion Button** — Direct link to published Notion page from the UI
- 📤 **PDF & DOCX Export** — Professionally formatted exports via ReportLab
- ✅ **Document Validation** — Quality score, grade, word count, and pass/fail checks with visual indicators
- 📊 **Live Stats Dashboard** — Real-time stats for templates, documents, and jobs
- 🎨 **Modern Dark UI** — Built with Streamlit, custom CSS, gradient cards, and metric boxes
- 🐳 **Docker Ready** — Includes `docker-compose.yml` for full stack deployment

---

## 🖥️ Local Access

| Service | URL |
|---|---|
| Streamlit Frontend | http://localhost:8501 |
| FastAPI Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Network Access | http://192.168.1.42:8501 |

---

## 🗂️ Project Structure

```
New_Doc_Hub/
│
├── api/                               # API Layer — FastAPI route handlers
│   ├── __init__.py
│   ├── documents.py                   # Document generation & retrieval endpoints
│   ├── export.py                      # PDF/DOCX export endpoints
│   ├── notion_api.py                  # Notion publishing endpoints
│   ├── questionnaires.py              # Questionnaire CRUD endpoints
│   ├── system.py                      # Health check & system info endpoints
│   └── templates.py                   # Template management + section edit endpoints
│
├── migrations/                        # Database Migrations
│   └── seed_from_json.py             # Database seeding from JSON files
│
├── Schema/                            # Data Schemas & Fixtures
│   ├── content.json
│   ├── metadata.json
│   ├── new_content.json
│   ├── new_metadata.json
│   ├── Question_Answer.json
│   ├── new_Question_Answer.json
│   ├── new_Question_Answer.py
│   ├── random.json
│   └── schemas/
│       └── document_schema.py         # Pydantic document schema models
│
├── services/                          # Core Service Layer
│   ├── azure_client.py                # Azure OpenAI client configuration
│   ├── document_exporter.py           # PDF/DOCX export — cover page, sections
│   ├── document_generator.py          # Core LLM-powered generation logic
│   ├── document_repository.py         # Document storage & retrieval
│   ├── document_validator.py          # Quality score, grade, checks validation
│   ├── langchain_service.py           # LangChain LLM service wrapper
│   ├── notion_service.py              # Notion API integration + version control
│   ├── prompt_builder.py              # Dynamic prompt construction
│   ├── questionnaire_repository.py    # Questionnaire data access layer
│   └── template_repository.py        # Template storage & retrieval
│
├── utils/                             # Utility Modules
│   └── logger.py                      # Logging configuration
│
├── main.py                            # FastAPI application entry point
├── document_app.py                    # Streamlit frontend application
├── db.py                              # Database connection & ORM setup
├── docforge.db                        # SQLite database (local dev)
├── Entity_Relationship_Diagram.png    # ER diagram
├── WireFrame_Diafram.odt              # UI/UX wireframe diagrams
├── table_creation_file.txt            # SQL table creation reference
├── requirements.txt                   # Python dependencies
└── .env                               # Environment variables (not committed)
```

---

## 🔄 How It Works

```
User Input (Questionnaire Answers)
          │
          ▼
    Fetch Template          ◄── template_repository.py
    by Document Type
          │
          ▼
    Extract Sections        ◄── document_generator.py
    (User-edited or default)
          │
          ▼
    LangChain + Azure       ◄── langchain_service.py
    Generate Content             azure_client.py
    per Section                  prompt_builder.py
          │
          ▼
    Validate Document       ◄── document_validator.py
    (Score, Grade, Checks)
          │
          ▼
    Export to PDF/DOCX      ◄── document_exporter.py
    (Cover + Sections)
          │
          ▼
    Publish to Notion       ◄── notion_service.py  (optional)
    (Auto-Versioning)
          │
          ▼
    Open in Notion          ◄── Direct link in UI
```

---

## ✏️ Template Section Editor

Users can customize document sections directly from the Templates page:

- **Edit** any template's sections with one click
- **Add** new sections at the end
- **Insert** sections at a specific position
- **Remove** any section with the delete button
- **Save** changes directly to PostgreSQL — generation uses updated sections instantly
- **Duplicate prevention** — same section name cannot be added twice

```
User edits sections in Templates page
        ↓
Saves to PostgreSQL (structure.sections)
        ↓
generate_document() fetches template from DB
        ↓
build_prompt() uses those exact sections
        ↓
AI generates ONLY those sections
```

---

## 🔢 Version Control Logic

DocForgeHub implements automatic Notion-based version control:

```
User publishes: Department = HR, Doc Type = Offer Letter
        │
        ▼
Check if same Dept + Doc Type exists in Notion
        │
        ├── Not found  ──►  Publish as v1
        │
        └── Found
              existing_version = page.properties.Version
              new_version = existing_version + 1
              Publish as v{new_version}
```

| Publish # | Department | Doc Type | Version |
|---|---|---|---|
| 1st | HR | Offer Letter | v1 |
| 2nd | HR | Offer Letter | v2 |
| 1st | Finance | Invoice Template | v1 |
| 2nd | Finance | Invoice Template | v2 |

---

## 📊 Document Quality Validation

Every generated document is automatically validated with visual metric cards:

| Metric | Description |
|---|---|
| Quality Score | 0–100 score based on content completeness |
| Grade | A / B / C / D based on score |
| Word Count | Total words in generated document |
| Checks | Pass/Fail count — red warning if any failures |

---

## 🏢 Supported Departments

| Department |
|---|
| HR & People Operations |
| Legal & Compliance |
| Sales & Customer Facing |
| Engineering & Operations |
| Product & Design |
| Marketing & Content |
| Finance & Operations |
| Partnership & Alliances |
| IT & Internal Systems |
| Platform & Infrastructure Operations |
| Data & Analytics |
| QA & Testing |
| Security & Information Assurance |

---

## 📄 Supported Document Types (130 Templates)

Each department supports 10 document types including NDA, Privacy Policy, SLA, Employment Contract, Offer Letter, Technical Spec, Risk Assessment, Compliance Report, and more.

---

## 🗃️ Notion Database Schema

| Field | Type | Description |
|---|---|---|
| Title | Title | `{Doc Type} — {Company Name}` |
| Department | Select | HR, Finance, Legal, etc. |
| Document Type | Select | Document type string |
| Industry | Select | Company industry |
| Version | Rich Text | Auto-incremented (v1, v2...) |
| Status | Select | Published / Draft / Reviewed |
| Company | Rich Text | Company name |
| Word Count | Number | Auto-calculated |
| Published At | Date | Publication date |

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Frontend | Streamlit |
| API Framework | FastAPI + Uvicorn |
| LLM Framework | LangChain, LangGraph, LangSmith |
| LLM Provider | Azure OpenAI (GPT-4) |
| PDF/DOCX Export | ReportLab |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Notion Integration | Notion API v2022-06-28 |
| Validation | Pydantic |
| Environment | Python venv |

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.10 or higher
- Azure OpenAI API access (API key + endpoint)
- Notion Internal Integration token — [notion.so/my-integrations](https://notion.so/my-integrations)
- PostgreSQL (for production)

### 1. Clone the Repository

```bash
git clone https://github.com/Rrensisorathiya/DocForgeHub.git
cd DocForgeHub
git checkout new-version
```

### 2. Create & Activate Virtual Environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-01

# Database (PostgreSQL)
DB_HOST=localhost
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432

# Notion
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# App
APP_ENV=development
LOG_LEVEL=INFO
```

### 5. Run Database Migrations

```bash
python migrations/migrate_complete.py
python migrations/migrate_json_to_db.py
python migrations/seed_from_json.py
```

### 6. Start the Backend

```bash
uvicorn main:app --reload --port 8000
```

### 7. Start the Frontend

```bash
# New terminal
streamlit run document_app.py
```

Frontend: `http://localhost:8501`
Backend API Docs: `http://localhost:8000/docs`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check & system info |
| GET | `/api/departments` | Get all available departments |
| GET | `/templates/` | Get all templates |
| PUT | `/templates/{id}/sections` | Update template sections |
| GET | `/api/questionnaires` | Get questionnaires by doc type |
| POST | `/api/documents/generate` | Generate a new document via LLM |
| GET | `/api/documents/{id}` | Retrieve a generated document |
| POST | `/api/documents/{id}/export` | Export document to PDF/DOCX |
| POST | `/api/documents/{id}/mark-notion` | Mark document as published in Notion |

---

## 🧪 Testing & Demo

```bash
# Quick demo run
python demo.py

# Run document generation tests
python test_document_generation.py

# Run LLM service tests
python services/test_llm.py
```

---

## 📦 Key Dependencies

```
langchain
langchain-openai
langgraph
langchain-core
langsmith
fastapi
uvicorn
streamlit
python-dotenv
reportlab
pydantic
notion-client
psycopg2-binary
requests
openai
```

```bash
pip install -r requirements.txt
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-version`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

## 📬 Contact

For questions or support, open an issue on [GitHub](https://github.com/Rrensisorathiya/DocForgeHub) or reach out to the project maintainer. --> -->