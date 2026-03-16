"""
Document Validator
- Checks generated document for format, quality, completeness
- Returns validation report with score and issues
- Used after generation before saving to DB
"""
import re
from typing import Dict, List, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================
# REQUIRED SECTIONS PER DOC TYPE
# ============================================================
REQUIRED_SECTIONS = {
    "SOP": [
        "purpose", "scope", "roles", "procedure", "tools", "compliance", "review", "approval"
    ],
    "Policy": [
        "purpose", "scope", "policy statement", "roles", "compliance", "enforcement", "review", "approval"
    ],
    "Proposal": [
        "executive summary", "background", "objective", "solution", "timeline", "budget", "risk", "approval"
    ],
    "SOW": [
        "purpose", "scope", "deliverable", "timeline", "roles", "budget", "acceptance", "approval"
    ],
    "Incident Report": [
        "incident", "date", "description", "impact", "root cause", "resolution", "lessons", "approval"
    ],
    "FAQ": [
        "purpose", "scope", "frequently asked", "question", "answer", "review"
    ],
    "Runbook": [
        "purpose", "scope", "prerequisite", "step", "troubleshoot", "escalation", "review"
    ],
    "Playbook": [
        "purpose", "scope", "roles", "procedure", "scenario", "kpi", "review", "approval"
    ],
    "RCA": [
        "incident", "description", "impact", "root cause", "corrective", "preventive", "lessons", "approval"
    ],
    "SLA": [
        "purpose", "scope", "parties", "service", "metric", "escalation", "penalty", "review", "approval"
    ],
    "Change Management": [
        "purpose", "scope", "change request", "impact", "roles", "approval", "testing", "review"
    ],
    "Handbook": [
        "welcome", "overview", "policy", "procedure", "compliance", "acknowledgment"
    ],
}

# Minimum word counts per doc type
MIN_WORD_COUNTS = {
    "SOP": 1500,
    "Policy": 1200,
    "Proposal": 1500,
    "SOW": 1200,
    "Incident Report": 800,
    "FAQ": 1000,
    "Runbook": 1200,
    "Playbook": 1500,
    "RCA": 1000,
    "SLA": 1000,
    "Change Management": 1200,
    "Handbook": 2000,
}

# Placeholder patterns that should NOT appear in generated docs
PLACEHOLDER_PATTERNS = [
    r"\[insert.*?\]",
    r"\[your.*?\]",
    r"\[company name\]",
    r"\[department\]",
    r"\[date\]",
    r"\[tbd\]",
    r"\[add.*?\]",
    r"\[specify.*?\]",
    r"\[enter.*?\]",
    r"\[fill.*?\]",
    r"lorem ipsum",
    r"placeholder",
    r"xxx+",
    r"n/a\s*\(not provided\)",
]


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

def check_word_count(content: str, doc_type: str) -> Tuple[bool, int, int]:
    """Check if document meets minimum word count."""
    word_count = len(content.split())
    min_count  = MIN_WORD_COUNTS.get(doc_type, 800)
    return word_count >= min_count, word_count, min_count


def check_sections_present(content: str, doc_type: str) -> Tuple[bool, List[str], List[str]]:
    """Check if required sections are present."""
    content_lower = content.lower()
    required      = REQUIRED_SECTIONS.get(doc_type, [])
    present       = [s for s in required if s in content_lower]
    missing       = [s for s in required if s not in content_lower]
    ok            = len(missing) == 0
    return ok, present, missing


def check_markdown_structure(content: str) -> Tuple[bool, List[str]]:
    """Check if document has proper markdown headings."""
    issues = []
    h2_sections = re.findall(r"^##\s+.+", content, re.MULTILINE)
    h3_sections = re.findall(r"^###\s+.+", content, re.MULTILINE)

    if len(h2_sections) < 3:
        issues.append(f"Only {len(h2_sections)} main sections (##) found — expected at least 3")

    if len(h3_sections) < 2:
        issues.append(f"Only {len(h3_sections)} subsections (###) found — expected at least 2")

    return len(issues) == 0, issues


