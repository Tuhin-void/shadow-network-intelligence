"""
Shadow Network Intelligence - Shared Utilities
Common utility functions
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json

def generate_id(prefix: str = "ID") -> str:
    """Generate a unique ID with prefix"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_val = hashlib.md5(timestamp.encode()).hexdigest()[:6]
    return f"{prefix}_{timestamp}_{hash_val}"

def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"${amount:,.2f}"

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime"""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")

def get_date_range(period: str) -> tuple[datetime, datetime]:
    """Get date range for period string"""
    end = datetime.now()
    
    period_map = {
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365)
    }
    
    delta = period_map.get(period, timedelta(days=30))
    start = end - delta
    
    return start, end

def calculate_risk_score(
    patterns: List[str],
    amounts: List[float],
    transaction_count: int
) -> float:
    """Calculate risk score from various factors"""
    score = 0.0
    
    high_risk_patterns = ["circular", "layered", "structuring", "shell_company"]
    for pattern in patterns:
        if pattern.lower() in high_risk_patterns:
            score += 0.25
    
    if amounts:
        max_amount = max(amounts)
        if max_amount > 100000:
            score += 0.2
        elif max_amount > 50000:
            score += 0.1
    
    if transaction_count > 50:
        score += 0.15
    elif transaction_count > 20:
        score += 0.1
    
    return min(score, 1.0)

def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON with default"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(data: Any) -> str:
    """Safely dump JSON with fallback"""
    try:
        return json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        return "{}"

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [lst[i:i+chunk_size] for i in range(0, len(lst), chunk_size)]

def flatten_dict(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive data showing only last N characters"""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]