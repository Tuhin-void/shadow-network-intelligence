/**
 * Backend API client — raw transport only.
 *
 * This module knows how to TALK to the orchestrator. It does not know what
 * the responses *mean* — that translation lives in `lib/adapters/`.
 *
 * Base URL is read from `VITE_API_BASE_URL` (defaults to localhost:8000).
 * The orchestrator mounts all routes under `/api/v1` (PATH_PREFIX in the
 * backend's shared/config.py). Both prefix and host are overridable.
 */

const DEFAULT_HOST = 'http://localhost:8000';
const DEFAULT_PREFIX = '/api/v1';

function envHost(): string {
  // Vite exposes import.meta.env at build time; guard for tests / SSR.
  const fromEnv =
    typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL;
  return (fromEnv as string | undefined)?.replace(/\/$/, '') || DEFAULT_HOST;
}

function envPrefix(): string {
  const fromEnv =
    typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_PREFIX;
  const raw = (fromEnv as string | undefined) || DEFAULT_PREFIX;
  return raw.startsWith('/') ? raw : `/${raw}`;
}

export const apiBase = (): string => `${envHost()}${envPrefix()}`;

/* -------------------------------------------------------------------------- */
/* Backend payload contracts — mirror of the Python dataclasses               */
/* (kept loose because they're raw transport — adapters tighten them).        */
/* -------------------------------------------------------------------------- */

export interface BackendOrchestratorStatus {
  offline_mode: boolean;
  session_count: number;
  prewarm: Record<string, unknown> & { warmed?: number; elapsed_s?: number; error?: string };
  cache_hits: number;
  cache_misses: number;
}

export interface BackendPresetSummary {
  key: string;
  title: string;
  showcases: string[];
}

export interface BackendReportEntity {
  v_id: string;
  type: string;
  name: string;
  risk_score?: number | null;
  propagated_risk?: number | null;
  ring_touch_count?: number;
  fraud_degree?: number;
  rerank_reason?: string;
}

export interface BackendReportRelationship {
  source_v_id: string;
  target_v_id: string;
  target_type: string;
  target_name: string;
  edge: string;
  via?: string;
  depth?: number;
}

export interface BackendReportPath {
  from_v_id: string;
  to_v_id: string;
  length: number;
}

export interface BackendReportEvidence {
  id: string;
  type: string;
  strength: number;
  content: string;
  provenance?: Record<string, unknown>;
}

export interface BackendInvestigationReport {
  query: string;
  investigation_id: string;
  session_id: string;
  strategy: string;
  elapsed_ms: number;
  suspects: BackendReportEntity[];
  hidden_relationships: BackendReportRelationship[];
  ring_connections: BackendReportRelationship[];
  ownership_flow: BackendReportRelationship[];
  transaction_flows: BackendReportRelationship[];
  shared_infrastructure: BackendReportRelationship[];
  traversal_paths: BackendReportPath[];
  structural_signals: Record<string, unknown> & {
    entity_count?: number;
    neighbor_count?: number;
    evidence_count?: number;
    strategy?: string;
    ring_touch_sum?: number;
    fraud_degree_sum?: number;
    context_breakdown?: {
      ring_connections?: number;
      ownership_flow?: number;
      transaction_flows?: number;
      shared_infrastructure?: number;
      hidden_relationships?: number;
    };
  };
  evidence_chain: BackendReportEvidence[];
  narrative: string;
}

export interface BackendDemoRunResult {
  preset_key: string;
  preset: { title: string; top_k: number; depth: number; showcases: string[] };
  query: string;
  report: BackendInvestigationReport;
}

export interface BackendStreamEnvelope<P = Record<string, unknown>> {
  kind: string;
  payload: P;
  timestamp_ms: number;
  session_id: string;
  seq: number;
}

/* -------------------------------------------------------------------------- */
/* Fetch wrapper                                                              */
/* -------------------------------------------------------------------------- */

class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string) {
    super(`API ${status}: ${body.slice(0, 240)}`);
    this.status = status;
    this.body = body;
  }
}

async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    ...init,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as T;
}

async function apiPost<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...init,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as T;
}

/* -------------------------------------------------------------------------- */
/* Endpoints                                                                  */
/* -------------------------------------------------------------------------- */

