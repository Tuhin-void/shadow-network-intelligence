"""
Generates 2_baseline_systems_overview.pdf — a self-contained explanation of
what this folder does, how the pieces fit together, and how to run it.

Usage:
    ../.venv/bin/python generate_overview_pdf.py
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Preformatted,
)


HERE = Path(__file__).resolve().parent
OUTPUT_PATH = HERE / "2_baseline_systems_overview.pdf"


def _styles():
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title", parent=base["Title"], fontSize=22, leading=26, spaceAfter=12
    )
    h1 = ParagraphStyle(
        "H1", parent=base["Heading1"], fontSize=15, leading=19,
        spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1f2d3d"),
    )
    h2 = ParagraphStyle(
        "H2", parent=base["Heading2"], fontSize=12, leading=16,
        spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#34495e"),
    )
    body = ParagraphStyle(
        "Body", parent=base["BodyText"], fontSize=10, leading=14,
        alignment=TA_LEFT, spaceAfter=6,
    )
    mono = ParagraphStyle(
        "Mono", parent=base["Code"], fontSize=9, leading=12,
        backColor=colors.HexColor("#f4f4f4"), borderPadding=6,
        leftIndent=8, rightIndent=8,
    )
    caption = ParagraphStyle(
        "Caption", parent=base["BodyText"], fontSize=8, leading=10,
        textColor=colors.HexColor("#777"), spaceAfter=10,
    )
    return {"title": title, "h1": h1, "h2": h2, "body": body, "mono": mono, "caption": caption}


def _table(data, col_widths=None, header=True):
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]
    if not header:
        style = style[2:]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t


def _para(text, style):
    return Paragraph(text, style)


def build_story():
    s = _styles()
    story = []

    story.append(_para("Shadow Network Intelligence", s["title"]))
    story.append(_para("Folder 2 — <b>2_baseline_systems/</b>", s["h1"]))
    story.append(_para(
        "Pure LLM and Vector RAG baselines for fraud-detection benchmarking. "
        "These are the lower-bound comparators against which the GraphRAG approach "
        "(folder 3) will be evaluated.",
        s["body"],
    ))

    story.append(_para("What this folder does", s["h1"]))
    story.append(_para(
        "Folder 2 implements <b>two of the three approaches</b> the project compares "
        "for detecting financial crime in transaction networks:",
        s["body"],
    ))
    story.append(_table([
        ["Approach", "How it answers", "When it wins"],
        ["Pure LLM",
         "Direct question to the LLM. No retrieval, no data access.",
         "Trivia / general-knowledge questions."],
        ["Vector RAG",
         "Embed question → top-k similar documents from ChromaDB → "
         "inject as context → LLM generates a grounded answer.",
         "Document-style queries where keyword/semantic similarity is enough."],
        ["GraphRAG (folder 3)",
         "Graph traversal on TigerGraph + vector hybrid. NOT in this folder.",
         "Relationship-heavy queries (ownership chains, address sharing, hops)."],
    ], col_widths=[1.2 * inch, 3.2 * inch, 2.2 * inch]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(_para(
        "The benchmark runs every benchmark question through both baselines, captures "
        "latency / tokens / answer / retrieved sources, and writes a results JSON to "
        "<b>outputs/benchmark_results/</b>.",
        s["body"],
    ))

    story.append(_para("Data source (read-only)", s["h1"]))
    story.append(_para(
        "All input data comes from <b>shadow_network_sample_dataset/</b> at the project "
        "root — a tiny preview of what the data engine (folder 1) will eventually generate. "
        "Folder 2 only reads from it; nothing is written back.",
        s["body"],
    ))
    story.append(_table([
        ["Entity", "Count", "Notes"],
        ["Persons", "3", "Includes one sanctions-flagged individual (Elena Volkov)"],
        ["Companies", "3", "Three ShadowCorp entities in circular ownership"],
        ["Accounts", "3", "At Emirates Gulf, Oceanic Trust, Harbor Financial"],
        ["Addresses", "2", "ADDR-000002 is shared by all 3 companies (shell pattern)"],
        ["Transactions", "3", "A1 → A2 → A3 → A1 layered chain at ~$150K each"],
        ["Edges", "10", "OWNS, HAS_ACCOUNT, LOCATED_AT relationships"],
        ["Authored docs", "2", "Pre-written compliance summaries"],
        ["Benchmark Qs", "2", "With expected pipeline winner (GraphRAG) and difficulty"],
    ], col_widths=[1.6 * inch, 0.7 * inch, 4.3 * inch]))

    story.append(_para("Module layout", s["h1"]))
    story.append(Preformatted(
        "2_baseline_systems/\n"
        "├── config.py                  Env-driven settings (Ollama URL, paths, top-k)\n"
        "├── requirements.txt           chromadb, sentence-transformers, requests, pandas\n"
        "├── data_loader.py             Reads CSVs/JSONs from sample dataset\n"
        "├── document_builder.py        Hybrid chunking → 16 ChromaDB documents\n"
        "├── benchmark_data_loader.py   Loads questions + ground-truth fraud ring\n"
        "├── benchmark_runner.py        CLI entrypoint; wires baselines, writes results\n"
        "├── generate_overview_pdf.py   This file — regenerates the PDF\n"
        "│\n"
        "├── pure_llm/\n"
        "│   ├── ollama_client.py       Minimal /api/generate HTTP wrapper\n"
        "│   └── baseline.py            PureLLMBaseline.answer(q) — no retrieval\n"
        "│\n"
        "└── vector_rag/\n"
        "    ├── embedder.py            sentence-transformers all-MiniLM-L6-v2 (384-dim)\n"
        "    ├── chroma_store.py        PersistentClient → outputs/chroma_db/\n"
        "    └── baseline.py            VectorRAGBaseline.answer(q)\n",
        s["mono"],
    ))

    story.append(PageBreak())

    story.append(_para("How a question flows through the system", s["h1"]))

    story.append(_para("Pure LLM (lower bound)", s["h2"]))
    story.append(Preformatted(
        "question  ──►  OllamaClient.generate(prompt, system=SYSTEM_PROMPT)  ──►  answer\n"
        "                                                                          │\n"
        "                                                                          ▼\n"
        "                                                          {answer, latency, tokens}\n",
        s["mono"],
    ))
    story.append(_para(
        "No retrieval. The LLM only knows what was in its training data. Expect "
        "hallucinations on questions referencing specific entity IDs.",
        s["body"],
    ))

    story.append(_para("Vector RAG", s["h2"]))
    story.append(Preformatted(
        "question  ──►  Embedder.embed(q)  ──►  ChromaStore.search(top_k=5)\n"
        "                                                │\n"
        "                                                ▼\n"
        "                                       [hits with text + metadata + distance]\n"
        "                                                │\n"
        "                                                ▼\n"
        "                                    format_context → prompt template\n"
        "                                                │\n"
        "                                                ▼\n"
        "                                       OllamaClient.generate(...)\n"
        "                                                │\n"
        "                                                ▼\n"
        "                          {answer, sources[], latency, retrieval_ms, tokens}\n",
        s["mono"],
    ))

    story.append(_para("Chunking strategy (the design decision)", s["h1"]))
    story.append(_para(
        "<b>Hybrid: 3 document types are indexed into ChromaDB.</b> With only ~14 entities "
        "and ~3 transactions, pure per-row chunking would be too granular; a single mega-doc "
        "would lose retrieval precision. Three types balance both.",
        s["body"],
    ))
    story.append(_table([
        ["Doc type", "Count", "What it is", "Good for"],
        ["entity_profile", "11",
         "One paragraph per Person/Company/Account/Address with all linked "
         "ownerships, accounts, and addresses rolled into natural language.",
         "“Who is X?”, “What does C-000001 own?”"],
        ["transaction", "3",
         "One sentence per transaction with party names resolved and risk score.",
         "“Find layered transfers > $100K”, “Recent suspicious wires”"],
        ["authored", "2",
         "The pre-authored semantic_documents.json passed through verbatim.",
         "Narrative / compliance-officer style questions"],
    ], col_widths=[1.2 * inch, 0.55 * inch, 2.4 * inch, 2.45 * inch]))

    story.append(Spacer(1, 0.1 * inch))
    story.append(_para(
        "Total: <b>16 documents</b>, each embedded to 384 dims with "
        "<i>sentence-transformers/all-MiniLM-L6-v2</i>, stored under "
        "<i>outputs/chroma_db/shadow_network_baseline</i> using cosine similarity.",
        s["body"],
    ))

    story.append(_para("How to run", s["h1"]))
    story.append(Preformatted(
        "# 1. One-time setup\n"
        "python3.12 -m venv .venv\n"
        ".venv/bin/python -m pip install -r 2_baseline_systems/requirements.txt\n"
        "ollama serve &              # start Ollama\n"
        "ollama pull llama3.2        # one-time model download\n\n"
        "# 2. Run the benchmark\n"
        "cd 2_baseline_systems\n"
        "../.venv/bin/python benchmark_runner.py\n\n"
        "# Options:\n"
        "#   --approaches pure_llm,vector_rag   # subset\n"
        "#   --questions custom_qs.json         # bring your own questions\n"
        "#   --limit 1                          # smoke-test\n"
        "#   --skip-index                       # reuse existing Chroma index\n"
        "#   --output PATH                      # override results path\n",
        s["mono"],
    ))

    story.append(_para("Where results live", s["h1"]))
    story.append(_table([
        ["Path", "What it is"],
        ["outputs/benchmark_results/benchmark_<ts>.json",
         "Run summary + every individual answer with sources, latency, GT eval"],
        ["outputs/chroma_db/chroma.sqlite3",
         "Vector store metadata (collection registry, document store, IDs)"],
        ["outputs/chroma_db/<uuid>/data_level0.bin",
         "Raw 384-dim embedding vectors for the HNSW index"],
        ["outputs/chroma_db/<uuid>/*.bin",
         "HNSW graph structure (header, length, link_lists)"],
    ], col_widths=[3.4 * inch, 3.2 * inch]))

    story.append(PageBreak())

    story.append(_para("Configuration (env vars, all optional)", s["h1"]))
    story.append(_table([
        ["Variable", "Default", "Used by"],
        ["OLLAMA_URL", "http://localhost:11434", "Both baselines"],
        ["OLLAMA_MODEL", "llama3.2", "Both baselines"],
        ["OLLAMA_TIMEOUT_S", "60", "OllamaClient request timeout"],
        ["EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2", "Vector RAG"],
        ["EMBED_DEVICE", "cpu", "sentence-transformers device"],
        ["CHROMA_DIR", "outputs/chroma_db", "Vector RAG persistence path"],
        ["CHROMA_COLLECTION", "shadow_network_baseline", "Collection name"],
        ["VECTOR_TOP_K", "5", "Retrieval depth"],
        ["SHADOW_DATASET_DIR", "shadow_network_sample_dataset/", "Data source"],
        ["BENCHMARK_OUTPUT_DIR", "outputs/", "Where results land"],
    ], col_widths=[2.0 * inch, 2.5 * inch, 2.0 * inch]))

    story.append(_para("Result schema (per question, per approach)", s["h1"]))
    story.append(Preformatted(
        "{\n"
        "  \"approach\":            \"pure_llm\" | \"vector_rag\",\n"
        "  \"question\":            \"<full question text>\",\n"
        "  \"question_id\":         \"Q001\",\n"
        "  \"question_meta\":       { ...all original question metadata },\n"
        "  \"answer\":              \"<LLM-generated answer text>\" | null,\n"
        "  \"sources\":             [ { id, doc_type, distance }, ... ],\n"
        "  \"latency_ms\":          <float>,\n"
        "  \"retrieval_ms\":        <float, vector_rag only>,\n"
        "  \"prompt_tokens\":       <int>,\n"
        "  \"completion_tokens\":   <int>,\n"
        "  \"model\":               \"llama3.2\",\n"
        "  \"error\":               null | \"<error msg if Ollama unreachable>\",\n"
        "  \"ground_truth_eval\":   { score, matched_entities, matched_address }\n"
        "}\n",
        s["mono"],
    ))

    story.append(_para("First-run benchmark results (real numbers)", s["h1"]))
    story.append(_para(
        "Question tested: <i>“Find all companies sharing an address with ShadowCorp Holdings "
        "that transferred funds offshore within 24 hours.”</i>",
        s["body"],
    ))
    story.append(_table([
        ["Metric", "Pure LLM", "Vector RAG"],
        ["Latency", "9.3 s", "5.9 s"],
        ["Prompt tokens", "108", "530"],
        ["Completion tokens", "187", "148"],
        ["Ground-truth score", "0.125", "0.375"],
        ["Entities correctly named",
         "0 — hallucinated FSP-000001, ECP-000002, BCS-000003",
         "3 — C-000002, C-000003, A-000002"],
        ["Shared address mentioned",
         "made up “123 Main St, Anytown, USA”",
         "correctly: “PO Box 778 George Town Cayman Islands”"],
    ], col_widths=[1.6 * inch, 2.5 * inch, 2.4 * inch]))

    story.append(Spacer(1, 0.1 * inch))
    story.append(_para(
        "<b>Takeaway:</b> Vector RAG was 1.6× faster, used 3× more prompt tokens (for "
        "retrieved context), and was <b>3× more accurate</b> on the ground-truth signal. "
        "This is the design proving itself on the first real run.",
        s["body"],
    ))

    story.append(_para("Constraints & non-goals", s["h1"]))
    story.append(_para(
        "• <b>Only modifies files inside 2_baseline_systems/.</b> Reads from "
        "shadow_network_sample_dataset/ and writes to outputs/, but never edits other "
        "numbered folders.<br/>"
        "• <b>No GraphRAG here.</b> That lives in folder 3.<br/>"
        "• <b>Ollama is required at runtime.</b> Without it the runner records "
        "per-question errors rather than crashing.<br/>"
        "• <b>Ground-truth evaluator is intentionally coarse.</b> Simple ID string-match "
        "against the fraud ring. Replace with LLM-as-judge for real accuracy work.",
        s["body"],
    ))

    story.append(_para("Where this fits in the bigger picture", s["h1"]))
    story.append(_para(
        "Folder 2 is the <b>baseline comparator</b>. The eventual story is:",
        s["body"],
    ))
    story.append(_para(
        "&nbsp;&nbsp;1. Folder 1 generates synthetic transaction data.<br/>"
        "&nbsp;&nbsp;2. Folder 2 (this) and folder 3 (GraphRAG) both answer questions on it.<br/>"
        "&nbsp;&nbsp;3. Folder 4 orchestrates and exposes a unified API.<br/>"
        "&nbsp;&nbsp;4. The benchmark proves GraphRAG’s value <i>relative to</i> folder 2.<br/>"
        "Without folder 2 as a comparator, there is no quantitative argument for GraphRAG.",
        s["body"],
    ))
    story.append(_para(
        "<i>This PDF is regenerated by running ../.venv/bin/python generate_overview_pdf.py "
        "from inside 2_baseline_systems/.</i>",
        s["caption"],
    ))

    return story


def main() -> None:
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.7 * inch,
        title="2_baseline_systems Overview",
        author="Shadow Network Intelligence",
    )
    doc.build(build_story())
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
