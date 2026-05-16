/**
 * Adapter layer — backend (orchestrator) → frontend (domain types).
 *
 * The backend NEVER bends to the frontend. Every transformation a UI
 * component needs lives in this folder. If a future backend change moves a
 * field, only adapters here are updated — components keep their contracts.
 *
 * Public surface:
 *   - transformOrchestratorStatus(backend)         → ConnectionStatus
 *   - transformBackendPresetList(backend)          → LivePresetSummary[]
 *   - transformBackendStreamEvent(envelope, ctx)   → StreamEvent | null
 *   - transformInvestigationReport(backend, meta)  → IntelReport
 *   - buildSnapshotFromBackendReport(meta, report) → PresetSnapshot (live)
 */

import type {
  BackendInvestigationReport,
  BackendOrchestratorStatus,
  BackendPresetSummary,
  BackendReportEntity,
  BackendReportEvidence,
  BackendReportPath,
  BackendReportRelationship,
  BackendStreamEnvelope,
} from '@/lib/api-client';
import type {
  Edge,
  EdgeKind,
  Entity,
  EntityKind,
  EvidenceItem,
  HiddenRelationship,
  IntelReport,
  NarrativeBlock,
  PresetSnapshot,
  Ring,
  StreamEvent,
  StreamEventKind,
  StructuralSignal,
  TraversalPath,
} from '@/types/intel';
import { clamp, riskToTier } from '@/lib/utils';

/* -------------------------------------------------------------------------- */
/* Connection status                                                          */
/* -------------------------------------------------------------------------- */

export interface ConnectionStatus {
  reachable: boolean;
  /** TigerGraph live vs offline-fallback mode (orchestrator-side flag). */
  tigergraphOffline: boolean;
  prewarm: { warmed: number; elapsedSec?: number; error?: string };
  cache: { hits: number; misses: number; hitRate: number };
  sessionCount: number;
  lastCheckedAt: string;
}

export function transformOrchestratorStatus(
  s: BackendOrchestratorStatus,
): ConnectionStatus {
  const hits = s.cache_hits ?? 0;
  const misses = s.cache_misses ?? 0;
  const total = hits + misses;
  return {
    reachable: true,
    tigergraphOffline: Boolean(s.offline_mode),
    prewarm: {
      warmed: typeof s.prewarm?.warmed === 'number' ? (s.prewarm.warmed as number) : 0,
      elapsedSec:
        typeof s.prewarm?.elapsed_s === 'number' ? (s.prewarm.elapsed_s as number) : undefined,
      error: typeof s.prewarm?.error === 'string' ? (s.prewarm.error as string) : undefined,
    },
    cache: {
      hits,
      misses,
      hitRate: total === 0 ? 0 : hits / total,
    },
    sessionCount: s.session_count ?? 0,
    lastCheckedAt: new Date().toISOString(),
  };
}

/* -------------------------------------------------------------------------- */
/* Preset list                                                                */
/* -------------------------------------------------------------------------- */

export interface LivePresetSummary {
  key: string;
  title: string;
  showcases: string[];
  /** Frontend tone gradient assigned by ordinal — purely cosmetic. */
  tone: PresetSnapshot['tone'];
}

const TONE_CYCLE: PresetSnapshot['tone'][] = [
  'rose',
  'amber',
  'violet',
  'ice',
  'emerald',
  'rose',
  'amber',
  'violet',
];

export function transformBackendPresetList(
  list: BackendPresetSummary[],
): LivePresetSummary[] {
  return list.map((p, i) => ({
    key: p.key,
    title: p.title,
    showcases: p.showcases ?? [],
    tone: TONE_CYCLE[i % TONE_CYCLE.length],
  }));
}

/* -------------------------------------------------------------------------- */
/* Entity / Edge mapping                                                      */
/* -------------------------------------------------------------------------- */

const VTYPE_TO_KIND: Record<string, EntityKind> = {
  Person: 'person',
  PERSON: 'person',
  Company: 'company',
  COMPANY: 'company',
  Account: 'account',
  ACCOUNT: 'account',
  Transaction: 'transaction',
  TRANSACTION: 'transaction',
  Device: 'device',
  DEVICE: 'device',
  Address: 'address',
  ADDRESS: 'address',
  // FraudRing has no direct EntityKind. We represent it as a "shell_company"
  // glyph so it lights up distinctively on the canvas without inventing a new
  // kind. The ring metadata is preserved in `rings` on the report itself.
  FraudRing: 'shell_company',
  FRAUDRING: 'shell_company',
};