def check_placeholders(content: str) -> Tuple[bool, List[str]]:
    """Check for unfilled placeholder text."""
    content_lower = content.lower()
    found = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, content_lower)
        if matches:
            found.extend(matches[:3])  # max 3 examples per pattern
    return len(found) == 0, found


def check_company_name(content: str, company_name: str) -> Tuple[bool, int]:
    """Check if company name is used in document."""
    if company_name in ("the company", "", "testco"):
        return True, 0
    count = content.lower().count(company_name.lower())
    return count >= 3, count


def check_has_tables(content: str, doc_type: str) -> Tuple[bool, int]:
    """Check if document has tables where expected."""
    table_count = len(re.findall(r"^\|.+\|", content, re.MULTILINE))
    doc_types_needing_tables = {"SOP", "SLA", "Change Management", "SOW", "RCA", "Proposal"}

    if doc_type in doc_types_needing_tables:
        return table_count >= 1, table_count
    return True, table_count  # optional for other types


def check_has_numbered_lists(content: str, doc_type: str) -> Tuple[bool, int]:
    """Check if procedural docs have numbered steps."""
    numbered = len(re.findall(r"^\d+\.\s+", content, re.MULTILINE))
    procedural_types = {"SOP", "Runbook", "Playbook", "Change Management"}

    if doc_type in procedural_types:
        return numbered >= 5, numbered
    return True, numbered


def check_version_history(content: str) -> bool:
    """Check if document has version history section."""
    content_lower = content.lower()
    return any(kw in content_lower for kw in [
        "version history", "revision history", "change log",
        "version | date", "version|date", "document history"
    ])


def check_specificity(content: str) -> Tuple[bool, List[str]]:
    """Check for vague/generic phrases that indicate low quality."""
    vague_phrases = [
        "as needed", "when appropriate", "in a timely manner",
        "best practices", "ensure compliance", "coordinate with",
        "work closely", "as required", "on a regular basis",
    ]
    content_lower = content.lower()
    found = [p for p in vague_phrases if content_lower.count(p) > 3]
    return len(found) == 0, found


def check_approval_section(content: str) -> bool:
    """Check if document has approval section."""
    content_lower = content.lower()
    return any(kw in content_lower for kw in [
        "approval", "approved by", "sign-off", "sign off", "authorized by"
    ])


# ============================================================
# SCORING
# ============================================================

def calculate_score(checks: Dict) -> int:
    """Calculate quality score out of 100."""
    weights = {
        "word_count":       20,
        "sections":         25,
        "markdown":         10,
        "no_placeholders":  15,
        "company_name":     10,
        "tables":           5,
        "numbered_lists":   5,
        "version_history":  5,
        "approval":         5,
    }
    score = 0
    for check, weight in weights.items():
        if checks.get(check, False):
            score += weight
    return score


def get_grade(score: int) -> Tuple[str, str]:
    """Return letter grade and color."""
    if score >= 90:
        return "A", "🟢 Excellent"
    elif score >= 75:
        return "B", "🟡 Good"
    elif score >= 60:
        return "C", "🟠 Acceptable"
    elif score >= 40:
        return "D", "🔴 Needs Improvement"
    else:
        return "F", "❌ Poor Quality"


# ============================================================
# MAIN VALIDATE FUNCTION
# ============================================================

