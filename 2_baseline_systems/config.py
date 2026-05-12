"""
Configuration for the baseline systems.

All settings can be overridden via environment variables (or a .env file at
the project root). Defaults assume a local Ollama install and the bundled
shadow_network_sample_dataset/ as the data source.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass


PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
BASELINE_DIR: Path = Path(__file__).resolve().parent

DATASET_DIR: Path = Path(
    os.getenv("SHADOW_DATASET_DIR", PROJECT_ROOT / "shadow_network_sample_dataset")
)

OUTPUT_DIR: Path = Path(os.getenv("BENCHMARK_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
RESULTS_DIR: Path = OUTPUT_DIR / "benchmark_results"

CHROMA_DIR: Path = Path(os.getenv("CHROMA_DIR", PROJECT_ROOT / "outputs" / "chroma_db"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "shadow_network_baseline")

OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_S: float = float(os.getenv("OLLAMA_TIMEOUT_S", "60"))

EMBED_MODEL: str = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DEVICE: str = os.getenv("EMBED_DEVICE", "cpu")

TOP_K: int = int(os.getenv("VECTOR_TOP_K", "5"))


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def summary() -> dict:
    return {
        "dataset_dir": str(DATASET_DIR),
        "output_dir": str(OUTPUT_DIR),
        "chroma_dir": str(CHROMA_DIR),
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "embed_model": EMBED_MODEL,
        "top_k": TOP_K,
    }