function backendTypeToKind(t: string | undefined): EntityKind {
  if (!t) return 'person';
  return VTYPE_TO_KIND[t] ?? VTYPE_TO_KIND[t.toUpperCase()] ?? 'person';
}

/**
 * Backend risk_score comes as 0..1 (commonly) or 0..100 (rarely). Detect
 * which and normalize to 0..100 for the frontend.
 */
function normalizeRisk(raw: number | null | undefined, fallback: number): number {
  if (raw == null || Number.isNaN(raw)) return fallback;
  if (raw <= 1) return clamp(Math.round(raw * 100), 0, 100);
  return clamp(Math.round(raw), 0, 100);
}

function riskForSuspect(e: BackendReportEntity): number {
  // Heuristic: blend declared risk with topology-derived intensity. Both
  // ring_touch_count and fraud_degree express structural prominence.
  const base = normalizeRisk(e.risk_score ?? e.propagated_risk ?? null, 50);
  const ringBoost = Math.min(40, (e.ring_touch_count ?? 0) * 18);
  const degreeBoost = Math.min(20, (e.fraud_degree ?? 0) * 2);
  return clamp(Math.round(base * 0.55 + ringBoost + degreeBoost), 0, 100);
}

function importanceForSuspect(e: BackendReportEntity): number {
  // Map fraud_degree + ring_touch onto the 3..10 sizing scale.
  const raw = 3 + Math.min(7, (e.fraud_degree ?? 0) * 1.2 + (e.ring_touch_count ?? 0) * 2);
  return Math.round(raw);
}

export function transformBackendEntity(e: BackendReportEntity): Entity {
  const risk = riskForSuspect(e);
  const flags: string[] = [];
  if (e.rerank_reason) flags.push(e.rerank_reason);
  if ((e.ring_touch_count ?? 0) > 0) flags.push(`ring-touch:${e.ring_touch_count}`);
  if ((e.fraud_degree ?? 0) > 0) flags.push(`fraud-degree:${e.fraud_degree}`);
  return {
    id: e.v_id,
    label: e.name || e.v_id,
    kind: backendTypeToKind(e.type),
    risk,
    tier: riskToTier(risk),
    importance: importanceForSuspect(e),
    attrs: {
      backendType: e.type,
      backendRisk: e.risk_score ?? 0,
      ringTouch: e.ring_touch_count ?? 0,
      fraudDegree: e.fraud_degree ?? 0,
      rerankReason: e.rerank_reason ?? '',
    },
    flags,
  };
}

/**
 * Synthesize a "stub" Entity from a relationship's target. Used because the
 * backend only fully describes seed entities in `suspects` — the targets
 * surfaced via traversal need lightweight representations to render.
 */
function entityStubFromRelationship(r: BackendReportRelationship): Entity {
  const kind = backendTypeToKind(r.target_type);
  // Default to medium risk for non-seed neighbors — they're context, not
  // prime suspects. Topology elevates them visually anyway.
  return {
    id: r.target_v_id,
    label: r.target_name || r.target_v_id,
    kind,
    risk: 40,
    tier: 'medium',
    importance: 4,
    attrs: { backendType: r.target_type, stub: true },
  };
}

const EDGE_TO_KIND: Record<string, EdgeKind> = {
  OWNS: 'owns',
  BENEFITS_FROM: 'controls',
  HAS_ACCOUNT: 'owns',
  TRANSFERRED_TO: 'transfers',
  SENT_TRANSACTION: 'transfers',
  RECEIVED_TRANSACTION: 'transfers',
  LOCATED_AT: 'shares_address',
  REGISTERED_AT: 'shares_address',
  USES_DEVICE: 'shares_device',
  SHARES_DEVICE_WITH: 'shares_device',
  SHARES_ADDRESS_WITH: 'shares_address',
  ASSOCIATED_WITH: 'kyc_match',
  ACCESSED_FROM: 'shares_device',
  PERSON_MEMBER_OF_RING: 'controls',
  COMPANY_MEMBER_OF_RING: 'controls',
  ACCOUNT_MEMBER_OF_RING: 'controls',
  TRANSACTION_MEMBER_OF_RING: 'controls',
  DEVICE_CONNECTED_TO_RING: 'controls',
  ADDRESS_CONNECTED_TO_RING: 'controls',
};

function backendEdgeToKind(e: string): EdgeKind {
  return EDGE_TO_KIND[e?.toUpperCase?.() ?? e] ?? 'hidden_link';
}

