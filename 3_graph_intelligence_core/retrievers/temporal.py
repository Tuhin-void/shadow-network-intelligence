"""Temporal retriever — retrieves time-based patterns and anomalies."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TemporalPattern:
    pattern_type: str
    entity_id: str
    time_window: dict
    transaction_count: int
    total_amount: float
    avg_amount: float
    risk_indicators: list[str]


class TemporalRetriever:
    """
    Retrieves time-based patterns in the graph.
    - Transaction spikes
    - Burst detection
    - Temporal anomaly patterns
    - Time-windowed aggregation
    """

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def detect_spike(
        self,
        account_id: str,
        window_hours: int = 24,
        threshold_amount: float = 10000,
    ) -> dict:
        """Detect transaction spike for an account."""
        result = self.client.run_installed_query(
            "tg_temporal_spike",
            {"account_id": account_id, "window_hours": window_hours},
        )

        if "error" not in result:
            return {"detected": True, "analysis": result}

        sent_edges = self.client.get_edges("SENT_TRANSACTION", account_id, limit=100)
        received_edges = self.client.get_edges("RECEIVED_TRANSACTION", account_id, limit=100)

        sent_amounts = [e.get("attributes", {}).get("amount", 0) for e in sent_edges if e]
        received_amounts = [e.get("attributes", {}).get("amount", 0) for e in received_edges if e]

        spikes = []
        if sent_amounts:
            total_sent = sum(sent_amounts)
            avg_sent = total_sent / len(sent_amounts)
            if max(sent_amounts) > threshold_amount:
                spikes.append(f"High outbound spike: max={max(sent_amounts):.2f}, avg={avg_sent:.2f}")

        if received_amounts:
            total_received = sum(received_amounts)
            avg_received = total_received / len(received_amounts)
            if max(received_amounts) > threshold_amount:
                spikes.append(f"High inbound spike: max={max(received_amounts):.2f}, avg={avg_received:.2f}")

        return {
            "detected": len(spikes) > 0,
            "spikes": spikes,
            "sent_count": len(sent_amounts),
            "received_count": len(received_amounts),
            "total_sent": sum(sent_amounts),
            "total_received": sum(received_amounts),
        }

    def get_temporal_context(
        self,
        entity_id: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get time-filtered transaction history for an entity."""
        edges = self.client.get_edges("SENT_TRANSACTION", entity_id, limit=limit)
        edges += self.client.get_edges("RECEIVED_TRANSACTION", entity_id, limit=limit)

        transactions = []
        for e in edges:
            tx_id = e.get("to_id") or e.get("v_id", "")
            tx = self.client.get_vertex("Transaction", tx_id)
            if tx:
                ts = tx.get("attributes", {}).get("timestamp", 0)
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
                transactions.append(tx.get("attributes", {}))

        return sorted(transactions, key=lambda x: x.get("timestamp", 0), reverse=True)

    def find_rapid_fire(self, account_id: str, min_txns: int = 5, window_minutes: int = 30) -> dict:
        """Find rapid-fire transactions (smurfing indicator)."""
        txns = self.get_temporal_context(account_id, limit=100)

        if len(txns) < min_txns:
            return {"detected": False, "reason": "insufficient transactions"}

        timestamps = [t.get("timestamp", 0) for t in txns]
        timestamps.sort()

        burst_count = 0
        for i in range(len(timestamps) - min_txns + 1):
            window = timestamps[i + min_txns - 1] - timestamps[i]
            if window <= window_minutes * 60:
                burst_count += 1

        return {
            "detected": burst_count > 0,
            "burst_count": burst_count,
            "total_transactions": len(txns),
            "window_minutes": window_minutes,
            "min_txns": min_txns,
        }

    def time_series_summary(
        self,
        entity_id: str,
        buckets: int = 10,
    ) -> dict:
        """Summarize entity activity as time-bucketed series."""
        txns = self.get_temporal_context(entity_id, limit=500)

        if not txns:
            return {"buckets": [], "total": 0}

        amounts = [t.get("amount", 0) for t in txns]
        timestamps = [t.get("timestamp", 0) for t in txns]

        if not timestamps:
            return {"buckets": [], "total": 0}

        min_ts = min(timestamps)
        max_ts = max(timestamps)
        range_ts = max_ts - min_ts or 1
        bucket_size = range_ts / buckets

        bucket_data = []
        for b in range(buckets):
            b_start = min_ts + b * bucket_size
            b_end = b_start + bucket_size
            b_txns = [t for t in txns if b_start <= t.get("timestamp", 0) < b_end]
            bucket_data.append({
                "bucket": b,
                "start_time": int(b_start),
                "end_time": int(b_end),
                "tx_count": len(b_txns),
                "total_amount": sum(t.get("amount", 0) for t in b_txns),
                "avg_amount": sum(t.get("amount", 0) for t in b_txns) / max(len(b_txns), 1),
            })

        return {"buckets": bucket_data, "total": len(txns)}