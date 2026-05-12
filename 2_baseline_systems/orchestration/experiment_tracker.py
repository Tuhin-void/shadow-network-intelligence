"""
Experiment tracker for reproducibility.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


class ExperimentTracker:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path(__file__).parent.parent.parent / "outputs" / "experiments")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.runs: dict = {}

    def create_run(
        self,
        config: dict,
        profile: str,
        dataset_hash: str = "",
    ) -> dict:
        from ..shared.schemas import BenchmarkRun
        run_id = self._generate_id()
        timestamp = datetime.now().isoformat()

        run_meta = {
            "run_id": run_id,
            "timestamp": timestamp,
            "profile": profile,
            "config_snapshot": self._sanitize(config),
            "dataset_hash": dataset_hash,
        }

        self.runs[run_id] = run_meta
        self._save(run_id, run_meta)
        return run_meta

    def record_result(self, run_id: str, approach: str, result: dict) -> None:
        if run_id not in self.runs:
            return
        if "results" not in self.runs[run_id]:
            self.runs[run_id]["results"] = {}
        if approach not in self.runs[run_id]["results"]:
            self.runs[run_id]["results"][approach] = []
        self.runs[run_id]["results"][approach].append(result)
        self._save(run_id, self.runs[run_id])

    def record_evaluation(self, run_id: str, evaluation: dict) -> None:
        if run_id not in self.runs:
            return
        if "evaluations" not in self.runs[run_id]:
            self.runs[run_id]["evaluations"] = []
        self.runs[run_id]["evaluations"].append(evaluation)
        self._save(run_id, self.runs[run_id])

    def get_run(self, run_id: str) -> Optional[dict]:
        if run_id in self.runs:
            return self.runs[run_id]
        path = self.storage_dir / f"{run_id}.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                self.runs[run_id] = data
                return data
        return None

    def list_runs(self) -> list[dict]:
        runs = []
        for p in sorted(self.storage_dir.glob("*.json"), reverse=True):
            with open(p) as f:
                runs.append(json.load(f))
        return runs

    def get_reproducibility_metadata(self, run_id: str) -> Optional[dict]:
        run = self.get_run(run_id)
        if not run:
            return None
        return {
            "run_id": run["run_id"],
            "timestamp": run["timestamp"],
            "profile": run["profile"],
            "config": run.get("config_snapshot", {}),
            "dataset_hash": run.get("dataset_hash", ""),
            "python_version": "3.11",
        }

    def _generate_id(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"EXP_{ts}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]}"

    def _sanitize(self, config: dict) -> dict:
        safe = dict(config)
        for key in ("openai_api_key", "anthropic_api_key", "tigergraph_password"):
            if key in safe:
                safe[key] = "***"
        return safe

    def _save(self, run_id: str, data: dict) -> None:
        path = self.storage_dir / f"{run_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)