let _edgeCounter = 0;
function edgeId(r: BackendReportRelationship): string {
  return `live_e_${r.source_v_id}_${r.target_v_id}_${r.edge}_${++_edgeCounter}`;
}

export function transformBackendRelationship(r: BackendReportRelationship): Edge {
  const kind = backendEdgeToKind(r.edge);
  return {
    id: edgeId(r),
    source: r.source_v_id || r.via || r.target_v_id,
    target: r.target_v_id,
    kind,
    confidence: 0.85,
    weight: 3 + (r.depth ?? 1),
    hidden: kind === 'hidden_link',
    meta: {
      backendEdge: r.edge,
      via: r.via ?? '',
      depth: r.depth ?? 1,
    },
  };
}

function relationshipToHidden(r: BackendReportRelationship, index: number): HiddenRelationship {
  return {
    id: `live_h_${r.source_v_id}_${r.target_v_id}_${index}`,
    from: r.source_v_id || r.via || r.target_v_id,
    to: r.target_v_id,
    via: r.via ? [r.via] : [],
    reason: humanizeEdge(r.edge),
    confidence: 0.78,
  };
}

function humanizeEdge(edge: string): string {
  if (!edge) return 'structural link';
  return edge.toLowerCase().replace(/_/g, ' ');
}

/* -------------------------------------------------------------------------- */
/* Rings                                                                      */
/* -------------------------------------------------------------------------- */

/**
 * Group ring_connections by their `via` field (the FR-XXX id) into Ring
 * entries. Topology surfacing — the ring itself is the structural signal.
 */
export function ringsFromReport(report: BackendInvestigationReport): Ring[] {
  const byRing = new Map<string, Set<string>>();
  for (const r of report.ring_connections ?? []) {
    const id = r.via && r.via.startsWith('FR-') ? r.via : ringIdFromEntity(r);
    if (!id) continue;
    if (!byRing.has(id)) byRing.set(id, new Set());
    const set = byRing.get(id)!;
    // The non-FR side of the edge is the ring member.
    const member = r.source_v_id?.startsWith('FR-') ? r.target_v_id : r.source_v_id;
    if (member && !member.startsWith('FR-')) set.add(member);
  }
  // Also harvest from suspects' attrs (ring_touch > 0 + rerank_reason "member of ring FR-XXX")
  for (const s of report.suspects ?? []) {
    const m = /member of ring (FR-\w+)/i.exec(s.rerank_reason ?? '');
    if (m) {
      const id = m[1];
      if (!byRing.has(id)) byRing.set(id, new Set());
      byRing.get(id)!.add(s.v_id);
    }
  }
  return [...byRing.entries()].map(([id, members]) => ({
    id,
    name: id,
    members: [...members],
    cohesion: clamp(members.size / 8, 0.2, 0.95),
    signal: 'closed_cycle',
    risk: members.size >= 6 ? 'critical' : members.size >= 3 ? 'high' : 'medium',
  }));
}

function ringIdFromEntity(r: BackendReportRelationship): string | null {
  if (r.source_v_id?.startsWith('FR-')) return r.source_v_id;
  if (r.target_v_id?.startsWith('FR-')) return r.target_v_id;
  return null;
}

/* -------------------------------------------------------------------------- */
/* Paths                                                                      */
/* -------------------------------------------------------------------------- */

export function transformBackendPath(p: BackendReportPath, i: number): TraversalPath {
  return {
    id: `live_path_${i}_${p.from_v_id}_${p.to_v_id}`,
    label: `${p.from_v_id} → ${p.to_v_id}`,
    nodes: [p.from_v_id, p.to_v_id],
    edges: [],
    hops: p.length ?? 1,
    why: `Shortest structural path · ${p.length ?? 1} hop${(p.length ?? 1) === 1 ? '' : 's'}`,
    intent: 'shortest_path',
  };
}

/**
 * Turn ownership / transaction relationships into 2-node TraversalPath
 * entries so they render in the existing PathList component.
 */
function relationshipsToPaths(
  rels: BackendReportRelationship[],
  intent: TraversalPath['intent'],
  labelPrefix: string,
): TraversalPath[] {
  return rels.map((r, i) => ({
    id: `live_${intent}_${i}_${r.source_v_id}_${r.target_v_id}`,
    label: `${labelPrefix}: ${r.source_v_id} → ${r.target_name || r.target_v_id}`,
    nodes: [r.source_v_id || r.via || r.target_v_id, r.target_v_id],
    edges: [],
    hops: r.depth ?? 1,
    why: humanizeEdge(r.edge),
    intent,
  }));
}

