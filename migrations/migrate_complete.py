"""
Complete Database Migration for DocForgeHub
Run: python3 migrations/migrate_complete.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection
from utils.logger import setup_logger

logger = setup_logger(__name__)


def run_migrations():
    conn = get_connection()
    cursor = conn.cursor()

    print("Starting migrations...")

    # ─────────────────────────────────────────
    # 1. DEPARTMENTS
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id        SERIAL PRIMARY KEY,
            name      VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ departments")

    # ─────────────────────────────────────────
    # 2. DOCUMENT TYPES
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_types (
            id        SERIAL PRIMARY KEY,
            name      VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ document_types")

    # ─────────────────────────────────────────
    # 3. TEMPLATES  (department + doc_type + sections)
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id              SERIAL PRIMARY KEY,
            department      VARCHAR(255) NOT NULL,
            document_type   VARCHAR(255) NOT NULL,
            structure       JSONB        NOT NULL,
            version         VARCHAR(20)  DEFAULT '1.0',
            is_active       BOOLEAN      DEFAULT TRUE,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (department, document_type)
        );
    """)
    print("✅ templates")

    # ─────────────────────────────────────────
    # 4. QUESTIONNAIRES
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questionnaires (
            id              SERIAL PRIMARY KEY,
            document_type   VARCHAR(255) NOT NULL,
            department      VARCHAR(255) NOT NULL,
            questions       JSONB        NOT NULL,
            version         VARCHAR(20)  DEFAULT '1.0',
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (department, document_type)
        );
    """)
    print("✅ questionnaires")

    # ─────────────────────────────────────────
    # 5. DOCUMENT METADATA  (from metadata.json)
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_metadata (
            id                  SERIAL PRIMARY KEY,
            document_id         VARCHAR(255),          -- links to generated_documents
            title               VARCHAR(200),
            document_type       VARCHAR(255),
            department          VARCHAR(255),
            industry            VARCHAR(100) DEFAULT 'SaaS',
            version             VARCHAR(20)  DEFAULT '1.0',
            status              VARCHAR(50)  DEFAULT 'Draft',
            created_by          VARCHAR(100) DEFAULT 'AI Document Generator',
            reviewer            VARCHAR(100),
            approved_by         VARCHAR(100),
            approval_date       DATE,
            effective_date      DATE,
            expiry_date         DATE,
            review_frequency    VARCHAR(50),
            tags                JSONB,
            compliance_tags     JSONB,
            audience            JSONB,
            priority            VARCHAR(20)  DEFAULT 'Medium',
            confidentiality     VARCHAR(50)  DEFAULT 'Internal',
            word_count          INTEGER,
            reading_time        INTEGER,
            source_prompt       TEXT,
            template_id         INTEGER REFERENCES templates(id),
            related_documents   JSONB,
            doc_specific_meta   JSONB,
            created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ document_metadata")

    # ─────────────────────────────────────────
    # 6. GENERATED DOCUMENTS  (final AI output)
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_documents (
            id                  SERIAL PRIMARY KEY,
            job_id              VARCHAR(255) UNIQUE,   -- Redis job ID
            document_type       VARCHAR(255) NOT NULL,
            department          VARCHAR(255) NOT NULL,
            industry            VARCHAR(100) DEFAULT 'SaaS',
            question_answers    JSONB,
            generated_content   TEXT,
            status              VARCHAR(50)  DEFAULT 'completed',
            error_message       TEXT,
            template_id         INTEGER REFERENCES templates(id),
            metadata_id         INTEGER REFERENCES document_metadata(id),
            created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ generated_documents")

    # ─────────────────────────────────────────
    # 7. GENERATION JOBS  (Redis job tracking)
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_jobs (
            id              SERIAL PRIMARY KEY,
            job_id          VARCHAR(255) NOT NULL UNIQUE,
            status          VARCHAR(50)  DEFAULT 'pending',
            document_type   VARCHAR(255),
            department      VARCHAR(255),
            industry        VARCHAR(100),
            question_answers JSONB,
            result_doc_id   INTEGER REFERENCES generated_documents(id),
            error_message   TEXT,
            started_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            completed_at    TIMESTAMP,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ generation_jobs")

    # ─────────────────────────────────────────
    # 8. DOCUMENT VERSIONS  (version history)
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_versions (
            id              SERIAL PRIMARY KEY,
            document_id     INTEGER REFERENCES generated_documents(id),
            version         VARCHAR(20) NOT NULL,
            content         TEXT,
            changed_by      VARCHAR(100),
            change_notes    TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ document_versions")

    # ─────────────────────────────────────────
    # 9. QUESTION ANSWERS LOG  (from Question_Answer.json)
    # ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS question_answer_logs (
            id              SERIAL PRIMARY KEY,
            job_id          VARCHAR(255),
            document_type   VARCHAR(255),
            department      VARCHAR(255),
            company_name    VARCHAR(255),
            company_size    VARCHAR(100),
            primary_product TEXT,
            target_market   VARCHAR(50),
            tools_used      JSONB,
            compliance_reqs JSONB,
            geo_locations   VARCHAR(255),
            tone_preference VARCHAR(100),
            specific_focus  TEXT,
            extra_answers   JSONB,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ question_answer_logs")

    # ─────────────────────────────────────────
    # SEED: Departments
    # ─────────────────────────────────────────
    departments = [
        "HR & People Operations",
        "Legal & Compliance",
        "Sales & Customer-Facing",
        "Engineering & Operations",
        "Product & Design",
        "Marketing & Content",
        "Finance & Operations",
        "Partnership & Alliances",
        "IT & Internal Systems",
        "Platform & Infrastructure Operation",
        "Data & Analytics",
        "QA & Testing",
        "Security & Information Assurance",
    ]
    for dept in departments:
        cursor.execute("""
            INSERT INTO departments (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
        """, (dept,))
    print("✅ departments seeded")

    # ─────────────────────────────────────────
    # SEED: Document Types
    # ─────────────────────────────────────────
    doc_types = [
        "SOP", "Policy", "Proposal", "SOW", "Incident Report",
        "FAQ", "Runbook", "Playbook", "RCA", "SLA",
        "Change Management", "Handbook",
    ]
    for dt in doc_types:
        cursor.execute("""
            INSERT INTO document_types (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
        """, (dt,))
    print("✅ document_types seeded")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n✅ All migrations completed successfully!")
    print("\n📋 Tables created:")
    print("   departments           — all 13 departments")
    print("   document_types        — SOP, Policy, Proposal, etc.")
    print("   templates             — structure/sections per dept+type")
    print("   questionnaires        — questions per dept+type")
    print("   document_metadata     — full metadata from metadata.json")
    print("   generated_documents   — AI generated content + job_id")
    print("   generation_jobs       — Redis job tracking table")
    print("   document_versions     — version history")
    print("   question_answer_logs  — user Q&A input log")


if __name__ == "__main__":
    run_migrations()