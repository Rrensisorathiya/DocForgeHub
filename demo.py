import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
from typing import List, Dict, Optional
import requests

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="DocuGen Pro - AI Document Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS FOR PROFESSIONAL DESIGN
# ============================================
def load_custom_css():
    st.markdown("""
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global Styles */
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Main Container */
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        }
        
        [data-testid="stSidebar"] .css-1d391kg {
            color: white;
        }
        
        /* Card Styling */
        .custom-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            border-left: 5px solid #4CAF50;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .custom-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
        }
        
        /* Document Card */
        .doc-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            margin-bottom: 15px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        .doc-card:hover {
            border-color: #4CAF50;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }
        
        /* Header Styles */
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e3c72;
            margin-bottom: 10px;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        .sub-header {
            font-size: 1.8rem;
            font-weight: 600;
            color: #2a5298;
            margin-top: 30px;
            margin-bottom: 20px;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        
        /* Stat Box */
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Success Box */
        .success-box {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            text-align: center;
            font-weight: 600;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        }
        
        /* Warning Box */
        .warning-box {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            text-align: center;
            font-weight: 600;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        }
        
        /* Info Box */
        .info-box {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        }
        
        /* Button Styling */
        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 30px;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
        }
        
        /* Progress Bar */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Tag Styling */
        .tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-right: 8px;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        /* Document Type Badge */
        .doc-type-badge {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }
        
        /* Status Badge */
        .status-published {
            background: #4CAF50;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .status-draft {
            background: #FF9800;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        /* Divider */
        .custom-divider {
            height: 3px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border: none;
            margin: 30px 0;
            border-radius: 5px;
        }
        
        /* Input Field Styling */
        .stTextInput>div>div>input {
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            padding: 10px;
            transition: border-color 0.3s ease;
        }
        
        .stTextInput>div>div>input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }
        
        /* Select Box Styling */
        .stSelectbox>div>div>select {
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }
        
        /* Metric Card */
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
            border-top: 4px solid #4CAF50;
        }
        
        /* Sidebar Navigation */
        .nav-item {
            padding: 12px 20px;
            margin: 8px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
        }
        
        .nav-item:hover {
            background: rgba(255, 255, 255, 0.1);
            padding-left: 25px;
        }
        
        .nav-item-active {
            background: rgba(255, 255, 255, 0.2);
            border-left: 4px solid #4CAF50;
        }
        
        /* Loading Animation */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        </style>
    """, unsafe_allow_html=True)

# ============================================
# MOCK DATA & CONFIGURATION
# ============================================

INDUSTRIES = ["SaaS", "E-commerce", "FinTech", "Healthcare"]

DEPARTMENTS = {
    "SaaS": [
        "HR & People Operations",
        "Legal & Compliance",
        "Sales & Customer Facing",
        "Engineering & Operations",
        "Product & Design",
        "Marketing & Content",
        "Finance & Operations",
        "Partnership & Alliances",
        "IT & Internal Systems",
        "Platform & Infrastructure Operations",
        "Data & Analytics",
        "QA & Testing",
        "Security & Information Assurance"
    ]
}

DOCUMENT_TYPES = [
    "SOP", "Policy", "Proposal", "SOW", "Incident Report",
    "FAQ", "Runbook", "Playbook", "RCA", "SLA",
    "Change Management Document"
]

# Sample questions based on document type
QUESTIONS = {
    "SOP": [
        {"id": "q1", "text": "What is the name of this procedure?", "type": "text", "required": True},
        {"id": "q2", "text": "Who are the primary stakeholders?", "type": "multiselect", "options": ["HR Team", "Managers", "All Employees", "IT Department"], "required": True},
        {"id": "q3", "text": "What compliance frameworks apply?", "type": "multiselect", "options": ["GDPR", "SOC2", "ISO 27001", "HIPAA", "None"], "required": False},
        {"id": "q4", "text": "Describe the main objective", "type": "textarea", "required": True},
    ],
    "Policy": [
        {"id": "q1", "text": "Policy Title", "type": "text", "required": True},
        {"id": "q2", "text": "Policy Scope", "type": "multiselect", "options": ["Company-wide", "Department-specific", "Role-specific"], "required": True},
        {"id": "q3", "text": "Effective Date", "type": "date", "required": True},
        {"id": "q4", "text": "Policy Owner", "type": "text", "required": True},
    ],
    "Proposal": [
        {"id": "q1", "text": "Project/Proposal Name", "type": "text", "required": True},
        {"id": "q2", "text": "Target Client/Stakeholder", "type": "text", "required": True},
        {"id": "q3", "text": "Budget Range", "type": "select", "options": ["< $10K", "$10K - $50K", "$50K - $100K", "> $100K"], "required": True},
        {"id": "q4", "text": "Project Timeline", "type": "select", "options": ["1-3 months", "3-6 months", "6-12 months", "> 12 months"], "required": True},
    ]
}