/* -------------------------------------------------------------------------- */
/* Evidence                                                                   */
/* -------------------------------------------------------------------------- */

export function transformBackendEvidence(e: BackendReportEvidence): EvidenceItem {
  return {
    id: e.id || `live_ev_${Math.random().toString(36).slice(2, 9)}`,
    claim: e.content,
    basis: basisForBackendType(e.type),
    refs: refsFromProvenance(e.provenance),
    confidence: clamp(e.strength ?? 0.7, 0, 1),
    timestamp: new Date().toISOString(),
  };
}

function basisForBackendType(t: string): EvidenceItem['basis'] {
  const s = (t || '').toLowerCase();
  if (s.includes('ring')) return 'ring';
  if (s.includes('path')) return 'path';
  if (s.includes('signal')) return 'signal';
  if (s.includes('relationship') || s.includes('edge')) return 'edge';
  return 'attribute';
}

function refsFromProvenance(prov: Record<string, unknown> | undefined): string[] {
  if (!prov) return [];
  const out: string[] = [];
  for (const v of Object.values(prov)) {
    if (typeof v === 'string') out.push(v);
    else if (Array.isArray(v)) v.forEach((x) => typeof x === 'string' && out.push(x));
  }
  return out.slice(0, 6);
}

/* -------------------------------------------------------------------------- */
/* Structural signals                                                         */
/* -------------------------------------------------------------------------- */

export function structuralSignalsFromReport(
  report: BackendInvestigationReport,
): StructuralSignal[] {
  const s = report.structural_signals ?? {};
  const cb = (s.context_breakdown ?? {}) as Record<string, number>;
  const signals: StructuralSignal[] = [];

  const ringTouch = (s.ring_touch_sum ?? 0) as number;
  if (ringTouch > 0) {
    signals.push({
      id: 'sig_ring_touch',
      name: 'Ring proximity',
      description: `${ringTouch} ring-membership ties surfaced across suspects.`,
      intensity: clamp(ringTouch / 8, 0.15, 1),
      contributors: (report.suspects ?? [])
        .filter((s) => (s.ring_touch_count ?? 0) > 0)
        .map((s) => s.v_id),
    });
  }

  const fraudDegree = (s.fraud_degree_sum ?? 0) as number;
  if (fraudDegree > 0) {
    signals.push({
      id: 'sig_fraud_degree',
      name: 'Fraud-relevant degree',
      description: `Suspects sit on ${fraudDegree} fraud-relevant edges in aggregate.`,
      intensity: clamp(fraudDegree / 24, 0.2, 1),
      contributors: (report.suspects ?? [])
        .filter((s) => (s.fraud_degree ?? 0) > 0)
        .map((s) => s.v_id),
    });
  }

  const neighborCount = (s.neighbor_count ?? 0) as number;
  if (neighborCount > 0) {
    signals.push({
      id: 'sig_neighborhood',
      name: 'Neighborhood expansion',
      description: `${neighborCount} structural neighbors traversed for context.`,
      intensity: clamp(neighborCount / 240, 0.1, 1),
      contributors: [],
    });
  }

  const hidden = cb.hidden_relationships ?? 0;
  if (hidden > 0) {
    signals.push({
      id: 'sig_hidden',
      name: 'Hidden-relationship surfacing',
      description: `${hidden} non-obvious link types surfaced via topology.`,
      intensity: clamp(hidden / 12, 0.2, 1),
      contributors: [],
    });
  }

  return signals;
}

/* -------------------------------------------------------------------------- */
/* Narrative                                                                  */
/* -------------------------------------------------------------------------- */

export function narrativeFromReport(report: BackendInvestigationReport): NarrativeBlock {
  const narr = (report.narrative || '').trim();
  // Headline = first non-empty line, body = the rest.
  const lines = narr.split(/\n+/).filter((l) => l.trim());
  const headline = lines[0] || `Investigation ${report.investigation_id}`;
  const body = lines.slice(1).join(' ') || `Strategy: ${report.strategy || 'auto'}.`;
  // Highlights = top 5 suspect rerank-reasons, deduped.
  const highlights = uniq(
    (report.suspects ?? [])
      .map((s) => s.rerank_reason)
      .filter((s): s is string => Boolean(s))
      .slice(0, 5),
  );
  return { headline, body, highlights };
}

