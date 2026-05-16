/* Shadow Network Intelligence — domain types
 * The frontend treats these as the canonical contract surfaced by the
 * existing orchestrator + SSE backend. Mock data conforms to this shape.
 */

export type EntityKind =
  | 'person'
  | 'shell_company'
  | 'company'
  | 'account'
  | 'wallet'
  | 'device'
  | 'address'
  | 'transaction'
  | 'phone'
  | 'document';

export type RiskTier = 'low' | 'medium' | 'high' | 'critical';

export interface Entity {
  id: string;
  label: string;
  kind: EntityKind;
  /** 0 - 100 */
  risk: number;
  tier: RiskTier;
  /** topological importance — drives node sizing */
  importance: number;
  attrs?: Record<string, string | number | boolean>;
  /** ring membership ids if any */
  rings?: string[];
  flags?: string[];
}

export type EdgeKind =
  | 'owns'
  | 'controls'
  | 'transfers'
  | 'shares_device'
  | 'shares_address'
  | 'shares_phone'
  | 'employs'
  | 'authorizes'
  | 'wires_to'
  | 'kyc_match'
  | 'hidden_link';

export interface Edge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind;
  /** 0 - 1 */
  confidence: number;
  /** strength / count */
  weight: number;
  hidden?: boolean;
  meta?: Record<string, string | number | boolean>;
}

export interface Ring {
  id: string;
  name: string;
  members: string[];
  /** structural cohesion 0-1 */
  cohesion: number;
  /** topology signal that surfaced the ring */
  signal: 'closed_cycle' | 'shared_infrastructure' | 'ownership_layering' | 'fan_out';
  risk: RiskTier;
}

export interface HiddenRelationship {
  id: string;
  from: string;
  to: string;
  via: string[];
  reason: string;
  confidence: number;
}

export interface TraversalPath {
  id: string;
  label: string;
  nodes: string[];
  edges: string[];
  /** structural distance (graph hops) */
  hops: number;
  /** explanation of why this path matters */
  why: string;
  intent: 'shortest_path' | 'evidence_chain' | 'reverse_edge' | 'topology_expansion';
}

export interface StructuralSignal {
  id: string;
  name: string;
  description: string;
  intensity: number; // 0-1
  contributors: string[]; // entity ids
}

export interface EvidenceItem {
  id: string;
  /** what this evidences */
  claim: string;
  /** structural source */
  basis: 'edge' | 'ring' | 'path' | 'signal' | 'attribute';
  refs: string[]; // edges, paths, entity ids
  confidence: number;
  timestamp: string;
}

export interface NarrativeBlock {
  headline: string;
  body: string;
  highlights: string[];
}

export interface IntelReport {
  suspects: Entity[];
  hiddenRelationships: HiddenRelationship[];
  rings: Ring[];
  ownershipFlow: TraversalPath[];
  transactionFlows: TraversalPath[];
  sharedInfrastructure: HiddenRelationship[];
  traversalPaths: TraversalPath[];
  structuralSignals: StructuralSignal[];
  evidence: EvidenceItem[];
  narrative: NarrativeBlock;
}

export type StreamEventKind =
  | 'session.start'
  | 'topology.expanded'
  | 'entity.discovered'
  | 'edge.traversed'
  | 'ring.detected'
  | 'hidden.relationship'
  | 'path.discovered'
  | 'suspicion.escalated'
  | 'evidence.collected'
  | 'signal.surfaced'
  | 'report.section'
  | 'session.complete';

export interface StreamEvent {
  id: string;
  kind: StreamEventKind;
  /** logical sequence */
  seq: number;
  /** ISO timestamp */
  at: string;
  /** human-facing single line */
  title: string;
  /** structural payload — depends on kind */
  detail?: string;
  refs?: string[]; // entity / edge / path ids
  severity?: RiskTier;
  /** which section of the 9-part report this contributes to */
  section?: keyof IntelReport;
}

export interface PresetSnapshot {
  id: string;
  label: string;
  description: string;
  tags: string[];
  /** thematic gradient for card */
  tone: 'ice' | 'amber' | 'rose' | 'violet' | 'emerald';
  graph: { entities: Entity[]; edges: Edge[] };
  rings: Ring[];
  hidden: HiddenRelationship[];
  paths: TraversalPath[];
  signals: StructuralSignal[];
  /** the canonical SSE stream this preset replays */
  stream: StreamEvent[];
  /** the final report */
  report: IntelReport;
  /** focus entity id (the prime suspect / seed) */
  seed: string;
  /** benchmark comparison data keyed by method */
  benchmark: BenchmarkComparison;
}

export type BenchmarkMethod = 'pure_llm' | 'vector_rag' | 'graph_rag';

export interface MethodResult {
  method: BenchmarkMethod;
  latencyMs: number;
  tokens: number;
  confidence: number;
  /** structural reasoning depth */
  hops: number;
  /** count of relationships uncovered */
  relationshipsFound: number;
  /** count of MISSED ground-truth relationships */
  relationshipsMissed: number;
  hiddenLinksFound: number;
  ringsDetected: number;
  answer: string;
  /** retrieval trace — what the method consulted */
  trace: string[];
  /** what the method failed to see */
  blindSpots: string[];
}

export interface BenchmarkComparison {
  question: string;
  groundTruth: string;
  results: Record<BenchmarkMethod, MethodResult>;
}

export interface Session {
  id: string;
  presetId: string;
  title: string;
  status: 'queued' | 'streaming' | 'complete' | 'replaying';
  startedAt: string;
  completedAt?: string;
  /** snapshot of events seen so far */
  events: StreamEvent[];
  /** soft progress, 0-1 */
  progress: number;
  /** branch parent */
  parent?: string;
  analyst: string;
}
