# eval/ragas_eval.py
import os, json
from datetime import datetime
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger(__name__)

RESULTS_DIR = Path(os.getenv("EVAL_RESULTS_DIR", "./eval_results"))
RESULTS_DIR.mkdir(exist_ok=True)

DEFAULT_DATASET = [
    {"question": "What are the confidentiality obligations in the NDA?",
     "ground_truth": "The receiving party must protect confidential information with at least reasonable care."},
    {"question": "What is the SLA uptime guarantee?",
     "ground_truth": "99.9% monthly availability is guaranteed."},
    {"question": "What does the HR leave policy say about annual leave?",
     "ground_truth": "Employees are entitled to paid annual leave as per company policy."},
    {"question": "What triggers a data breach notification obligation?",
     "ground_truth": "Unauthorized access to personal data must be reported within 72 hours."},
    {"question": "What are the payment terms in the vendor contract?",
     "ground_truth": "Payment is due within 30 days of invoice receipt."},
]


# ── scorers ──────────────────────────────────────────────────────────────

def _faithfulness(answer: str, chunks: list) -> float:
    if not chunks or not answer:
        return 0.0
    chunk_text = " ".join(c.get("text", "").lower() for c in chunks)
    words = [w for w in answer.lower().split() if len(w) > 5]
    if not words:
        return 0.5
    return min(sum(1 for w in words if w in chunk_text) / len(words) * 1.5, 1.0)


def _answer_relevancy(question: str, answer: str) -> float:
    if not answer or not question:
        return 0.0
    q_words = {w.lower() for w in question.split() if len(w) > 3}
    a_words = {w.lower() for w in answer.split()}
    if not q_words:
        return 0.5
    return min(len(q_words & a_words) / len(q_words) * 2.5, 1.0)


def _context_recall(ground_truth: str, chunks: list) -> float:
    if not ground_truth or not chunks:
        return 0.5
    chunk_text = " ".join(c.get("text", "").lower() for c in chunks)
    gt_words   = {w.lower() for w in ground_truth.split() if len(w) > 4}
    if not gt_words:
        return 0.5
    return min(sum(1 for w in gt_words if w in chunk_text) / len(gt_words) * 1.8, 1.0)

def _context_precision(chunks: list, threshold: float = 0.25) -> float:
    if not chunks:
        return 0.0
    relevant = sum(1 for c in chunks if c.get("score", 0) >= threshold)
    return relevant / len(chunks)


# ── main runner ───────────────────────────────────────────────────────────

def run_ragas_evaluation(dataset: list = None, config: dict = None,
                         save_results: bool = True) -> dict:
    from rag.tools import search_docs, refine_query

    dataset = dataset or DEFAULT_DATASET
    config  = config  or {"top_k": 5, "use_refine": True, "filters": {}}

    top_k      = config.get("top_k", 5)
    use_refine = config.get("use_refine", True)
    filters    = config.get("filters", {})

    rows = []
    faith_list, relev_list, recall_list, prec_list = [], [], [], []

    for item in dataset:
        question     = item.get("question", "")
        ground_truth = item.get("ground_truth", "")
        if not question:
            continue

        refined = question
        if use_refine:
            refined = refine_query(question).get("refined", question)

        search_result = search_docs(
            query      = refined,
            doc_type   = filters.get("doc_type"),
            department = filters.get("department"),
            industry   = filters.get("industry"),
            top_k      = top_k,
        )
        chunks = search_result.get("chunks", [])

        # generate answer
        if chunks:
            context = "\n\n".join(
                f"[{c['doc_title']}]\n{c['text']}" for c in chunks
            )
            prompt = (
                f"Answer using ONLY the context below.\n"
                f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
            )
            try:
                from langchain_openai import AzureChatOpenAI
                llm = AzureChatOpenAI(
                    azure_endpoint   = os.getenv("AZURE_LLM_ENDPOINT", ""),
                    api_key          = os.getenv("AZURE_OPENAI_LLM_KEY", ""),
                    api_version      = os.getenv("AZURE_LLM_API_VERSION", "2024-02-15-preview"),
                    azure_deployment = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI", ""),
                    temperature=0, max_tokens=500,
                )
                answer = llm.invoke(prompt).content.strip()
            except Exception as e:
                answer = f"LLM error: {e}"
        else:
            answer = "No relevant documents found."

        f  = round(_faithfulness(answer, chunks), 3)
        r  = round(_answer_relevancy(question, answer), 3)
        rc = round(_context_recall(ground_truth, chunks), 3)
        p  = round(_context_precision(chunks), 3)

        faith_list.append(f)
        relev_list.append(r)
        recall_list.append(rc)
        prec_list.append(p)

        # Citation strings — user-friendly format
        citation_strings = [
            f"{c.get('doc_title','?')} › {c.get('section','General')}"
            for c in chunks[:3]
        ]

        rows.append({
            "question":          question,
            "answer":            answer[:400],
            "ground_truth":      ground_truth,
            "refined_query":     refined,
            "citations":         citation_strings,
            "chunks_used":       len(chunks),
            "faithfulness":      f,
            "answer_relevancy":  r,
            "context_recall":    rc,
            "context_precision": p,
        })

    def avg(lst): return round(sum(lst) / len(lst), 3) if lst else 0.0

    overall = avg([avg(faith_list), avg(relev_list), avg(recall_list), avg(prec_list)])

    # ── scores dict — matches what UI expects ────────────────────────────
    result = {
        "timestamp":    datetime.now().isoformat(),
        "dataset_size": len(rows),
        "config":       config,
        # Top-level for simple access
        "faithfulness":       avg(faith_list),
        "answer_relevancy":   avg(relev_list),
        "context_recall":     avg(recall_list),
        "context_precision":  avg(prec_list),
        # Nested scores dict — for eval history table
        "scores": {
            "overall":           overall,
            "faithfulness":      avg(faith_list),
            "answer_relevancy":  avg(relev_list),
            "context_recall":    avg(recall_list),
            "context_precision": avg(prec_list),
        },
        "results": rows,  # per-question detail
        "rows":    rows,  # alias
    }

    if save_results:
        fname = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(fname, "w") as fh:
                json.dump(result, fh, indent=2)
            logger.info(f"Eval saved: {fname}")
        except Exception as e:
            logger.error(f"Save error: {e}")

    return result


def load_latest_results() -> dict:
    files = sorted(RESULTS_DIR.glob("eval_*.json"), reverse=True)
    if not files:
        return None
    try:
        with open(files[0]) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Load error: {e}")
        return None


def load_all_results() -> list:
    files   = sorted(RESULTS_DIR.glob("eval_*.json"), reverse=True)
    results = []
    for fp in files[:20]:
        try:
            with open(fp) as f:
                data = json.load(f)
                data["filename"] = fp.name
                results.append(data)
        except Exception:
            pass
    return results