function uniq<T>(xs: T[]): T[] {
  return [...new Set(xs)];
}

/* -------------------------------------------------------------------------- */
/* Full report transform                                                      */
/* -------------------------------------------------------------------------- */

export function transformInvestigationReport(
  report: BackendInvestigationReport,
): IntelReport {
  const suspects = (report.suspects ?? []).map(transformBackendEntity);
  const hiddenRels = (report.hidden_relationships ?? []).map(relationshipToHidden);
  const sharedInfra = (report.shared_infrastructure ?? []).map(relationshipToHidden);
  const ownershipPaths = relationshipsToPaths(
    report.ownership_flow ?? [],
    'evidence_chain',
    'OWNS',
  );
  const txPaths = relationshipsToPaths(
    report.transaction_flows ?? [],
    'evidence_chain',
    'TX',
  );
  const traversal = (report.traversal_paths ?? []).map(transformBackendPath);

  return {
    suspects,
    hiddenRelationships: hiddenRels,
    rings: ringsFromReport(report),
    ownershipFlow: ownershipPaths,
    transactionFlows: txPaths,
    sharedInfrastructure: sharedInfra,
    traversalPaths: traversal,
    structuralSignals: structuralSignalsFromReport(report),
    evidence: (report.evidence_chain ?? []).map(transformBackendEvidence),
    narrative: narrativeFromReport(report),
  };
}

/* -------------------------------------------------------------------------- */
/* Synthetic PresetSnapshot from a live report                                */
/* -------------------------------------------------------------------------- */

/**
 * Build a complete PresetSnapshot from a live backend report so it can be
 * dropped into the existing intel-store flow with zero special-casing.
 *
 * The graph is materialized from suspects + every relationship target; edges
 * are reified from all relationship buckets.
 */
export function buildSnapshotFromBackendReport(
  meta: { key: string; title: string; tone: PresetSnapshot['tone'] },
  report: BackendInvestigationReport,
): PresetSnapshot {
  const intelReport = transformInvestigationReport(report);

  // Materialize all entities: suspects (rich) + stubs for everything else
  // referenced by relationships. Dedupe by id, prefer suspect-shaped entry.
  const entities = new Map<string, Entity>();
  intelReport.suspects.forEach((s) => entities.set(s.id, s));

  const allRels: BackendReportRelationship[] = [
    ...(report.hidden_relationships ?? []),
    ...(report.ring_connections ?? []),
    ...(report.ownership_flow ?? []),
    ...(report.transaction_flows ?? []),
    ...(report.shared_infrastructure ?? []),
  ];

  const edges: Edge[] = [];
  for (const r of allRels) {
    if (r.source_v_id && !entities.has(r.source_v_id)) {
      entities.set(r.source_v_id, {
        id: r.source_v_id,
        label: r.source_v_id,
        kind: r.source_v_id.startsWith('FR-') ? 'shell_company' : 'person',
        risk: 45,
        tier: 'medium',
        importance: 3,
        attrs: { stub: true },
      });
    }
    if (r.target_v_id && !entities.has(r.target_v_id)) {
      entities.set(r.target_v_id, entityStubFromRelationship(r));
    }
    edges.push(transformBackendRelationship(r));
  }

  const seed = intelReport.suspects[0]?.id ?? [...entities.keys()][0] ?? 'unknown';

  return {
    id: `live_${meta.key}`,
    label: meta.title,
    description: intelReport.narrative.headline,
    tags: ['live', 'graphrag', 'tigergraph'],
    tone: meta.tone,
    graph: { entities: [...entities.values()], edges },
    rings: intelReport.rings,
    hidden: [...intelReport.hiddenRelationships, ...intelReport.sharedInfrastructure],
    paths: [
      ...intelReport.traversalPaths,
      ...intelReport.ownershipFlow,
      ...intelReport.transactionFlows,
    ],
    signals: intelReport.structuralSignals,
    stream: [], // Live stream is produced incrementally — not pre-canned.
    report: intelReport,
    seed,
    // The live preset doesn't have a 3-way benchmark comparison; downstream
    // benchmark UI keeps using its mock preset corpus. This is intentional.
    benchmark: {
      question: report.query,
      groundTruth: 'Live investigation (no benchmark counterparts)',
      results: {} as PresetSnapshot['benchmark']['results'],
    },
  };
}

/* -------------------------------------------------------------------------- */
/* Stream-event adapter                                                       */
/* -------------------------------------------------------------------------- */

