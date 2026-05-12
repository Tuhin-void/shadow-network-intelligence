"""
Helpers - Utility functions for file I/O, data processing, etc.
"""
import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


def ensure_dir(path: str) -> Path:
    """Ensure directory exists, create if not"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path: str) -> Dict[str, Any]:
    """Load JSON file"""
    with open(path, "r") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: str, indent: int = 2) -> None:
    """Save data to JSON file"""
    ensure_dir(Path(path).parent)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, default=str)


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load CSV file as list of dictionaries"""
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_csv(data: List[Dict[str, Any]], path: str) -> None:
    """Save list of dictionaries to CSV"""
    if not data:
        return

    ensure_dir(Path(path).parent)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime as ISO timestamp"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount"""
    return f"{currency} {amount:,.2f}"


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length"""
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide, return default if denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def percentage(part: float, total: float, decimals: int = 1) -> float:
    """Calculate percentage with specified decimals"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, decimals)


class Timer:
    """Simple timer context manager"""

    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start = None
        self.end = None
        self.elapsed = None

    def __enter__(self):
        self.start = datetime.now()
        return self

    def __exit__(self, *args):
        self.end = datetime.now()
        self.elapsed = (self.end - self.start).total_seconds()

    def __str__(self):
        return f"{self.name}: {self.elapsed:.2f}s"


def batch_items(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Batch items into chunks"""
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]