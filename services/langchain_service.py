import os
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import LLMChain
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# ── Max tokens per document length ────────────────────────────────────
# gpt-4o-mini supports up to 16384 output tokens
DOCUMENT_MAX_TOKENS = {
    "short":  500,    # Offer Letter = 1 page max, 150-200 words
    "medium": 4000,   # Contracts, Reports = 4-8 pages
    "long":   14000,  # Employee Handbook, IT Policy = 35+ pages
}

# ── Exact per-document overrides (from Question_Answer.json specs) ────
DOCUMENT_TOKEN_OVERRIDES = {
    "Offer Letter":               500,   # 1 page ONLY - 150-200 words max
    "Invoice Template":           400,   # 1 page ONLY
    "Press Release Template":     600,   # 1 page ONLY
    "Onboarding Checklist":       1000,  # 1-3 pages
    "Bug Report Template":        600,   # 1-2 pages
    "Test Case Template":         600,   # 1-2 pages
    "Exit Interview Form":        1500,  # 2-4 pages
    "Performance Appraisal Form": 2500,  # 3-8 pages
    "Leave Policy Document":      3000,  # 5-12 pages
    "Employment Contract":        2000,  # 2-5 pages
    "Non-Disclosure Agreement (NDA)": 2000,
    "Service Level Agreement (SLA)":  2500,
    "Code of Conduct":            7000,  # 15-25 pages
    "HR Policy Manual":           9000,  # 20-30 pages
    "Employee Handbook":          16000, # 35-40 pages (MAXIMUM tokens for long docs)
    "IT Policy Manual":           12000, # 20-35 pages
    "Information Security Policy": 12000,
    "Business Continuity Plan (BCP)": 10000,
    "Disaster Recovery Plan":     10000,
    "Cybersecurity Risk Assessment": 10000,
}


def get_llm(max_tokens: int = 4000):
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
        api_version=os.getenv("AZURE_LLM_API_VERSION"),
        deployment_name=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI"),
        temperature=0.3,
        max_tokens=max_tokens,
    )


def get_max_tokens(prompt_text: str, doc_type: str = "") -> int:
    """
    Determine max_tokens based on doc_type or prompt content.
    Priority: doc_type override > prompt length detection > default
    """
    # 1. Check exact doc_type override first
    if doc_type and doc_type in DOCUMENT_TOKEN_OVERRIDES:
        tokens = DOCUMENT_TOKEN_OVERRIDES[doc_type]
        logger.info(f"Doc type override: {doc_type} → {tokens} tokens")
        return tokens

    # 2. Detect from prompt content
    if any(x in prompt_text for x in [
        "35+ pages", "15000+ words", "15000-20000", "35-50 pages",
        "Employee Handbook", "IT Policy Manual", "Information Security Policy"
    ]):
        return DOCUMENT_MAX_TOKENS["long"]

    if any(x in prompt_text for x in [
        "4-8 pages", "2000-4000 words", "1500-4000 words",
        "5-12 pages", "15-25 pages", "20-30 pages"
    ]):
        return DOCUMENT_MAX_TOKENS["medium"]

    if any(x in prompt_text for x in [
        "1 page ONLY", "300-500 words", "1-3 pages"
    ]):
        return DOCUMENT_MAX_TOKENS["short"]

    # 3. Default medium
    return DOCUMENT_MAX_TOKENS["medium"]


def generate_document_with_langchain(prompt_text: str, doc_type: str = "") -> str:
    """
    Generate document with smart token control based on document type.

    - Offer Letter        → 500 tokens  = 1 page (150-200 words)
    - Employment Contract → 2000 tokens = 2-5 pages
    - Code of Conduct     → 7000 tokens = 15-25 pages
    - Employee Handbook   → 14000 tokens = 35-50 pages
    """
    max_tokens = get_max_tokens(prompt_text, doc_type)
    logger.info(f"Generating '{doc_type}' — max_tokens: {max_tokens}")

    llm = get_llm(max_tokens=max_tokens)
    prompt = PromptTemplate(
        input_variables=["content"],
        template="{content}",
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    result = chain.run(content=prompt_text)
    logger.info(f"Generated {len(result.split())} words for '{doc_type}'")
    return result
