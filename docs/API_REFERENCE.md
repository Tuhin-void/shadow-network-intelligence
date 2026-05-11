# Shadow Network Intelligence - API Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <your_token>
```

## Endpoints

### Health
```
GET /health
```
System health check.

**Response:**
```json
{
  "status": "healthy",
  "tigergraph": "connected",
  "llm": "ollama",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Investigations
```
POST /investigate
```
Run fraud investigation.

**Request:**
```json
{
  "query": "Investigate account ACC001 for suspicious activity",
  "entity_id": "ACC001",
  "depth": "standard"
}
```

**Response:**
```json
{
  "investigation_id": "INV_12345",
  "status": "completed",
  "findings": {
    "risk_score": 0.85,
    "risk_level": "HIGH",
    "patterns_detected": ["circular_pattern", "structuring"],
    "evidence": [...]
  },
  "execution_time_ms": 450
}
```

### Alerts
```
GET /alerts?status=open&limit=50
```
List fraud alerts.

**Response:**
```json
{
  "alerts": [
    {
      "id": "ALT_001",
      "type": "LARGE_TRANSFER",
      "severity": "HIGH",
      "entity_id": "ACC001",
      "description": "Transaction exceeds threshold"
    }
  ],
  "total": 1
}
```

### Reports
```
POST /reports/sar
```
Generate SAR report.

**Request:**
```json
{
  "investigation_id": "INV_12345",
  "format": "json"
}
```

### Benchmark
```
POST /benchmark
```
Run benchmark comparison.

**Request:**
```json
{
  "query": "Detect shell company rings",
  "approaches": ["pure_llm", "vector_rag", "graphrag"]
}
```

### Search
```
POST /search
```
Search transaction graph.

**Request:**
```json
{
  "query": "transactions over $10,000",
  "filters": {
    "amount_min": 10000,
    "date_from": "2024-01-01"
  }
}
```

## Error Responses

| Code | Description |
|------|-------------|
| 400 | Invalid request parameters |
| 401 | Missing or invalid authentication |
| 404 | Entity not found |
| 500 | Internal server error |

**Error Format:**
```json
{
  "error": "INVESTIGATION_FAILED",
  "message": "Failed to connect to TigerGraph",
  "details": {}
}
```

## Rate Limits
- `/search`: 100 requests/minute
- `/investigate`: 10 requests/minute
- `/benchmark`: 5 requests/minute