/**
 * Cognitive adapter — backend deep-investigation response → frontend
 * CognitiveReport shape.
 *
 * Backend endpoint: POST /api/v1/investigate/deep   (returns a combined
 * structure with `investigation`, `swarm`, `reasoning`, `metadata`)
 *
 * Frontend consumers (CognitivePanel, intel-store) only ever see the
 * normalized CognitiveReport from this file.
 */

import type { BackendInvestigationReport } from '@/lib/api-client';

/* -------------------------------------------------------------------------- */
/* Raw backend shapes                                                         */
/* -------------------------------------------------------------------------- */

export interface BackendAgentFinding {
  agent: string;
  summary: string;
  confidence: number;
  findings: unknown[];
  metrics: Record<string, unknown>;
  notes?: string[];
}

export interface BackendSwarmReport {
  query: string;
  investigation_id: string;
  elapsed_ms: number;
  agents: BackendAgentFinding[];
  coordinator_summary: string;
  consolidated_metrics: Record<string, unknown>;
}

export interface BackendClaim {
  statement: string;
  basis: string;
  confidence: number;
  refs: string[];
}

export interface BackendContradiction {
  a: BackendClaim;
  b: BackendClaim;
  reason: string;
}

export interface BackendReasoning {
  query: string;
  overall_confidence: number;
  headline: string;
  body: string;
  key_claims: BackendClaim[];
  contradictions: BackendContradiction[];
  explanations: Record<string, string>;
}

export interface BackendDeepReport {
  query: string;
  elapsed_ms: number;
  investigation: BackendInvestigationReport;
  swarm: BackendSwarmReport;
  reasoning: BackendReasoning;
  metadata: {
    engine_cache_hit?: boolean;
    agent_count?: number;
    claim_count?: number;
    contradiction_count?: number;
    overall_confidence?: number;
  };
}

/* -------------------------------------------------------------------------- */
/* Normalized frontend shape                                                  */
/* -------------------------------------------------------------------------- */

export type ClaimBasis = 'ring' | 'ownership' | 'flow' | 'infra' | 'other';

export interface CognitiveClaim {
  statement: string;
  basis: ClaimBasis;
  confidence: number;
  refs: string[];
}

export interface CognitiveAgent {
  /** stable id for keys + style mapping */
  id: string;
  /** display name */
  label: string;
  summary: string;
  confidence: number;
  notes: string[];
  /** flat key/value metrics for the agent — rendered as a chip list */
  metrics: Array<{ key: string; value: string }>;
}

export interface CognitiveContradiction {
  reason: string;
  claimA: string;
  claimB: string;
}

export interface CognitiveReport {
  query: string;
  elapsedMs: number;
  cacheHit: boolean;
  /** 0..1 — grounded in real graph evidence */
  overallConfidence: number;
  headline: string;
  body: string;
  agents: CognitiveAgent[];
  claims: CognitiveClaim[];
  contradictions: CognitiveContradiction[];
  /** v_id → why-this-entity rationale */
  explanations: Record<string, string>;
  /** Counts breakdown for status chips */
  counts: {
    agents: number;
    claims: number;
    contradictions: number;
    explanations: number;
    suspects: number;
    structuralEdges: number;
  };
}

/* -------------------------------------------------------------------------- */
/* Display mapping                                                            */
/* -------------------------------------------------------------------------- */

const AGENT_LABEL: Record<string, string> = {
  retrieval_analyst: 'Retrieval Analyst',
  graph_topology_investigator: 'Graph Topology Investigator',
  sanctions_exposure_tracer: 'Sanctions Exposure Tracer',
  fraud_ring_analyst: 'Fraud Ring Analyst',
  synthesis_coordinator: 'Synthesis Coordinator',
};

function _safeBasis(b: string): ClaimBasis {
  switch (b) {
    case 'ring':
    case 'ownership':
    case 'flow':
    case 'infra':
      return b;
    default:
      return 'other';
  }
}

function _flattenMetrics(
  m: Record<string, unknown>,
): Array<{ key: string; value: string }> {
  if (!m) return [];
  return Object.entries(m).map(([k, v]) => ({
    key: k,
    value:
      typeof v === 'object' && v !== null
        ? JSON.stringify(v).slice(0, 60)
        : String(v),
  }));
}

/* -------------------------------------------------------------------------- */
/* Public transform                                                           */
/* -------------------------------------------------------------------------- */

export function transformDeepReport(d: BackendDeepReport): CognitiveReport {
  const agents: CognitiveAgent[] = (d.swarm?.agents ?? []).map((a) => ({
    id: a.agent,
    label: AGENT_LABEL[a.agent] ?? a.agent,
    summary: a.summary || '',
    confidence: clamp(a.confidence ?? 0, 0, 1),
    notes: a.notes ?? [],
    metrics: _flattenMetrics(a.metrics ?? {}),
  }));

  const claims: CognitiveClaim[] = (d.reasoning?.key_claims ?? []).map((c) => ({
    statement: c.statement,
    basis: _safeBasis(c.basis),
    confidence: clamp(c.confidence ?? 0, 0, 1),
    refs: c.refs ?? [],
  }));

  const contradictions: CognitiveContradiction[] = (
    d.reasoning?.contradictions ?? []
  ).map((x) => ({
    reason: x.reason,
    claimA: x.a?.statement ?? '',
    claimB: x.b?.statement ?? '',
  }));

  const suspectCount = d.investigation?.suspects?.length ?? 0;
  const structEdges = Number(
    d.investigation?.structural_signals?.context_breakdown?.ring_connections ?? 0,
  ) + Number(
    d.investigation?.structural_signals?.context_breakdown?.ownership_flow ?? 0,
  ) + Number(
    d.investigation?.structural_signals?.context_breakdown?.transaction_flows ?? 0,
  ) + Number(
    d.investigation?.structural_signals?.context_breakdown?.shared_infrastructure ?? 0,
  );

  return {
    query: d.query ?? '',
    elapsedMs: d.elapsed_ms ?? 0,
    cacheHit: Boolean(d.metadata?.engine_cache_hit),
    overallConfidence: clamp(d.reasoning?.overall_confidence ?? 0, 0, 1),
    headline: d.reasoning?.headline ?? '',
    body: d.reasoning?.body ?? '',
    agents,
    claims,
    contradictions,
    explanations: d.reasoning?.explanations ?? {},
    counts: {
      agents: agents.length,
      claims: claims.length,
      contradictions: contradictions.length,
      explanations: Object.keys(d.reasoning?.explanations ?? {}).length,
      suspects: suspectCount,
      structuralEdges: structEdges,
    },
  };
}

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}
