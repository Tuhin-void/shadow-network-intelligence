"""Tracing module — logs retrieval decisions for debugging."""
import logging
import time
from typing import Optional


class RetrievalTracer:
    """
    Traces graph retrieval execution for debugging and audit.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.logger = logging.getLogger("graphrag.trace")
        self.spans: list[dict] = []

    def start_span(self, name: str, tags: Optional[dict] = None) -> str:
        if not self.enabled:
            return ""

        span_id = f"span_{len(self.spans):04d}"
        span = {
            "id": span_id,
            "name": name,
            "start_time": time.time(),
            "tags": tags or {},
            "events": [],
        }
        self.spans.append(span)
        self.logger.debug(f"[{span_id}] Start: {name}")
        return span_id

    def add_event(self, span_id: str, event: str, data: Optional[dict] = None) -> None:
        if not self.enabled or not span_id:
            return

        for span in self.spans:
            if span["id"] == span_id:
                span["events"].append({
                    "event": event,
                    "time": time.time(),
                    "data": data or {},
                })
                break

    def end_span(self, span_id: str, result: Optional[dict] = None) -> None:
        if not self.enabled or not span_id:
            return

        for span in self.spans:
            if span["id"] == span_id:
                span["end_time"] = time.time()
                span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000
                if result:
                    span["result"] = result
                self.logger.debug(
                    f"[{span_id}] End: {span['name']} ({span['duration_ms']:.1f}ms)"
                )
                break

    def get_trace(self) -> list[dict]:
        return self.spans

    def clear(self) -> None:
        self.spans = []

    def summary(self) -> dict:
        if not self.spans:
            return {"total_spans": 0}

        total_duration = sum(s.get("duration_ms", 0) for s in self.spans)
        return {
            "total_spans": len(self.spans),
            "total_duration_ms": total_duration,
            "spans": self.spans,
        }