export interface StreamAdapterContext {
  /** sequence offset so adapted events have a monotonic .seq */
  seqOffset?: number;
}

/**
 * Maps a backend SSE envelope into a frontend StreamEvent. Some backend
 * event kinds collapse to the closest frontend kind; rare housekeeping
 * events (prewarm.done, query.received) are surfaced as 'session.start'
 * variants so the timeline stays informative.
 */
export function transformBackendStreamEvent(
  env: BackendStreamEnvelope,
  ctx: StreamAdapterContext = {},
): StreamEvent | null {
  const kind = mapEventKind(env.kind);
  if (!kind) return null;
  const seq = env.seq + (ctx.seqOffset ?? 0);
  const id = `live_ev_${env.session_id || 'anon'}_${env.seq}_${Math.random().toString(36).slice(2, 6)}`;
  const at = new Date(env.timestamp_ms || Date.now()).toISOString();
  const { title, detail, refs, severity, section } = describeEvent(env);
  return { id, kind, seq, at, title, detail, refs, severity, section };
}

const EVENT_KIND_MAP: Record<string, StreamEventKind | null> = {
  'session.started': 'session.start',
  'query.received': 'session.start',
  'prewarm.done': 'session.start',
  'entity.found': 'entity.discovered',
  'neighborhood.expanded': 'topology.expanded',
  'ring.discovered': 'ring.detected',
  'hidden_relationship.found': 'hidden.relationship',
  'traversal.path': 'path.discovered',
  'ring.member_promoted': 'suspicion.escalated',
  'evidence.collected': 'evidence.collected',
  'report.finalized': 'session.complete',
  'error': null,
};

function mapEventKind(k: string): StreamEventKind | null {
  if (k in EVENT_KIND_MAP) return EVENT_KIND_MAP[k];
  return null;
}

function describeEvent(env: BackendStreamEnvelope): {
  title: string;
  detail?: string;
  refs?: string[];
  severity?: StreamEvent['severity'];
  section?: StreamEvent['section'];
} {
  const p = env.payload ?? {};
  switch (env.kind) {
    case 'session.started':
      return {
        title: 'Session opened',
        detail: `Investigation ${(p as any).investigation_id ?? '—'}`,
      };
    case 'query.received':
      return {
        title: 'Query accepted',
        detail: String((p as any).query ?? '').slice(0, 120),
      };
    case 'prewarm.done':
      return {
        title: 'Cache prewarm complete',
        detail: `${(p as any).warmed ?? 0} entities warmed`,
      };
    case 'entity.found': {
      const name = (p as any).name ?? (p as any).v_id ?? 'entity';
      const reason = (p as any).rerank_reason ?? '';
      return {
        title: `Surfaced ${name}`,
        detail: reason || undefined,
        refs: [(p as any).v_id].filter(Boolean),
        section: 'suspects',
      };
    }
    case 'neighborhood.expanded':
      return {
        title: 'Neighborhood expanded',
        detail: `${(p as any).neighbor_count ?? 0} neighbors traversed`,
      };
    case 'ring.discovered': {
      const via = (p as any).via ?? [];
      return {
        title: `Ring connections surfaced`,
        detail: `${(p as any).edge_count ?? 0} ring edges via ${via.join(', ') || 'topology'}`,
        section: 'rings',
        severity: 'high',
      };
    }
    case 'hidden_relationship.found':
      return {
        title: 'Hidden relationships surfaced',
        detail: `${(p as any).count ?? 0} non-obvious ties`,
        section: 'hiddenRelationships',
        severity: 'high',
      };
    case 'traversal.path':
      return {
        title: 'Traversal path',
        detail: `${(p as any).from ?? ''} → ${(p as any).to ?? ''} · ${(p as any).length ?? 0} hops`,
        section: 'traversalPaths',
      };
    case 'ring.member_promoted':
      return {
        title: 'Ring members promoted',
        detail: `${(p as any).count ?? 0} entities elevated by ring proximity`,
        refs: ((p as any).promoted_ids ?? []) as string[],
        severity: 'critical',
        section: 'suspects',
      };
    case 'evidence.collected':
      return {
        title: 'Evidence collected',
        detail: `${(p as any).count ?? 0} structural references`,
        section: 'evidence',
      };
    case 'report.finalized':
      return {
        title: 'Investigation complete',
        detail: 'Structured report ready',
        section: 'evidence',
      };
    default:
      return { title: env.kind };
  }
}
