"""Shared test configuration — adds the repo root to sys.path so tests
can import cross-module packages (3_graph_intelligence_core, etc.) the
same way the orchestrator does at runtime."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# 3_graph_intelligence_core uses bare imports (`from configs.config import ...`)
# so we also need it on the path for the GraphRAG-side tests.
_CORE = _REPO_ROOT / "3_graph_intelligence_core"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))
# 4_orchestrator_api uses bare imports too (`from orchestration.activation
# import get_activation`) — uvicorn handles this via `--app-dir`; tests
# mirror it here.
_API = _REPO_ROOT / "4_orchestrator_api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))
