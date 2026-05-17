# Benchmark reliability report

**Verdict:** `STABLE`  •  **Queries:** 5  •  **Trials per query:** 2

- Structural metric drift: **0** (target: 0)
- Latency outliers (>90.0% variance): **0**
- Empty answers: **0** (target: 0)

## Per-query results

| query | t1 ms | t2 ms | ent₁ | ent₂ | nb₁ | nb₂ | ev₁ | ev₂ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `ADV-RING-001` | 8207.6 | 1419.0 | 5 | 5 | 160 | 160 | 5 | 5 |
| `ADV-HIDDEN-002` | 17508.8 | 4812.3 | 5 | 5 | 187 | 187 | 5 | 5 |
| `ADV-COLLUSION-003` | 22332.5 | 4838.1 | 5 | 5 | 145 | 145 | 5 | 5 |
| `ADV-DEVICE-004` | 15939.6 | 2095.3 | 5 | 5 | 244 | 244 | 5 | 5 |
| `ADV-LAYERING-005` | 23725.9 | 3677.4 | 5 | 5 | 265 | 265 | 5 | 5 |