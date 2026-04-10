# 🚀 DocForgeHub — AI-Powered Enterprise Document Platform

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

</div>

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

For questions or support, open an issue on [GitHub](https://github.com/Rrensisorathiya/DocForgeHub) or reach out to the project maintainer. -->