# Initialize session state
if 'generated_documents' not in st.session_state:
    st.session_state.generated_documents = []

if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"

# ============================================
# HELPER FUNCTIONS
# ============================================

def render_stat_box(number: str, label: str):
    """Render a statistics box"""
    return f"""
    <div class="stat-box">
        <div class="stat-number">{number}</div>
        <div class="stat-label">{label}</div>
    </div>
    """

def render_card(title: str, content: str, border_color: str = "#4CAF50"):
    """Render a custom card"""
    return f"""
    <div class="custom-card" style="border-left-color: {border_color}">
        <h3 style="color: #1e3c72; margin-bottom: 15px;">{title}</h3>
        <p style="color: #555; line-height: 1.6;">{content}</p>
    </div>
    """

def generate_mock_document(industry: str, department: str, doc_type: str, answers: Dict) -> Dict:
    """Generate a mock document (replace with actual LangChain generation)"""
    doc = {
        "id": f"DOC-{len(st.session_state.generated_documents) + 1:04d}",
        "title": answers.get("q1", f"{doc_type} Document"),
        "type": doc_type,
        "industry": industry,
        "department": department,
        "content": f"# {answers.get('q1', doc_type)}\n\n## Generated Content\n\nThis is a professionally generated {doc_type} document for {department} in the {industry} industry.\n\n**Key Details:**\n" + "\n".join([f"- {k}: {v}" for k, v in answers.items()]),
        "version": "1.0",
        "tags": ["auto-generated", doc_type.lower(), department.lower()],
        "created_by": "AI DocuGen Pro",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_published": False,
        "notion_page_id": None
    }
    return doc

# ============================================
# SIDEBAR NAVIGATION
# ============================================

def render_sidebar():
    """Render sidebar navigation"""
    with st.sidebar:
        st.markdown("<h1 style='color: white; text-align: center; margin-bottom: 30px;'>📄 DocuGen Pro</h1>", unsafe_allow_html=True)
        st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.3); margin-bottom: 20px;'>", unsafe_allow_html=True)
        
        # Navigation buttons
        pages = {
            "🏠 Home": "Home",
            "✨ Generate Document": "Generate",
            "📚 Document Library": "Library",
            "🚀 Publish to Notion": "Publish"
        }
        
        for icon_label, page_key in pages.items():
            if st.button(icon_label, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.current_page = page_key
        
        st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.3); margin: 30px 0;'>", unsafe_allow_html=True)
        
        # Statistics in sidebar
        st.markdown("<h3 style='color: white;'>📊 Quick Stats</h3>", unsafe_allow_html=True)
        st.metric("Total Documents", len(st.session_state.generated_documents), delta=None)
        published = sum(1 for doc in st.session_state.generated_documents if doc.get('is_published', False))
        st.metric("Published to Notion", published, delta=None)
        
        st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.3); margin: 30px 0;'>", unsafe_allow_html=True)
        
        # Footer
        st.markdown("""
            <div style='color: rgba(255,255,255,0.7); text-align: center; font-size: 0.8rem; margin-top: 50px;'>
                <p>Powered by AI</p>
                <p>© 2026 DocuGen Pro</p>
            </div>
        """, unsafe_allow_html=True)

# ============================================
# PAGE: HOME
# ============================================

