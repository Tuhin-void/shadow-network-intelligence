# Benchmark reliability report

**Verdict:** `ACCEPTABLE`  •  **Queries:** 5  •  **Trials per query:** 2

- Structural metric drift: **0** (target: 0)
- Latency outliers (>80.0% variance): **2**
- Empty answers: **0** (target: 0)

## Per-query results

| query | t1 ms | t2 ms | ent₁ | ent₂ | nb₁ | nb₂ | ev₁ | ev₂ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `ADV-RING-001` | 7789.0 | 1633.5 | 5 | 5 | 160 | 160 | 5 | 5 |
| `ADV-HIDDEN-002` | 15149.7 | 3585.9 | 5 | 5 | 187 | 187 | 5 | 5 |
| `ADV-COLLUSION-003` | 22636.4 | 4700.2 | 5 | 5 | 145 | 145 | 5 | 5 |
| `ADV-DEVICE-004` | 16191.6 | 2756.4 | 5 | 5 | 244 | 244 | 5 | 5 |
| `ADV-LAYERING-005` | 23038.7 | 3392.5 | 5 | 5 | 265 | 265 | 5 | 5 |

## Issues detected

- ADV-DEVICE-004: latency variance 83.0% > 80.0%
- ADV-LAYERING-005: latency variance 85.3% > 80.0%