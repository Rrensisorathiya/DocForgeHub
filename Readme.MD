# DocForgeHub — AI-Powered Document Generator

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

## 📄 Supported Document Types (123 Templates)

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

For questions or support, open an issue on [GitHub](https://github.com/Rrensisorathiya/DocForgeHub) or reach out to the project maintainer.