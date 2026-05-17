import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Archive,
  Brain,
  CheckCircle2,
  Clock,
  Compass,
  Layers,
  Loader2,
  Network,
  RefreshCw,
  ShieldAlert,
  Target,
  Trash2,
  Zap,
} from 'lucide-react';
import { api } from '@/lib/api-client';
import type {
  BackendArchivedInvestigationSummary,
  BackendEnvironmentState,
} from '@/lib/api-client';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';

/**
 * RecentInvestigationsPanel — disk-backed archive of every investigation
 * the orchestrator has run. Replaces the in-memory `customQueryHistory`
 * strip with a real operational archive.
 *
 * Each row carries the SAME structural signals that the InvestigationReport
 * exposes — suspect count, ring count, neighbor count, evidence count,
 * elapsed ms, intent kind, has_deep_report. Clicking a row replays the
 * investigation by re-running the original query through GraphRAG (the
 * cache returns it instantly on warm hit).
 */
export function RecentInvestigationsPanel({ limit = 12 }: { limit?: number }) {
  const navigate = useNavigate();
  const runCustomDeep = useIntelStore((s) => s.runCustomDeepStream);
  const cognitivePhase = useIntelStore((s) => s.cognitivePhase);
  const liveStreamPhase = useIntelStore((s) => s.liveStreamPhase);

  const [rows, setRows] = useState<BackendArchivedInvestigationSummary[]>([]);
  const [phase, setPhase] = useState<'loading' | 'ready' | 'error' | 'empty'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [intentFilter, setIntentFilter] = useState<string | null>(null);
  // Live environment total — used to flag rows whose captured graph state
  // differs from the current one so the analyst knows a replay would run
  // against a changed graph. Refreshed lazily.
  const [liveEnv, setLiveEnv] = useState<BackendEnvironmentState | null>(null);

  const isRunning = cognitivePhase === 'running' || liveStreamPhase === 'streaming';

  const load = async () => {
    setPhase('loading');
    setError(null);
    try {
      const [r, env] = await Promise.all([
        api.listInvestigations({ limit, intentKind: intentFilter ?? undefined }),
        api.ingestEnvironment().catch(() => null),
      ]);
      setRows(r.investigations);
      setLiveEnv(env);
      setPhase(r.investigations.length === 0 ? 'empty' : 'ready');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  };

  useEffect(() => {
    load();
    // Poll lightly so newly-completed investigations show up without manual reload.
    const id = setInterval(load, 12_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit, intentFilter]);

  // Distinct intent kinds present in the current archive — used to populate
  // the filter pills. Only shown when there's at least 2 kinds.
  const intentKinds = Array.from(
    new Set(rows.map((r) => r.intent_kind).filter((k): k is string => !!k)),
  );

  const replay = async (row: BackendArchivedInvestigationSummary) => {
    navigate('/investigate');
    try {
      await runCustomDeep(row.query, { top_k: 5, depth: 2 });
    } catch {
      /* navigate already happened; error surfaces in the store */
    }
  };

  const remove = async (row: BackendArchivedInvestigationSummary) => {
    try {
      await api.deleteInvestigation(row.investigation_id);
      setRows((prev) => prev.filter((r) => r.investigation_id !== row.investigation_id));
    } catch {
      /* non-fatal */
    }
  };

  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Archive className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="heading-tactical">Recent investigations</span>
        <span className="chip text-[8.5px] inline-flex items-center gap-1 border-[rgba(34,211,238,0.32)] text-[var(--color-ice-400)]">
          <Layers className="w-2.5 h-2.5" />
          disk-backed
        </span>
        {phase === 'ready' && (
          <span className="ml-2 font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            {rows.length}
          </span>
        )}
        <button
          onClick={load}
          title="Refresh archive"
          className="ml-auto h-5 px-1.5 inline-flex items-center gap-1 rounded-sm hover:bg-[rgba(34,211,238,0.05)] text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
        >
          <RefreshCw className={cn('w-3 h-3', phase === 'loading' && 'animate-spin')} />
        </button>
      </div>

      {/* Intent filter strip (only shown when multiple workflows are archived) */}
      {intentKinds.length > 1 && (
        <div className="px-3 py-2 border-b border-[var(--color-line-soft)] flex items-center gap-1 flex-wrap">
          <FilterPill
            active={intentFilter == null}
            onClick={() => setIntentFilter(null)}
            label="all"
          />
          {intentKinds.map((k) => (
            <FilterPill
              key={k}
              active={intentFilter === k}
              onClick={() => setIntentFilter(k)}
              label={k.replace(/_/g, ' ')}
            />
          ))}
        </div>
      )}

      {phase === 'loading' && (
        <div className="px-3 py-3 flex items-center gap-2 font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          <Loader2 className="w-3 h-3 animate-spin" />
          reading archive …
        </div>
      )}

      {phase === 'error' && (
        <div className="px-3 py-3">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-rose-400)]" />
            <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-rose-400)]">
              archive unreachable
            </span>
            <button
              onClick={load}
              className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
            >
              retry
            </button>
          </div>
          {error && (
            <div className="font-mono text-[10px] text-[var(--color-rose-300)] break-all">
              {error.slice(0, 240)}
            </div>
          )}
        </div>
      )}

      {phase === 'empty' && (
        <div className="px-3 py-3 font-mono text-[10.5px] text-[var(--color-text-muted)] leading-relaxed">
          no investigations archived yet · run a custom investigation to populate
        </div>
      )}

      {phase === 'ready' && (
        <ul className="divide-y divide-[var(--color-line-soft)]">
          {rows.map((row) => (
            <RecentRow
              key={row.investigation_id}
              row={row}
              liveTotalVertices={liveEnv?.total_vertices ?? null}
              isRunning={isRunning}
              onReplay={() => replay(row)}
              onRemove={() => remove(row)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function FilterPill({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'h-5 px-2 inline-flex items-center font-mono text-[9px] tracking-[0.22em] uppercase rounded-sm transition-colors',
        active
          ? 'border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-300)]'
          : 'border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]',
      )}
    >
      {label}
    </button>
  );
}

function RecentRow({
  row,
  liveTotalVertices,
  isRunning,
  onReplay,
  onRemove,
}: {
  row: BackendArchivedInvestigationSummary;
  liveTotalVertices: number | null;
  isRunning: boolean;
  onReplay: () => void;
  onRemove: () => void;
}) {
  const intentTone = _intentTone(row.intent_kind);
  const elapsed = row.elapsed_ms != null ? _formatMs(row.elapsed_ms) : '—';
  const created = row.created_at ? _formatRel(row.created_at) : '';
  // Env drift flag — if the live graph has gained or lost >1% vertices
  // since this investigation ran, surface that so the analyst knows a
  // replay will be against a different graph.
  const drift = _computeEnvDrift(row.env_total_vertices ?? null, liveTotalVertices);

  return (
    <li className="px-3 py-2 hover:bg-[rgba(34,211,238,0.025)] transition-colors group">
      <div className="flex items-start gap-2">
        {/* Intent badge */}
        <div
          className="shrink-0 w-1 self-stretch rounded-full"
          style={{ background: intentTone }}
        />

        <button
          onClick={onReplay}
          disabled={isRunning}
          title={isRunning ? 'wait for the current investigation to finish' : `replay: ${row.query}`}
          className="flex-1 min-w-0 text-left disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {/* Headline: intent label + query text */}
          <div className="flex items-baseline gap-2 mb-0.5">
            <span
              className="font-mono text-[9px] tracking-[0.22em] uppercase shrink-0"
              style={{ color: intentTone }}
            >
              {row.intent_kind?.replace(/_/g, ' ') ?? '—'}
            </span>
            {row.intent_confidence != null && row.intent_kind && row.intent_kind !== 'unknown' && (
              <span className="font-mono text-[8.5px] text-[var(--color-text-muted)] shrink-0">
                {Math.round(row.intent_confidence * 100)}%
              </span>
            )}
            <span className="text-[12px] text-[var(--color-text-bright)] truncate">
              {row.query}
            </span>
          </div>

          {/* Signals row — only show populated metrics */}
          <div className="flex items-center gap-3 flex-wrap font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
            <Signal icon={Target} label="suspects" value={row.suspect_count} tone="emerald" />
            <Signal icon={Network} label="ring" value={row.ring_count} tone="amber" />
            <Signal icon={Compass} label="neighbors" value={row.neighbor_count} tone="ice" />
            <Signal icon={ShieldAlert} label="evidence" value={row.evidence_count} tone="rose" />
            {row.has_deep_report && (
              <span
                className="inline-flex items-center gap-1"
                style={{ color: 'var(--color-violet-400)' }}
                title={row.deep_confidence != null
                  ? `deep confidence ${(row.deep_confidence * 100).toFixed(0)}%`
                  : 'cognitive layer attached'}
              >
                <Brain className="w-2.5 h-2.5" />
                <span>cognitive{row.deep_confidence != null ? ` ${Math.round(row.deep_confidence * 100)}%` : ''}</span>
              </span>
            )}
            {/* Environment snapshot — what graph state was live when this
                investigation was archived. Surfaces drift vs current. */}
            {row.env_total_vertices != null && (
              <span
                className="inline-flex items-center gap-1"
                style={{ color: drift.color }}
                title={drift.tooltip}
              >
                <Layers className="w-2.5 h-2.5" />
                <span>
                  env {row.env_total_vertices.toLocaleString()}
                  {drift.label ? ` · ${drift.label}` : ''}
                </span>
              </span>
            )}
            <span className="inline-flex items-center gap-1 ml-auto">
              <Clock className="w-2.5 h-2.5" />
              <span>{elapsed}</span>
              <span className="text-[var(--color-text-ghost)] mx-0.5">·</span>
              <span>{created}</span>
              {row.offline_mode && (
                <>
                  <span className="text-[var(--color-text-ghost)] mx-0.5">·</span>
                  <span className="text-[var(--color-amber-400)]">offline</span>
                </>
              )}
            </span>
          </div>
        </button>

        <div className="shrink-0 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onReplay}
            disabled={isRunning}
            title="replay investigation"
            className="w-6 h-6 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-ice-300)] hover:bg-[rgba(34,211,238,0.05)] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Zap className="w-3 h-3" />
          </button>
          <button
            onClick={onRemove}
            title="remove from archive"
            className="w-6 h-6 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.05)]"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
    </li>
  );
}

function Signal({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Target;
  label: string;
  value: number | null | undefined;
  tone: 'emerald' | 'rose' | 'amber' | 'ice';
}) {
  if (value == null || value === 0) return null;
  const color =
    tone === 'emerald' ? 'var(--color-emerald-400)' :
    tone === 'rose' ? 'var(--color-rose-400)' :
    tone === 'amber' ? 'var(--color-amber-400)' :
    'var(--color-ice-400)';
  return (
    <span className="inline-flex items-center gap-1" style={{ color }}>
      <Icon className="w-2.5 h-2.5" />
      <span>{label}</span>
      <span className="text-[var(--color-text-bright)]">{value}</span>
    </span>
  );
}

function _intentTone(kind: string | null | undefined): string {
  switch (kind) {
    case 'rank_suspects':         return 'var(--color-emerald-400)';
    case 'find_ring':             return 'var(--color-amber-400)';
    case 'trace_money':           return 'var(--color-ice-400)';
    case 'ownership_chain':       return 'var(--color-violet-400)';
    case 'shared_infrastructure': return 'var(--color-violet-300)';
    case 'hidden_relationships':  return 'var(--color-rose-400)';
    case 'entity_dossier':        return 'var(--color-ice-300)';
    case 'neighborhood_expansion':return 'var(--color-ice-400)';
    case 'unknown':               return 'var(--color-amber-400)';
    default:                      return 'var(--color-text-muted)';
  }
}

function _formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

/**
 * Compare the captured env total vs the current live total. Anything within
 * ~1% counts as stable (catches the noise from upsert idempotency). Larger
 * deltas warn the analyst that a replay would run against a different graph.
 */
function _computeEnvDrift(
  captured: number | null,
  live: number | null,
): { label: string; color: string; tooltip: string } {
  if (captured == null || live == null) {
    return {
      label: '',
      color: 'var(--color-text-muted)',
      tooltip: 'graph state at investigation time',
    };
  }
  if (captured === 0) {
    return {
      label: '',
      color: 'var(--color-text-muted)',
      tooltip: 'no graph state captured',
    };
  }
  const delta = live - captured;
  const pct = Math.abs(delta) / captured;
  if (pct < 0.01) {
    return {
      label: 'matches live',
      color: 'var(--color-emerald-400)',
      tooltip: `graph total ${captured.toLocaleString()} (captured) ≈ ${live.toLocaleString()} (live) — replay safe`,
    };
  }
  const sign = delta > 0 ? '+' : '−';
  return {
    label: `Δ ${sign}${Math.abs(delta).toLocaleString()}`,
    color: 'var(--color-amber-400)',
    tooltip: `graph changed since: captured ${captured.toLocaleString()} → live ${live.toLocaleString()} (replay will see different data)`,
  };
}

function _formatRel(unix: number): string {
  const secs = Math.max(0, Math.floor(Date.now() / 1000 - unix));
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}