export const api = {
  /** GET /orchestrator/status — backend connectivity probe. */
  async orchestratorStatus(signal?: AbortSignal): Promise<BackendOrchestratorStatus> {
    return apiGet<BackendOrchestratorStatus>('/orchestrator/status', { signal });
  },

  /** POST /orchestrator/reconnect — explicit operator-triggered TG reconnect. */
  async orchestratorReconnect(signal?: AbortSignal): Promise<{ reconnected: boolean; online: boolean }> {
    return apiPost('/orchestrator/reconnect', {}, { signal });
  },

  /** POST /orchestrator/intent — pure-python intent preview, sub-ms. */
  async classifyIntent(query: string, signal?: AbortSignal): Promise<BackendIntent> {
    return apiPost<BackendIntent>('/orchestrator/intent', { query }, { signal });
  },

  /** GET /investigations — disk-backed archive list, newest-first. */
  async listInvestigations(
    opts: { limit?: number; intentKind?: string } = {},
    signal?: AbortSignal,
  ): Promise<BackendInvestigationListing> {
    const params = new URLSearchParams();
    if (opts.limit != null) params.set('limit', String(opts.limit));
    if (opts.intentKind) params.set('intent_kind', opts.intentKind);
    const qs = params.toString();
    return apiGet<BackendInvestigationListing>(`/investigations${qs ? `?${qs}` : ''}`, { signal });
  },

  /** GET /investigations/{id} — full archived record incl. (optional) deep_report. */
  async getInvestigation(
    investigationId: string,
    signal?: AbortSignal,
  ): Promise<BackendArchivedInvestigation> {
    return apiGet(`/investigations/${encodeURIComponent(investigationId)}`, { signal });
  },

  /** DELETE /investigations/{id} */
  async deleteInvestigation(
    investigationId: string,
    signal?: AbortSignal,
  ): Promise<{ ok: boolean }> {
    const res = await fetch(`${apiBase()}/investigations/${encodeURIComponent(investigationId)}`, {
      method: 'DELETE',
      signal,
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as { ok: boolean };
  },

  /** POST /benchmark/ad-hoc — run an analyst query through all 3 pipelines. */
  async runAdHocBenchmark(
    body: { question: string; approaches?: Array<'pure_llm' | 'vector_rag' | 'graph_rag'>; with_scoring?: boolean },
    signal?: AbortSignal,
  ): Promise<BackendBenchmarkRunResult> {
    return apiPost('/benchmark/ad-hoc', body, { signal });
  },

  /** GET /health — fastest possible "is the API process up" check. */
  async health(signal?: AbortSignal): Promise<{ status: string }> {
    return apiGet<{ status: string }>('/health', { signal });
  },

  /** GET /demo/presets — list of curated demo investigations. */
  async listPresets(signal?: AbortSignal): Promise<{ presets: BackendPresetSummary[] }> {
    return apiGet<{ presets: BackendPresetSummary[] }>('/demo/presets', { signal });
  },

  /** POST /demo/run/{key} — synchronous preset investigation. */
  async runDemoPreset(
    key: string,
    body: { session_id?: string } = {},
    signal?: AbortSignal,
  ): Promise<BackendDemoRunResult> {
    return apiPost<BackendDemoRunResult>(`/demo/run/${encodeURIComponent(key)}`, body, { signal });
  },

  /** POST /investigate — synchronous ad-hoc investigation. */
  async runInvestigation(
    body: { query: string; session_id?: string; top_k?: number; depth?: number; strategy?: string },
    signal?: AbortSignal,
  ): Promise<BackendInvestigationReport> {
    return apiPost<BackendInvestigationReport>('/investigate', body, { signal });
  },

  /**
   * POST /investigate/stream — SSE stream of investigation events.
   * Returns an async iterable of parsed envelopes (event-kind + JSON payload).
   */
  streamInvestigation(
    body: { query: string; session_id?: string; top_k?: number; depth?: number; strategy?: string },
    signal?: AbortSignal,
  ): AsyncIterable<BackendStreamEnvelope> {
    return sseStream(`/investigate/stream`, body, signal);
  },

  /** POST /demo/stream/{key} — SSE stream of a curated preset investigation. */
  streamDemoPreset(
    key: string,
    body: { session_id?: string } = {},
    signal?: AbortSignal,
  ): AsyncIterable<BackendStreamEnvelope> {
    return sseStream(`/demo/stream/${encodeURIComponent(key)}`, body, signal);
  },

  /** POST /investigate/deep — synchronous deep investigation. */
  async investigateDeep(
    body: { query: string; session_id?: string; top_k?: number; depth?: number; strategy?: string },
    signal?: AbortSignal,
  ): Promise<Record<string, unknown>> {
    return apiPost<Record<string, unknown>>('/investigate/deep', body, { signal });
  },

  /** POST /demo/deep/{key} — synchronous deep run for a curated preset. */
  async runDemoDeep(
    key: string,
    body: { session_id?: string } = {},
    signal?: AbortSignal,
  ): Promise<Record<string, unknown>> {
    return apiPost<Record<string, unknown>>(`/demo/deep/${encodeURIComponent(key)}`, body, { signal });
  },

  /**
   * POST /investigate/deep/stream — SSE stream of an ad-hoc deep
   * investigation (orchestrator + agent swarm + reasoning), supporting
   * custom natural-language queries from the operator.
   */
  streamInvestigateDeep(
    body: { query: string; session_id?: string; top_k?: number; depth?: number; strategy?: string },
    signal?: AbortSignal,
  ): AsyncIterable<BackendStreamEnvelope> {
    return sseStream('/investigate/deep/stream', body, signal);
  },

  /**
   * GET /benchmark/summary — consolidated real benchmark artifacts.
   * Returns null sections if scripts haven't been run yet.
   */
  async getBenchmarkSummary(signal?: AbortSignal): Promise<{
    adversarial: BackendAdversarialBenchmark | null;
    reliability: BackendReliability | null;
    tigergraph: Record<string, unknown> | null;
    artifacts_present: { adversarial: boolean; reliability: boolean; tigergraph: boolean };
    scripts_to_regenerate: Record<string, string>;
  }> {
    return apiGet('/benchmark/summary', { signal });
  },

  /** GET /benchmark/quantitative — real per-pipeline aggregate metrics. */
  async getQuantitativeBenchmark(signal?: AbortSignal): Promise<BackendQuantitativeBenchmark> {
    return apiGet('/benchmark/quantitative', { signal });
  },

  /** GET /benchmark/service/status — provider config + busy flag. */
  async getBenchmarkServiceStatus(signal?: AbortSignal): Promise<BackendBenchmarkServiceStatus> {
    return apiGet('/benchmark/service/status', { signal });
  },

  /** GET /benchmark/runs — list of persisted run summaries. */
  async listBenchmarkRuns(signal?: AbortSignal): Promise<BackendBenchmarkRunListing> {
    return apiGet('/benchmark/runs', { signal });
  },

  /** GET /benchmark/runs/{run_id} — full run detail + quantitative shape. */
  async getBenchmarkRun(runId: string, signal?: AbortSignal): Promise<BackendBenchmarkRunResult> {
    return apiGet(`/benchmark/runs/${encodeURIComponent(runId)}`, { signal });
  },

  /** POST /benchmark/run — synchronous live benchmark execution. */
  async runBenchmark(
    body: BackendBenchmarkRunRequest = {},
    signal?: AbortSignal,
  ): Promise<BackendBenchmarkRunResult> {
    return apiPost('/benchmark/run', body, { signal });
  },

  /**
   * POST /benchmark/run/stream — SSE stream of run progress. Yields flat
   * event records (the backend emits unwrapped dicts on the wire — each
   * event has its own `kind` and ad-hoc payload fields next to it).
   * Final event is always run.completed | run.error | run.busy.
   */
  async *streamBenchmarkRun(
    body: BackendBenchmarkRunRequest = {},
    signal?: AbortSignal,
  ): AsyncIterable<BackendBenchmarkStreamEvent> {
    for await (const env of sseStream<BackendBenchmarkStreamEvent>('/benchmark/run/stream', body, signal)) {
      // The backend emits a flat dict with `kind` + ad-hoc fields.
      // sseStream wraps that into BackendStreamEnvelope<P>, but the runtime
      // shape is still the original event — narrow it to the flat type.
      yield env as unknown as BackendBenchmarkStreamEvent;
    }
  },

  /* -------- Ingest ----------------------------------------------------- */

  /** POST /ingest/upload — multipart upload of a single CSV. */
  async ingestUpload(file: File, signal?: AbortSignal): Promise<BackendUploadManifest> {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${apiBase()}/ingest/upload`, {
      method: 'POST',
      body: form,
      signal,
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as BackendUploadManifest;
  },

  /** GET /ingest/list — recent uploads. */
  async ingestList(signal?: AbortSignal): Promise<{ uploads: BackendUploadManifest[] }> {
    return apiGet('/ingest/list', { signal });
  },

  /** POST /ingest/promote/{id} — load an upload into TigerGraph. */
  async ingestPromote(uploadId: string, signal?: AbortSignal): Promise<BackendPromotionResult> {
    return apiPost(`/ingest/promote/${encodeURIComponent(uploadId)}`, {}, { signal });
  },

  /** DELETE /ingest/upload/{id} — remove an upload from disk. */
  async ingestDelete(uploadId: string, signal?: AbortSignal): Promise<{ ok: boolean }> {
    const res = await fetch(`${apiBase()}/ingest/upload/${encodeURIComponent(uploadId)}`, {
      method: 'DELETE',
      signal,
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as { ok: boolean };
  },

  /** GET /ingest/schema — supported CSV shapes. */
  async ingestSchema(signal?: AbortSignal): Promise<BackendIngestSchema> {
    return apiGet('/ingest/schema', { signal });
  },

  /** POST /ingest/sample — bulk hydration of the curated benchmark ecosystem. */
  async ingestSample(
    profile: string = 'small',
    signal?: AbortSignal,
  ): Promise<BackendSampleIngestResult> {
    return apiPost(`/ingest/sample?profile=${encodeURIComponent(profile)}`, {}, { signal });
  },

  /** GET /ingest/environment — currently active intelligence environment.
   *  Pass `probe: true` to force a fresh TG round-trip (slower, but
   *  catches "cached online flag is stale" cases). */
  async ingestEnvironment(
    opts: { probe?: boolean } = {},
    signal?: AbortSignal,
  ): Promise<BackendEnvironmentState> {
    const qs = opts.probe ? '?probe=true' : '';
    return apiGet(`/ingest/environment${qs}`, { signal });
  },
};

export interface BackendSampleStage {
  vertex_type: string;
  file: string;
  records: number;
  skipped: number;
  elapsed_s: number;
  tg_response: unknown;
}

export interface BackendSampleIngestResult {
  profile: string;
  csv_dir: string;
  stages: BackendSampleStage[];
  elapsed_s: number;
  vertex_counts: Record<string, number> | null;
  total_records: number;
  total_skipped: number;
}

export interface BackendEnvironmentReadinessSignal {
  ready: boolean;
  reason: string;
}

export interface BackendEnvironmentReadiness {
  graph:     BackendEnvironmentReadinessSignal;
  topology:  BackendEnvironmentReadinessSignal;
  retrieval: BackendEnvironmentReadinessSignal;
  benchmark: BackendEnvironmentReadinessSignal;
  reasoning: BackendEnvironmentReadinessSignal;
}

export interface BackendEnvironmentState {
  tigergraph_online: boolean;
  vertex_counts: Record<string, number>;
  total_vertices: number;
  uploads_total: number;
  uploads_promoted: number;
  supported_profiles: string[];
  /** True when this call triggered a self-heal attempt. */
  reconnect_attempted?: boolean;
  /** True when ?probe=true was honored. */
  fresh_probe?: boolean;
  /** True when a fresh probe was attempted and TG failed. */
  probe_failed?: boolean;
  /** "empty" | "sample" | "uploaded" — what's loaded right now. */
  environment_kind?: 'empty' | 'sample' | 'uploaded' | string;
  /** Composite verdict: every readiness signal is ready. */
  investigation_ready?: boolean;
  /** Per-subsystem readiness — surfaced as the EnvironmentReadinessStrip. */
  readiness?: BackendEnvironmentReadiness;
}

export interface BackendUploadManifest {
  upload_id: string;
  filename: string;
  size_bytes: number;
  row_count: number;
  header: string[];
  preview: string[][];
  uploaded_at: number;
  detected_type: string | null;
  promoted: boolean;
  promotion: null | {
    vertex_type: string;
    records: number;
    skipped: Array<{ line: number; reason: string }>;
    tg_response: unknown;
    elapsed_s: number;
    promoted_at: number;
  };
}

export interface BackendPromotionResult {
  upload_id: string;
  vertex_type: string;
  records: number;
  skipped: number;
  tg_response: unknown;
  elapsed_s: number;
  vertex_counts: Record<string, number> | null;
}

export interface BackendIngestSchema {
  supported: Array<{
    vertex_type: string;
    required: string[];
    optional: string[];
  }>;
  notes: string[];
}

/* -------------------------------------------------------------------------- */
/* Benchmark payload contracts (mirror of the Python JSON)                    */
/* -------------------------------------------------------------------------- */

export interface BackendAdversarialQuery {
  id: string;
  category: string;
  question: string;
  needs_capability: string;
  vectorrag_failure_mode: string;
  graphrag: {
    entities: number;
    neighbors: number;
    evidence: number;
    structural_edges: number;
    ring_touch_sum: number;
    edge_types: string[];
    latency_ms: number;
    answer_preview: string;
  };
  vectorrag_proxy: {
    structural_signal: number;
    keyword_doc_hits: number;
    limitation: string;
  };
  pure_llm: {
    structural_signal: number;
    retrieval: string;
  };
}

export interface BackendAdversarialBenchmark {
  generated_at: number;
  profile: string;
  query_count: number;
  queries: BackendAdversarialQuery[];
  aggregate: {
    queries_with_structural_evidence: number;
    total_neighbors_traversed: number;
    total_structural_edges: number;
    avg_latency_ms: number;
    vectorrag_structural_total: number;
    pure_llm_structural_total: number;
  };
}

export interface BackendReliability {
  status: string;
  queries_run: number;
  trials_per_query: number;
  structural_drift_count: number;
  latency_outlier_count: number;
  empty_answer_count: number;
  latency_tolerance_pct: number;
  issues: string[];
}

export interface BackendPipelineAggregate {
  approach: 'pure_llm' | 'vector_rag' | 'graph_rag' | string;
  queries: number;
  errors?: number;
  avg_total_tokens?: number;
  avg_prompt_tokens?: number;
  avg_completion_tokens?: number;
  avg_latency_ms?: number;          // mock-LLM placeholder
  avg_retrieval_ms?: number;        // REAL retrieval cost
  avg_sources_retrieved?: number;
  total_cost?: number;
  avg_cost?: number;
  token_reduction_pct_vs_heaviest?: number;
  // Scoring aggregates (present only when the run included evaluations).
  n_evaluated?: number;
  avg_judge_overall?: number;
  avg_judge_relevance?: number;
  avg_judge_accuracy?: number;
  avg_judge_completeness?: number;
  avg_judge_hallucination?: number;
  avg_judge_clarity?: number;
  judge_pass_rate?: number;
  hallucination_resistance_rate?: number;
  avg_entity_f1?: number;
  avg_entity_precision?: number;
  avg_entity_recall?: number;
  avg_entity_path_coverage?: number;
  avg_semantic_score?: number;
  avg_accuracy?: number;
  failure_counts?: Record<string, number>;
}

export interface BackendQuantitativeBenchmark {
  run_id: string;
  timestamp: string;
  profile: string;
  config: Record<string, unknown>;
  queries_run: number;
  pipelines: BackendPipelineAggregate[];
  structural: null | {
    queries: number;
    graph_rag: number;
    vector_rag: number;
    pure_llm: number;
    total_structural_edges: number;
    total_neighbors: number;
  };
  scoring?: {
    enabled: boolean;
    semantic_methods: string[];
  };
  disclosure: Record<string, string>;
}

export interface BackendBenchmarkRunRequest {
  approaches?: Array<'pure_llm' | 'vector_rag' | 'graph_rag'>;
  limit?: number;
  tier?: number;
  with_scoring?: boolean;
}

export interface BackendBenchmarkRunSummary {
  run_id: string;
  timestamp: string;
  profile: string;
  queries_run: number;
  approaches: string[];
  has_evaluations: boolean;
  size_bytes: number;
  mtime: number;
}

export interface BackendBenchmarkRunListing {
  runs: BackendBenchmarkRunSummary[];
  directory: string;
  count: number;
}

export interface BackendBenchmarkServiceStatus {
  profile: string;
  providers: Record<string, unknown>;
  runner_initialized: boolean;
  scorer_initialized: boolean;
  semantic_method: string | null;
  busy: boolean;
  last_run_id: string | null;
  last_run_at: number | null;
  max_limit_per_request: number;
}

export interface BackendBenchmarkRunResult {
  /** Full BenchmarkRun.to_dict() — includes raw results, evaluations, queries. */
  run: Record<string, unknown> & {
    run_id: string;
    timestamp: string;
    profile: string;
    queries_run: number;
    results: Record<string, Array<Record<string, unknown>>>;
    evaluations?: Record<string, Array<Record<string, unknown>>>;
    queries?: Array<{
      id: string;
      question: string;
      query_type: string;
      tier: number;
      required_hops: number;
      fraud_ring_id: string | null;
      ground_truth_entities: string[];
    }>;
  };
  quantitative: BackendQuantitativeBenchmark;
}

export interface BackendIntent {
  kind: string;                     // 'rank_suspects' | 'find_ring' | ... | 'unknown'
  display_name: string;
  description: string;
  confidence: number;               // 0..1
  matched_patterns: string[];
  matched_entity_ids: string[];
  strategy_hint: string;
  suggested_workflows: Array<{ kind: string; display_name: string; description: string }>;
  requires_entity_id: boolean;
  operational_hint: string;
}

export interface BackendArchivedInvestigationSummary {
  investigation_id: string;
  session_id: string;
  created_at: number;
  query: string;
  intent_kind: string | null;
  intent_display: string | null;
  intent_confidence: number | null;
  suspect_count: number | null;
  ring_count: number | null;
  neighbor_count: number | null;
  evidence_count: number | null;
  fraud_degree_sum: number | null;
  ring_touch_sum: number | null;
  elapsed_ms: number | null;
  offline_mode: boolean | null;
  has_deep_report: boolean;
  deep_confidence: number | null;
  /** Snapshot fields — vertex total / kind / online at investigation time. */
  env_total_vertices?: number | null;
  env_kind?: string | null;
  env_online?: boolean | null;
  size_bytes: number | null;
}

export interface BackendArchivedInvestigation {
  investigation_id: string;
  session_id: string;
  created_at: number;
  query: string;
  intent: BackendIntent;
  top_k: number;
  depth: number;
  strategy: string;
  elapsed_ms: number;
  offline_mode: boolean;
  cache_hit: boolean;
  report: BackendInvestigationReport & { intent?: BackendIntent };
  deep_report: null | {
    query: string;
    investigation?: unknown;
    swarm?: unknown;
    reasoning?: {
      overall_confidence?: number;
      [k: string]: unknown;
    };
  };
  summary: {
    suspect_count: number;
    ring_count: number;
    evidence_count: number;
    deep_confidence: number | null;
  };
}

export interface BackendInvestigationListing {
  investigations: BackendArchivedInvestigationSummary[];
  stats: { directory: string; count: number; max_entries: number };
}

export interface BackendBenchmarkStreamEvent {
  kind: string;
  // run.started:    { run_id, profile, queries, approaches, scoring }
  // query.completed:{ approach, query_id, question, index, total, result, evaluation? }
  // query.failed:   { approach, query_id, error }
  // run.completed:  { run_id, elapsed_ms, output_file }
  // run.error:      { error, type }
  // run.busy:       { message, last_run_id }
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* SSE — POST-initiated stream parser                                         */
/* (EventSource doesn't support POST, so we read the body via fetch + reader) */
/* -------------------------------------------------------------------------- */

async function* sseStream<P = Record<string, unknown>>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncIterable<BackendStreamEnvelope<P>> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    const text = res.body ? await res.text() : '';
    throw new ApiError(res.status, text || 'no SSE body');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const rawBlock = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const ev = parseSseBlock(rawBlock);
        if (ev) yield ev as BackendStreamEnvelope<P>;
      }
    }
    // Flush any trailing complete block.
    if (buffer.trim()) {
      const ev = parseSseBlock(buffer.trim());
      if (ev) yield ev as BackendStreamEnvelope<P>;
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* noop */
    }
  }
}

function parseSseBlock(block: string): BackendStreamEnvelope | null {
  // SSE block format:  "event: <kind>\ndata: <json>\n\n"
  let kind = '';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) kind = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  const dataStr = dataLines.join('\n');
  let payload: unknown = {};
  try {
    payload = JSON.parse(dataStr);
  } catch {
    return null;
  }
  // Envelope shape from the backend: { kind, payload, timestamp_ms, session_id, seq }
  if (payload && typeof payload === 'object' && 'kind' in (payload as Record<string, unknown>)) {
    return payload as BackendStreamEnvelope;
  }
  return {
    kind: kind || 'unknown',
    payload: (payload ?? {}) as Record<string, unknown>,
    timestamp_ms: Date.now(),
    session_id: '',
    seq: 0,
  };
}

export { ApiError };
