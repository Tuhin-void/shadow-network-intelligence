import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Database,
  FileText,
  GitBranch,
  Layers,
  Loader2,
  Network,
  Plug,
  RotateCcw,
  ShieldAlert,
  Upload,
} from 'lucide-react';
import { api, type BackendEnvironmentState } from '@/lib/api-client';
import type { ConnectionStatus } from '@/lib/adapters';
import { cn } from '@/lib/utils';

/**
 * OperationalConnectorPanel — stateful intelligence-infrastructure layer.
 *
 * Replaces the static 2-column connector grid with two prominent live
 * connector cards (CSV, TigerGraph) plus an honest "planned" subsection
 * for adapters that require an enterprise bridge.
 *
 * Every state value here is derived from REAL backend signals:
 *   • TigerGraph card  → BackendEnvironmentState (vertex_counts, uploads, online)
 *   • CSV card         → BackendEnvironmentState (uploads_total, uploads_promoted)
 *   • reconnect button → POST /api/v1/orchestrator/reconnect
 *
 * No fake "LIVE" labels. No decorative state. The card is causally
 * connected to whether the operator can actually do work.
 */
export function OperationalConnectorPanel({
  env,
  backendOffline,
  tgOffline,
  onOpenUpload,
  onRefresh,
}: {
  env: BackendEnvironmentState | null;
  backendOffline: boolean;
  tgOffline: boolean;
  onOpenUpload: () => void;
  onRefresh: () => void;
}) {
  return (
    <section className="surface p-4 flex flex-col gap-3 min-h-0">
      <div className="flex items-center gap-2 shrink-0">
        <Plug className="w-3.5 h-3.5 text-[var(--color-violet-400)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-violet-400)]">
          external sources
        </span>
      </div>

      <div className="text-[13px] text-[var(--color-text-bright)] font-light leading-snug">
        Operational connector layer.
      </div>
      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
        Live state per adapter. Enterprise bridges marked honestly — no
        decorative connectors.
      </p>

      {/* Active connectors */}
      <div className="flex flex-col gap-2 mt-1">
        <TigerGraphConnector
          env={env}
          backendOffline={backendOffline}
          tgOffline={tgOffline}
          onRefresh={onRefresh}
        />
        <CSVConnector
          env={env}
          disabled={backendOffline}
          onOpenUpload={onOpenUpload}
        />
      </div>

      {/* Planned connectors */}
      <PlannedSubsection />
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* TigerGraph — the operational core                                          */
/* -------------------------------------------------------------------------- */

function TigerGraphConnector({
  env,
  backendOffline,
  tgOffline,
  onRefresh,
}: {
  env: BackendEnvironmentState | null;
  backendOffline: boolean;
  tgOffline: boolean;
  onRefresh: () => void;
}) {
  const navigate = useNavigate();
  const [reconnecting, setReconnecting] = useState(false);
  const [open, setOpen] = useState(false);

  const counts = env?.vertex_counts ?? {};
  const total = env?.total_vertices ?? 0;

  const state: ConnectorState = backendOffline
    ? 'backend-offline'
    : tgOffline
    ? 'offline'
    : total > 0
    ? 'active'
    : 'connected-empty';

  const tone = state === 'active' ? 'emerald'
    : state === 'connected-empty' ? 'amber'
    : 'rose';

  const headline =
    state === 'active' ? 'connected · topology active'
    : state === 'connected-empty' ? 'connected · awaiting hydration'
    : state === 'offline' ? 'disconnected · TG workspace unreachable'
    : 'backend unreachable';

  const reconnect = async () => {
    setReconnecting(true);
    try {
      await api.orchestratorReconnect();
      await onRefresh();
    } catch {
      // surface via env refresh
    } finally {
      setReconnecting(false);
    }
  };

  return (
    <div className={cn('panel-soft', borderClass(tone), 'border-l-2 p-3')}>
      <div className="flex items-center gap-2 mb-1.5">
        <Network className="w-3.5 h-3.5" style={{ color: toneColor(tone) }} />
        <span className="font-mono text-[10.5px] tracking-[0.28em] uppercase" style={{ color: toneColor(tone) }}>
          TigerGraph
        </span>
        <span className="ml-auto inline-flex items-center gap-1 font-mono text-[9px] tracking-[0.22em] uppercase" style={{ color: toneColor(tone) }}>
          <span className="w-1 h-1 rounded-full" style={{ background: toneColor(tone) }} />
          {state === 'active' || state === 'connected-empty' ? 'connected' : state === 'offline' ? 'disconnected' : 'unreachable'}
        </span>
      </div>
      <div className="text-[11.5px] text-[var(--color-text-bright)] leading-snug">
        {state === 'active' ? (
          <>
            <span className="font-mono text-[14px] text-[var(--color-emerald-400)]">
              {total.toLocaleString()}
            </span>{' '}
            <span className="font-mono text-[10px] text-[var(--color-text-muted)] uppercase tracking-[0.18em]">
              vertices · traversal ready
            </span>
          </>
        ) : (
          <span className="text-[11px] text-[var(--color-text-secondary)]">{headline}</span>
        )}
      </div>

      {/* Detail row — vertex counts per type, expandable */}
      {state === 'active' && (
        <>
          <button
            onClick={() => setOpen((v) => !v)}
            className="mt-2 inline-flex items-center gap-1 font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
          >
            {open ? 'collapse' : 'inspect topology'}
            <ChevronDown className={cn('w-3 h-3 transition-transform', open && 'rotate-180')} />
          </button>
          {open && (
            <div className="mt-2 grid grid-cols-2 gap-1">
              {Object.entries(counts).map(([t, n]) => (
                <div key={t} className="flex items-center gap-1.5 text-[10.5px] font-mono">
                  <Layers className="w-2.5 h-2.5 text-[var(--color-text-muted)]" />
                  <span className="text-[var(--color-text-secondary)] tracking-tight">{t}</span>
                  <span className="ml-auto text-[var(--color-text-bright)]">
                    {(n ?? 0).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Actions row */}
      <div className="mt-3 flex items-center gap-1.5 flex-wrap">
        {state === 'active' ? (
          <>
            <button
              onClick={() => navigate('/investigate')}
              className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border border-[rgba(34,211,238,0.32)] bg-[rgba(34,211,238,0.05)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)] text-[9.5px] font-mono tracking-[0.22em] uppercase"
            >
              <GitBranch className="w-3 h-3" />
              investigate
            </button>
            <button
              onClick={() => navigate('/benchmark')}
              className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-emerald-400)] hover:border-[rgba(16,185,129,0.32)] hover:bg-[rgba(16,185,129,0.04)] text-[9.5px] font-mono tracking-[0.22em] uppercase"
            >
              <ShieldAlert className="w-3 h-3" />
              validate
            </button>
          </>
        ) : state === 'offline' ? (
          <button
            onClick={reconnect}
            disabled={reconnecting}
            className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border border-[rgba(245,158,11,0.4)] bg-[rgba(245,158,11,0.06)] text-[var(--color-amber-400)] hover:bg-[rgba(245,158,11,0.12)] disabled:opacity-40 text-[9.5px] font-mono tracking-[0.22em] uppercase"
          >
            {reconnecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
            {reconnecting ? 'reconnecting' : 'reconnect now'}
          </button>
        ) : state === 'connected-empty' ? (
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            launch sample ecosystem or upload to hydrate
          </span>
        ) : null}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* CSV — upload hydration                                                     */
/* -------------------------------------------------------------------------- */

function CSVConnector({
  env,
  disabled,
  onOpenUpload,
}: {
  env: BackendEnvironmentState | null;
  disabled: boolean;
  onOpenUpload: () => void;
}) {
  const uploads = env?.uploads_total ?? 0;
  const promoted = env?.uploads_promoted ?? 0;
  return (
    <div className="panel-soft border-l-2 border-[rgba(34,211,238,0.32)] p-3">
      <div className="flex items-center gap-2 mb-1.5">
        <FileText className="w-3.5 h-3.5 text-[var(--color-ice-400)]" />
        <span className="font-mono text-[10.5px] tracking-[0.28em] uppercase text-[var(--color-ice-400)]">
          CSV
        </span>
        <span className="ml-auto inline-flex items-center gap-1 font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-ice-400)]">
          <span className="w-1 h-1 rounded-full bg-[var(--color-ice-400)]" />
          ready for upload
        </span>
      </div>
      <div className="text-[11.5px] text-[var(--color-text-secondary)] leading-snug">
        Schema-sniffed against the live graph. Promotion is real upsert
        against TigerGraph.
      </div>
      <div className="mt-2 flex items-center gap-3 font-mono text-[10px] text-[var(--color-text-muted)]">
        <span>
          <span className="text-[var(--color-text-bright)]">{uploads}</span> uploaded
        </span>
        <span>
          <span className="text-[var(--color-emerald-400)]">{promoted}</span> promoted
        </span>
      </div>
      <div className="mt-3 flex items-center gap-1.5">
        <button
          onClick={onOpenUpload}
          disabled={disabled}
          className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.12)] disabled:opacity-40 text-[9.5px] font-mono tracking-[0.22em] uppercase"
        >
          <Upload className="w-3 h-3" />
          upload dataset
          <ArrowRight className="w-2.5 h-2.5" />
        </button>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Planned — honest, no fake actions                                          */
/* -------------------------------------------------------------------------- */

const PLANNED = [
  { id: 'json',      label: 'JSON',         note: 'planned · adapter not enabled' },
  { id: 'postgres',  label: 'PostgreSQL',   note: 'planned · enterprise bridge required' },
  { id: 'kafka',     label: 'Kafka',        note: 'planned · enterprise bridge required' },
  { id: 'snowflake', label: 'Snowflake',    note: 'planned · enterprise bridge required' },
] as const;

function PlannedSubsection() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1 border-t border-[var(--color-line-soft)] pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
      >
        <AlertTriangle className="w-2.5 h-2.5 text-[var(--color-amber-400)]" />
        {open ? 'hide planned adapters' : `${PLANNED.length} planned adapters · not enabled`}
        <ChevronDown className={cn('w-3 h-3 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-1">
          {PLANNED.map((c) => (
            <div key={c.id} className="flex items-center gap-2 py-1 opacity-70">
              <Database className="w-2.5 h-2.5 text-[var(--color-text-muted)]" />
              <span className="font-mono text-[10.5px] text-[var(--color-text-secondary)]">
                {c.label}
              </span>
              <span className="ml-auto font-mono text-[8.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                {c.note}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* helpers                                                                    */
/* -------------------------------------------------------------------------- */

type ConnectorState = 'active' | 'connected-empty' | 'offline' | 'backend-offline';

function toneColor(t: 'emerald' | 'amber' | 'rose'): string {
  return t === 'emerald'
    ? 'var(--color-emerald-400)'
    : t === 'amber'
    ? 'var(--color-amber-400)'
    : 'var(--color-rose-400)';
}

function borderClass(t: 'emerald' | 'amber' | 'rose'): string {
  return t === 'emerald'
    ? 'border-l-[rgba(16,185,129,0.32)]'
    : t === 'amber'
    ? 'border-l-[rgba(245,158,11,0.32)]'
    : 'border-l-[rgba(244,63,94,0.32)]';
}

// Exported for type symmetry — useful if a future caller needs an empty placeholder.
export const NoConnectors: BackendEnvironmentState | null = null;

// Decorative imports kept tree-shakeable — these icons are used optionally
// by future connector cards (no-op placeholder).
void CheckCircle2;
