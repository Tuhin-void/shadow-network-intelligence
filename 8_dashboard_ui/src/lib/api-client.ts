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
};

/* -------------------------------------------------------------------------- */
/* SSE — POST-initiated stream parser                                         */
/* (EventSource doesn't support POST, so we read the body via fetch + reader) */
/* -------------------------------------------------------------------------- */

async function* sseStream(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncIterable<BackendStreamEnvelope> {
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
        if (ev) yield ev;
      }
    }
    // Flush any trailing complete block.
    if (buffer.trim()) {
      const ev = parseSseBlock(buffer.trim());
      if (ev) yield ev;
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
