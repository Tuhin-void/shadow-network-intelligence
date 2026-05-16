import type { BenchmarkMethod, MethodResult } from '@/types/intel';

/**
 * Forensic metrics — derived from the canonical MethodResult so we don't
 * pollute the preset corpus. Maps each method to plausible operational depth.
 */
export interface ForensicMetrics {
  /** USD estimate */
  cost: number;
  /** total edge traversals during retrieval */
  edgesTraversed: number;
  /** subjective hallucination likelihood (0..1) */
  hallucinationRisk: number;
  /** severity of the worst blind spot (0..1) */
  blindSpotSeverity: number;
  /** how complete the evidence chain is (0..1) */
  evidenceCompleteness: number;
  /** how far confidence propagated across hops (0..1) */
  confidencePropagation: number;
  /** % of preset topology actually visited */
  topologyCoverage: number;
}

export function forensicMetricsFor(
  method: BenchmarkMethod,
  result: MethodResult
): ForensicMetrics {
  const totalRel = result.relationshipsFound + result.relationshipsMissed;
  const recall = totalRel ? result.relationshipsFound / totalRel : 0;
  const blindSeverity =
    result.blindSpots.length === 0
      ? 0
      : Math.min(1, result.blindSpots.length / 5);

  // Method-shaped defaults
  if (method === 'pure_llm') {
    return {
      cost: +(result.tokens / 1000 * 0.012).toFixed(3),
      edgesTraversed: 0,
      hallucinationRisk: 0.45 + (1 - result.confidence) * 0.4,
      blindSpotSeverity: Math.max(0.7, blindSeverity),
      evidenceCompleteness: recall * 0.4,
      confidencePropagation: 0.1,
      topologyCoverage: 0.04,
    };
  }
  if (method === 'vector_rag') {
    return {
      cost: +(result.tokens / 1000 * 0.008 + result.trace.length * 0.0008).toFixed(3),
      edgesTraversed: Math.max(1, result.hops * 2),
      hallucinationRisk: 0.18 + (1 - result.confidence) * 0.25,
      blindSpotSeverity: Math.max(0.45, blindSeverity),
      evidenceCompleteness: recall * 0.55 + 0.10,
      confidencePropagation: 0.32,
      topologyCoverage: 0.18 + recall * 0.18,
    };
  }
  // graph_rag — high coverage, low hallucination, deep traversal
  return {
    cost: +(result.tokens / 1000 * 0.010 + result.hops * 0.0006).toFixed(3),
    edgesTraversed: 6 + result.hops * 6 + result.relationshipsFound * 2,
    hallucinationRisk: Math.max(0.02, 0.08 - result.confidence * 0.06),
    blindSpotSeverity: blindSeverity,
    evidenceCompleteness: 0.94 + recall * 0.06,
    confidencePropagation: 0.86 + result.confidence * 0.10,
    topologyCoverage: 0.92 + Math.min(0.08, recall * 0.08),
  };
}

/**
 * Map a benchmark trace step (a string) into a graph transform.
 *
 * Trace strings are stylized — "shortest_path(...)", "ring_detected(...)",
 * "reverse_edge(...)", "cluster(...)". We parse them and route the user
 * into the appropriate graph operation.
 */
export interface TraceAction {
  kind: 'path' | 'ring' | 'reverse' | 'cluster' | 'fingerprint' | 'address' | 'doc' | 'unknown';
  /** id referenced by the trace (if extractable) */
  ref?: string;
  /** display sub-label */
  sub: string;
}

export function parseTraceStep(step: string): TraceAction {
  const m = step.match(/(shortest_path|ring_detected|reverse_edge|cluster|fingerprint|address_reuse|device_fingerprint|filing-doc|kyc-snippet|kyc-doc|sanc-list-snippet|hosting-doc)\b/i);
  if (!m) return { kind: 'unknown', sub: step };
  const tok = m[1].toLowerCase();
  const refMatch = step.match(/\(([^)]+)\)/);
  const ref = refMatch ? refMatch[1].split(/[\s,→]/)[0] : undefined;

  if (tok.includes('shortest_path')) return { kind: 'path', ref, sub: 'shortest path traversal' };
  if (tok.includes('ring_detected')) return { kind: 'ring', ref, sub: 'ring detection' };
  if (tok.includes('reverse_edge')) return { kind: 'reverse', ref, sub: 'reverse-edge proof' };
  if (tok.includes('cluster')) return { kind: 'cluster', ref, sub: 'clustering' };
  if (tok.includes('fingerprint')) return { kind: 'fingerprint', ref, sub: 'device fingerprint join' };
  if (tok.includes('address')) return { kind: 'address', ref, sub: 'address reuse signal' };
  if (tok.includes('doc') || tok.includes('snippet')) return { kind: 'doc', ref, sub: 'document chunk' };
  return { kind: 'unknown', sub: step };
}