def validate_document(
    content: str,
    doc_type: str,
    department: str,
    question_answers: dict = None,
) -> Dict:
    """
    Run all validation checks and return a full report.
    
    Returns:
        {
            "valid": bool,
            "score": int,
            "grade": str,
            "word_count": int,
            "checks": {...},
            "issues": [...],
            "warnings": [...],
            "passed": [...],
        }
    """
    if not question_answers:
        question_answers = {}

    company_name = question_answers.get("company_name", "")
    issues   = []
    warnings = []
    passed   = []
    checks   = {}

    # ── 1. Word Count ──
    wc_ok, word_count, min_wc = check_word_count(content, doc_type)
    checks["word_count"] = wc_ok
    if wc_ok:
        passed.append(f"✅ Word count: {word_count:,} words (minimum: {min_wc:,})")
    else:
        issues.append(f"❌ Word count too low: {word_count:,} words (minimum required: {min_wc:,})")

    # ── 2. Required Sections ──
    sec_ok, present_secs, missing_secs = check_sections_present(content, doc_type)
    checks["sections"] = sec_ok
    if sec_ok:
        passed.append(f"✅ All required sections present ({len(present_secs)} sections)")
    else:
        issues.append(f"❌ Missing sections: {', '.join(missing_secs)}")
        if present_secs:
            warnings.append(f"⚠️ Sections found: {', '.join(present_secs)}")

    # ── 3. Markdown Structure ──
    md_ok, md_issues = check_markdown_structure(content)
    checks["markdown"] = md_ok
    if md_ok:
        h2 = len(re.findall(r"^##\s+.+", content, re.MULTILINE))
        h3 = len(re.findall(r"^###\s+.+", content, re.MULTILINE))
        passed.append(f"✅ Markdown structure: {h2} main sections, {h3} subsections")
    else:
        for issue in md_issues:
            warnings.append(f"⚠️ {issue}")
        checks["markdown"] = False

    # ── 4. No Placeholders ──
    ph_ok, placeholders = check_placeholders(content)
    checks["no_placeholders"] = ph_ok
    if ph_ok:
        passed.append("✅ No placeholder text found")
    else:
        issues.append(f"❌ Placeholder text found: {', '.join(set(placeholders[:5]))}")

    # ── 5. Company Name Usage ──
    cn_ok, cn_count = check_company_name(content, company_name)
    checks["company_name"] = cn_ok
    if company_name and company_name not in ("the company", ""):
        if cn_ok:
            passed.append(f"✅ Company name '{company_name}' used {cn_count} times")
        else:
            warnings.append(f"⚠️ Company name '{company_name}' used only {cn_count} time(s) — should appear more")

    # ── 6. Tables ──
    tbl_ok, tbl_count = check_has_tables(content, doc_type)
    checks["tables"] = tbl_ok
    if tbl_ok:
        passed.append(f"✅ Tables present: {tbl_count} table(s)")
    else:
        warnings.append(f"⚠️ No markdown tables found — {doc_type} should include at least 1 table")

    # ── 7. Numbered Lists ──
    nl_ok, nl_count = check_has_numbered_lists(content, doc_type)
    checks["numbered_lists"] = nl_ok
    if nl_ok:
        passed.append(f"✅ Numbered steps present: {nl_count} step(s)")
    else:
        warnings.append(f"⚠️ Few numbered steps ({nl_count}) — {doc_type} should have step-by-step procedures")

    # ── 8. Version History ──
    vh_ok = check_version_history(content)
    checks["version_history"] = vh_ok
    if vh_ok:
        passed.append("✅ Version history section present")
    else:
        warnings.append("⚠️ No version history section found")

    # ── 9. Approval Section ──
    ap_ok = check_approval_section(content)
    checks["approval"] = ap_ok
    if ap_ok:
        passed.append("✅ Approval section present")
    else:
        warnings.append("⚠️ No approval section found")

    # ── 10. Vague language check ──
    sp_ok, vague = check_specificity(content)
    if not sp_ok:
        warnings.append(f"⚠️ Overused vague phrases: {', '.join(vague)} — consider being more specific")

    # ── Score & Grade ──
    score      = calculate_score(checks)
    grade, label = get_grade(score)
    valid      = score >= 60 and len(issues) <= 2

    return {
        "valid":      valid,
        "score":      score,
        "grade":      grade,
        "label":      label,
        "word_count": word_count,
        "doc_type":   doc_type,
        "department": department,
        "checks":     checks,
        "issues":     issues,
        "warnings":   warnings,
        "passed":     passed,
        "summary":    f"{label} — Score: {score}/100 | {word_count:,} words | {len(passed)} checks passed, {len(issues)} issues, {len(warnings)} warnings",
    }