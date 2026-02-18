# Rensi — AI-Powered Document Generator

An intelligent document generation system built with **LangChain**, **LangGraph**, and **Azure OpenAI** that automates the creation of structured, department-specific documents from questionnaire inputs.

---

## 🚀 Features

- **Template-based document generation** — Fetches templates by document type and renders structured sections automatically
- **Questionnaire-driven input** — Collects structured data via questionnaires to populate documents
- **LangChain + LangGraph integration** — Uses LLM pipelines and graph-based workflows for intelligent content generation
- **Azure OpenAI backend** — Powered by Azure-hosted language models
- **Modular service architecture** — Clean separation of concerns across repositories, builders, and service layers

---

## 📁 Project Structure

```
Rensi/
├── api/
│   ├── documents.py          # Document API endpoints
│   ├── metadata.py           # Metadata API endpoints
│   ├── questionnaires.py     # Questionnaire API endpoints
│   ├── system.py             # System API endpoints
│   └── templates.py          # Template API endpoints
├── migrations/
│   └── migrate_json_to_db.py # Database migration scripts
├── Schema/
│   ├── content.json          # Content schema definitions
│   ├── metadata.json         # Metadata schema
│   ├── Question_Answer.json  # Q&A schema
│   ├── random.json           # Random data schema
│   └── schemas/              # Additional schemas
├── services/
│   ├── azure_client.py       # Azure OpenAI client setup
│   ├── document_generator.py # Core document generation logic
│   ├── document_repository.py# Document storage & retrieval
│   ├── langchain_service.py  # LangChain LLM service
│   ├── prompt_builder.py     # Prompt construction utilities
│   ├── questionnaire_repo.py # Questionnaire data access
│   └── template_repository.py# Template storage & retrieval
├── main.py                   # Application entry point
├── demo.py                   # Demo / quick test script
├── db.py                     # Database connection & setup
├── requirements.txt          # Python dependencies
└── .env                      # Environment variables (not committed)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM Framework | LangChain, LangGraph |
| LLM Provider | Azure OpenAI |
| API Layer | FastAPI (or Flask) |
| Database | SQLite / PostgreSQL (via `db.py`) |
| Environment | Python `venv` |

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.10 or higher
- Node.js (optional, for frontend tooling)
- Azure OpenAI API access

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Rensi
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-01
DATABASE_URL=sqlite:///./db.sqlite3
```

### 5. Run Database Migrations

```bash
python migrations/migrate_json_to_db.py
```

### 6. Start the Application

```bash
python main.py
```

---

## 📄 How Document Generation Works

1. **Fetch Template** — Retrieves the document template matching the requested `document_type`
2. **Fetch Questionnaire** — Loads the corresponding questionnaire for the document type
3. **Extract Sections** — Parses the template structure to identify required sections
4. **Generate Content** — Uses LangChain + Azure OpenAI to populate each section based on questionnaire answers
5. **Assemble Document** — Combines generated sections into a final formatted document

```python
# Core flow in document_generator.py
template = get_template_by_type(document_type)
questionnaire = get_questionnaire_by_type(document_type)
sections = extract_sections(template["structure"])
# ... LLM-powered content generation per section
```

---

## 🧪 Testing

```bash
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
python-dotenv
```

Install all at once:

```bash
pip install -r requirements.txt
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## 📬 Contact

For questions or support, reach out to the project maintainer or open an issue on GitHub.