def render_home_page():
    """Render home page"""
    st.markdown("<h1 class='main-header'>🚀 Welcome to DocuGen Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #555; margin-bottom: 40px;'>AI-Powered Enterprise Document Generation System</p>", unsafe_allow_html=True)
    
    # Stats Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(render_stat_box(f"{len(st.session_state.generated_documents)}", "Documents"), unsafe_allow_html=True)
    
    with col2:
        published = sum(1 for doc in st.session_state.generated_documents if doc.get('is_published', False))
        st.markdown(render_stat_box(f"{published}", "Published"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_stat_box("13", "Departments"), unsafe_allow_html=True)
    
    with col4:
        st.markdown(render_stat_box("11", "Doc Types"), unsafe_allow_html=True)
    
    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
    # Feature Cards
    st.markdown("<h2 class='sub-header'>✨ Key Features</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(render_card(
            "🤖 AI-Powered Generation",
            "Leverage advanced LLM models to generate professional, industry-ready documents in seconds.",
            "#667eea"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_card(
            "📋 Smart Templates",
            "Dynamic question-based workflows ensure every document meets compliance and quality standards.",
            "#764ba2"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_card(
            "🔗 Notion Integration",
            "Seamlessly publish documents to Notion with structured metadata and version control.",
            "#4CAF50"
        ), unsafe_allow_html=True)
    
    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown("<h2 class='sub-header'>🎯 Quick Actions</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🆕 Create New Document", key="home_create", use_container_width=True):
            st.session_state.current_page = "Generate"
            st.rerun()
    
    with col2:
        if st.button("📚 Browse Library", key="home_browse", use_container_width=True):
            st.session_state.current_page = "Library"
            st.rerun()
    
    # Recent Activity
    if st.session_state.generated_documents:
        st.markdown("<h2 class='sub-header'>🕐 Recent Documents</h2>", unsafe_allow_html=True)
        
        recent_docs = sorted(st.session_state.generated_documents, 
                           key=lambda x: x['created_at'], reverse=True)[:3]
        
        for doc in recent_docs:
            status_badge = "status-published" if doc.get('is_published') else "status-draft"
            status_text = "Published" if doc.get('is_published') else "Draft"
            
            st.markdown(f"""
            <div class="doc-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
                        <p style="margin: 5px 0; color: #666;">
                            <span class="doc-type-badge">{doc['type']}</span>
                            <span style="margin-left: 10px; color: #999;">📅 {doc['created_at']}</span>
                        </p>
                    </div>
                    <span class="{status_badge}">{status_text}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# PAGE: GENERATE DOCUMENT
# ============================================

def render_generate_page():
    """Render document generation page"""
    st.markdown("<h1 class='main-header'>✨ Generate New Document</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 30px;'>Follow the wizard to create professional documents</p>", unsafe_allow_html=True)
    
    # Progress tracker
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = 1
    
    # Progress bar
    progress = (st.session_state.generation_step - 1) / 3
    st.progress(progress)
    
    steps = ["📋 Select Type", "❓ Answer Questions", "🎉 Generate & Review"]
    cols = st.columns(3)
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if idx + 1 < st.session_state.generation_step:
                st.markdown(f"<p style='text-align: center; color: #4CAF50; font-weight: 600;'>✅ {step}</p>", unsafe_allow_html=True)
            elif idx + 1 == st.session_state.generation_step:
                st.markdown(f"<p style='text-align: center; color: #667eea; font-weight: 600;'>▶️ {step}</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p style='text-align: center; color: #999;'>⏺️ {step}</p>", unsafe_allow_html=True)
    
    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
    # STEP 1: Select Document Type
    if st.session_state.generation_step == 1:
        st.markdown("<h2 class='sub-header'>Step 1: Select Document Type</h2>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            industry = st.selectbox("🏢 Industry", INDUSTRIES, key="gen_industry")
        
        with col2:
            department = st.selectbox("🏛️ Department", DEPARTMENTS.get(industry, []), key="gen_department")
        
        with col3:
            doc_type = st.selectbox("📄 Document Type", DOCUMENT_TYPES, key="gen_doc_type")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("➡️ Next: Answer Questions", use_container_width=True):
            st.session_state.selected_industry = industry
            st.session_state.selected_department = department
            st.session_state.selected_doc_type = doc_type
            st.session_state.generation_step = 2
            st.rerun()
    
    # STEP 2: Answer Questions
    elif st.session_state.generation_step == 2:
        st.markdown("<h2 class='sub-header'>Step 2: Answer Questions</h2>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="info-box">
            <strong>Generating:</strong> {st.session_state.selected_doc_type} for {st.session_state.selected_department} in {st.session_state.selected_industry}
        </div>
        """, unsafe_allow_html=True)
        
        questions = QUESTIONS.get(st.session_state.selected_doc_type, QUESTIONS["SOP"])
        answers = {}
        
        for question in questions:
            st.markdown(f"<p style='font-weight: 600; color: #1e3c72; margin-top: 20px;'>{question['text']} {'*' if question['required'] else ''}</p>", unsafe_allow_html=True)
            
            if question['type'] == 'text':
                answers[question['id']] = st.text_input("", key=f"answer_{question['id']}", label_visibility="collapsed")
            
            elif question['type'] == 'textarea':
                answers[question['id']] = st.text_area("", key=f"answer_{question['id']}", height=120, label_visibility="collapsed")
            
            elif question['type'] == 'select':
                answers[question['id']] = st.selectbox("", question['options'], key=f"answer_{question['id']}", label_visibility="collapsed")
            
            elif question['type'] == 'multiselect':
                answers[question['id']] = st.multiselect("", question['options'], key=f"answer_{question['id']}", label_visibility="collapsed")
            
            elif question['type'] == 'date':
                answers[question['id']] = st.date_input("", key=f"answer_{question['id']}", label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.generation_step = 1
                st.rerun()
        
        with col2:
            if st.button("➡️ Generate Document", use_container_width=True):
                # Validate required fields
                all_valid = True
                for question in questions:
                    if question['required'] and not answers.get(question['id']):
                        all_valid = False
                        st.error(f"Please answer: {question['text']}")
                
                if all_valid:
                    st.session_state.current_answers = answers
                    st.session_state.generation_step = 3
                    st.rerun()
    
    # STEP 3: Generate & Review
    elif st.session_state.generation_step == 3:
        st.markdown("<h2 class='sub-header'>Step 3: Generating Document...</h2>", unsafe_allow_html=True)
        
        # Simulate generation with progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps_simulation = [
            ("Analyzing requirements...", 0.2),
            ("Loading AI model...", 0.4),
            ("Generating content...", 0.6),
            ("Applying formatting...", 0.8),
            ("Finalizing document...", 1.0),
        ]
        
        for step_text, progress_value in steps_simulation:
            status_text.markdown(f"<p style='text-align: center; color: #667eea; font-weight: 600;'>{step_text}</p>", unsafe_allow_html=True)
            progress_bar.progress(progress_value)
            time.sleep(0.5)
        
        # Generate document
        document = generate_mock_document(
            st.session_state.selected_industry,
            st.session_state.selected_department,
            st.session_state.selected_doc_type,
            st.session_state.current_answers
        )
        
        st.session_state.generated_documents.append(document)
        
        status_text.empty()
        progress_bar.empty()
        
        st.markdown(f"""
        <div class="success-box">
            ✅ Document Generated Successfully! ID: {document['id']}
        </div>
        """, unsafe_allow_html=True)
        
        # Display document preview
        st.markdown("<h3 style='color: #1e3c72; margin-top: 30px;'>📄 Document Preview</h3>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="doc-card">
            <h2 style="color: #1e3c72;">{document['title']}</h2>
            <p><span class="doc-type-badge">{document['type']}</span></p>
            <p style="color: #666; margin-top: 15px;"><strong>Industry:</strong> {document['industry']}</p>
            <p style="color: #666;"><strong>Department:</strong> {document['department']}</p>
            <p style="color: #666;"><strong>Version:</strong> {document['version']}</p>
            <p style="color: #666;"><strong>Created:</strong> {document['created_at']}</p>
            <div style="margin-top: 20px;">
                <strong>Tags:</strong><br>
                {''.join([f'<span class="tag">{tag}</span>' for tag in document['tags']])}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📖 View Full Content"):
            st.markdown(document['content'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Generate Another", use_container_width=True):
                st.session_state.generation_step = 1
                st.rerun()
        
        with col2:
            if st.button("📚 Go to Library", use_container_width=True):
                st.session_state.current_page = "Library"
                st.session_state.generation_step = 1
                st.rerun()

# ============================================
# PAGE: DOCUMENT LIBRARY
# ============================================

def render_library_page():
    """Render document library page"""
    st.markdown("<h1 class='main-header'>📚 Document Library</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 30px;'>Browse and manage all generated documents</p>", unsafe_allow_html=True)
    
    if not st.session_state.generated_documents:
        st.markdown("""
        <div class="info-box">
            <h3>📭 No Documents Yet</h3>
            <p>Start by generating your first document!</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("✨ Generate First Document", use_container_width=True):
            st.session_state.current_page = "Generate"
            st.rerun()
        return
    
    # Filters
    st.markdown("<h3 style='color: #1e3c72;'>🔍 Filters</h3>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_type = st.multiselect("Document Type", 
                                     options=list(set([doc['type'] for doc in st.session_state.generated_documents])),
                                     default=[])
    
    with col2:
        filter_industry = st.multiselect("Industry",
                                        options=list(set([doc['industry'] for doc in st.session_state.generated_documents])),
                                        default=[])
    
    with col3:
        filter_status = st.selectbox("Status", ["All", "Published", "Draft"])
    
    with col4:
        search_term = st.text_input("🔎 Search", placeholder="Search by title...")
    
    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
    # Filter documents
    filtered_docs = st.session_state.generated_documents
    
    if filter_type:
        filtered_docs = [doc for doc in filtered_docs if doc['type'] in filter_type]
    
    if filter_industry:
        filtered_docs = [doc for doc in filtered_docs if doc['industry'] in filter_industry]
    
    if filter_status == "Published":
        filtered_docs = [doc for doc in filtered_docs if doc.get('is_published', False)]
    elif filter_status == "Draft":
        filtered_docs = [doc for doc in filtered_docs if not doc.get('is_published', False)]
    
    if search_term:
        filtered_docs = [doc for doc in filtered_docs if search_term.lower() in doc['title'].lower()]
    
    # Display count
    st.markdown(f"<p style='color: #666; font-size: 1.1rem;'>Showing <strong>{len(filtered_docs)}</strong> of <strong>{len(st.session_state.generated_documents)}</strong> documents</p>", unsafe_allow_html=True)
    
    # Display documents
    for idx, doc in enumerate(filtered_docs):
        status_badge = "status-published" if doc.get('is_published') else "status-draft"
        status_text = "Published" if doc.get('is_published') else "Draft"
        
        with st.container():
            st.markdown(f"""
            <div class="doc-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
                        <p style="margin: 10px 0; color: #666;">
                            <span class="doc-type-badge">{doc['type']}</span>
                            <span style="margin-left: 10px;">🏢 {doc['industry']}</span>
                            <span style="margin-left: 10px;">🏛️ {doc['department']}</span>
                        </p>
                        <p style="margin: 5px 0; color: #999; font-size: 0.9rem;">
                            📅 {doc['created_at']} • 👤 {doc['created_by']} • 📌 v{doc['version']}
                        </p>
                        <div style="margin-top: 10px;">
                            {''.join([f'<span class="tag">{tag}</span>' for tag in doc['tags']])}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="{status_badge}">{status_text}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if st.button("📖 View Details", key=f"view_{idx}", use_container_width=True):
                    st.session_state.selected_doc_for_view = doc
                    st.session_state.show_doc_modal = True
            
            with col2:
                if not doc.get('is_published'):
                    if st.button("🚀 Publish", key=f"publish_{idx}", use_container_width=True):
                        doc['is_published'] = True
                        doc['notion_page_id'] = f"NOTION-{doc['id']}"
                        st.success(f"✅ Published to Notion!")
                        time.sleep(1)
                        st.rerun()
            
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{idx}", use_container_width=True):
                    st.session_state.generated_documents.remove(doc)
                    st.success("Document deleted!")
                    time.sleep(1)
                    st.rerun()
    
    # Document detail modal
    if st.session_state.get('show_doc_modal', False):
        doc = st.session_state.selected_doc_for_view
        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #1e3c72;'>📄 Document Details</h2>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="doc-card">
            <h2 style="color: #1e3c72;">{doc['title']}</h2>
            <p><span class="doc-type-badge">{doc['type']}</span></p>
            <hr>
            <p><strong>Industry:</strong> {doc['industry']}</p>
            <p><strong>Department:</strong> {doc['department']}</p>
            <p><strong>Version:</strong> {doc['version']}</p>
            <p><strong>Created By:</strong> {doc['created_by']}</p>
            <p><strong>Created At:</strong> {doc['created_at']}</p>
            <p><strong>Status:</strong> {'Published ✅' if doc.get('is_published') else 'Draft 📝'}</p>
            {f"<p><strong>Notion Page ID:</strong> {doc['notion_page_id']}</p>" if doc.get('notion_page_id') else ''}
            <div style="margin-top: 20px;">
                <strong>Tags:</strong><br>
                {''.join([f'<span class="tag">{tag}</span>' for tag in doc['tags']])}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h3 style='color: #1e3c72; margin-top: 20px;'>📝 Content</h3>", unsafe_allow_html=True)
        st.markdown(doc['content'])
        
        if st.button("✖️ Close", use_container_width=True):
            st.session_state.show_doc_modal = False
            st.rerun()

# ============================================
# PAGE: PUBLISH TO NOTION
# ============================================

def render_publish_page():
    """Render Notion publishing page"""
    st.markdown("<h1 class='main-header'>🚀 Publish to Notion</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #555; margin-bottom: 30px;'>Manage document publishing to Notion workspace</p>", unsafe_allow_html=True)
    
    # Unpublished documents
    unpublished = [doc for doc in st.session_state.generated_documents if not doc.get('is_published', False)]
    published = [doc for doc in st.session_state.generated_documents if doc.get('is_published', False)]
    
    # Stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(render_stat_box(f"{len(st.session_state.generated_documents)}", "Total Docs"), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_stat_box(f"{len(unpublished)}", "Ready to Publish"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_stat_box(f"{len(published)}", "Published"), unsafe_allow_html=True)
    
    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
    # Bulk publish
    if unpublished:
        st.markdown("<h2 class='sub-header'>📤 Ready to Publish</h2>", unsafe_allow_html=True)
        
        if st.button("🚀 Publish All to Notion", use_container_width=True):
            progress_bar = st.progress(0)
            status = st.empty()
            
            for idx, doc in enumerate(unpublished):
                status.markdown(f"<p style='text-align: center; color: #667eea;'>Publishing: {doc['title']}...</p>", unsafe_allow_html=True)
                time.sleep(0.3)  # Simulate API call
                doc['is_published'] = True
                doc['notion_page_id'] = f"NOTION-{doc['id']}"
                progress_bar.progress((idx + 1) / len(unpublished))
            
            st.markdown("""
            <div class="success-box">
                🎉 All documents published successfully!
            </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Individual publish
        for idx, doc in enumerate(unpublished):
            st.markdown(f"""
            <div class="doc-card">
                <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <span class="doc-type-badge">{doc['type']}</span>
                    <span style="margin-left: 10px;">📅 {doc['created_at']}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"🚀 Publish '{doc['title']}'", key=f"pub_{idx}", use_container_width=True):
                with st.spinner(f"Publishing {doc['title']}..."):
                    time.sleep(1)
                    doc['is_published'] = True
                    doc['notion_page_id'] = f"NOTION-{doc['id']}"
                st.success("✅ Published!")
                time.sleep(1)
                st.rerun()
    else:
        st.markdown("""
        <div class="info-box">
            <h3>✅ All Caught Up!</h3>
            <p>No documents waiting to be published.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Published documents
    if published:
        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
        st.markdown("<h2 class='sub-header'>✅ Published Documents</h2>", unsafe_allow_html=True)
        
        for doc in published:
            st.markdown(f"""
            <div class="doc-card">
                <h3 style="margin: 0; color: #1e3c72;">{doc['title']}</h3>
                <p style="margin: 5px 0; color: #666;">
                    <span class="status-published">Published</span>
                    <span style="margin-left: 10px;">🔗 Notion ID: {doc['notion_page_id']}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# MAIN APP
# ============================================

def main():
    """Main application"""
    load_custom_css()
    render_sidebar()
    
    # Route to pages
    if st.session_state.current_page == "Home":
        render_home_page()
    elif st.session_state.current_page == "Generate":
        render_generate_page()
    elif st.session_state.current_page == "Library":
        render_library_page()
    elif st.session_state.current_page == "Publish":
        render_publish_page()

if __name__ == "__main__":
    main()

    
