import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileText,
  Layers,
  Loader2,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
  UploadCloud,
  Zap,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  api,
  type BackendEnvironmentState,
  type BackendIngestSchema,
  type BackendSampleIngestResult,
  type BackendUploadManifest,
} from '@/lib/api-client';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';
import { OperationalConnectorPanel } from '@/components/sources/OperationalConnectorPanel';
import { EnvironmentReadinessStrip } from '@/components/sources/EnvironmentReadinessStrip';
import { SourceHandoffStrip } from '@/components/sources/SourceHandoffStrip';

/**
 * DataSources — "Choose Intelligence Environment" landing.
 *
 * Three operational paths:
 *   1. Launch Sample Fraud Ecosystem  → POST /api/v1/ingest/sample
 *   2. Upload Custom Dataset           → POST /api/v1/ingest/upload + /promote
 *   3. Connect External Source         → honest connector gallery
 *
 * Every numeric value on this page is read from one of:
 *   • /api/v1/ingest/environment (live TG state)
 *   • /api/v1/ingest/list (real uploads)
 *   • /api/v1/ingest/sample response
 *
 * No mock counters, no fake progress bars.
 */
export function DataSources() {
  const backendStatus = useIntelStore((s) => s.backendStatus);

  const [env, setEnv] = useState<BackendEnvironmentState | null>(null);
  const [uploads, setUploads] = useState<BackendUploadManifest[]>([]);
  const [schema, setSchema] = useState<BackendIngestSchema | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [sampleRunning, setSampleRunning] = useState(false);
  const [sampleResult, setSampleResult] = useState<BackendSampleIngestResult | null>(null);

  const [promotingId, setPromotingId] = useState<string | null>(null);
  const [latestPromotion, setLatestPromotion] = useState<{
    inserted: number;
    skipped: number;
    elapsedS: number;
    vertexCounts: Record<string, number> | null;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  const isOffline = !backendStatus;
  const tgOffline = backendStatus?.tigergraphOffline ?? false;

  // Refresh accepts a `probe` flag — manual refresh always asks for a
  // fresh TG round-trip (so the user gets the truth, not a cached flag),
  // while the auto-poll path uses the cheap cached read.
  const refresh = useCallback(async (opts: { probe?: boolean } = {}) => {
    setBusy(true);
    setErr(null);
    try {
      const [e, list, sch] = await Promise.all([
        api.ingestEnvironment({ probe: opts.probe }).catch(() => null),
        api.ingestList().catch(() => ({ uploads: [] })),
        api.ingestSchema().catch(() => null),
      ]);
      setEnv(e);
      setUploads(list.uploads);
      setSchema(sch);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Auto-poll every 15s so the Sources page reflects ingestion / promotion
  // activity from elsewhere (e.g. CLI) without manual reload.
  useEffect(() => {
    const id = setInterval(() => { void refresh(); }, 15_000);
    return () => clearInterval(id);
  }, [refresh]);

  // When the orchestrator-status poll flips TG offline, immediately
  // invalidate the env so we don't keep showing stale `online` counts.
  useEffect(() => {
    if (tgOffline || isOffline) {
      setEnv((prev) =>
        prev
          ? {
              ...prev,
              tigergraph_online: false,
              investigation_ready: false,
              readiness: prev.readiness && {
                ...prev.readiness,
                graph:     { ready: false, reason: 'tigergraph unreachable · investigations blocked' },
                topology:  { ready: false, reason: 'tigergraph offline' },
                retrieval: { ready: false, reason: 'retrieval requires a hydrated graph' },
                benchmark: { ready: false, reason: 'benchmark requires a hydrated graph' },
                reasoning: { ready: false, reason: 'reasoning requires retrieval' },
              },
            }
          : prev,
      );
    }
    // Trigger a probe refresh ONCE when we transition from offline → online,
    // so the page picks up the recovery without waiting for the next poll tick.
    // Empty dependency on env to avoid loops; we only need the flip detection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tgOffline, isOffline]);

  const launchSample = async () => {
    setSampleRunning(true);
    setErr(null);
    try {
      const r = await api.ingestSample('small');
      setSampleResult(r);
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSampleRunning(false);
    }
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const f = files[0];
    setBusy(true);
    setErr(null);
    try {
      const m = await api.ingestUpload(f);
      setUploads((prev) => [m, ...prev]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const promote = async (id: string) => {
    setPromotingId(id);
    setErr(null);
    try {
      const r = await api.ingestPromote(id);
      setLatestPromotion({
        inserted: r.records,
        skipped: r.skipped,
        elapsedS: r.elapsed_s,
        vertexCounts: r.vertex_counts,
      });
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setPromotingId(null);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.ingestDelete(id);
      setUploads((prev) => prev.filter((u) => u.upload_id !== id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <PageHeader
        icon={Database}
        eyebrow="intelligence environment"
        title="Choose how this workspace ingests evidence"
        meta="real TigerGraph hydration · no simulated runs"
      />
      <div className="px-6 pb-10 max-w-[1280px] mx-auto flex flex-col gap-4 pt-2">
        {/* Active environment + status bar */}
        <ActiveEnvironmentStrip
          env={env}
          backendOffline={isOffline}
          tgOffline={tgOffline}
          busy={busy}
          onRefresh={() => refresh({ probe: true })}
        />

        {/* Operational readiness verdict — single source of truth.
            Reads from `env.readiness` which the backend composes. */}
        {env?.readiness && (
          <EnvironmentReadinessStrip
            readiness={env.readiness}
            investigationReady={env.investigation_ready}
            freshProbe={env.fresh_probe}
            probeFailed={env.probe_failed}
            reconnectAttempted={env.reconnect_attempted}
          />
        )}

        {/* Operational handoffs — only renders when environment is ready.
            Hands off into /investigate (with seed), /benchmark, etc. */}
        <SourceHandoffStrip env={env} />

        {err && (
          <section className="surface px-3 py-2 border-l-2 border-[var(--color-rose-500)] flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-rose-400)] mt-0.5 shrink-0" />
            <span className="font-mono text-[10.5px] text-[var(--color-rose-300)] break-all">
              {err.slice(0, 320)}
            </span>
            <button
              onClick={() => setErr(null)}
              className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)]"
            >
              dismiss
            </button>
          </section>
        )}

        {/* Three-path landing */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <SampleEcosystemCard
            running={sampleRunning}
            result={sampleResult}
            canLaunch={!isOffline && !tgOffline}
            onLaunch={launchSample}
          />
          <UploadCustomCard
            expanded={showUpload}
            onToggle={() => setShowUpload((v) => !v)}
            disabled={isOffline}
            uploads={uploads.length}
          />
          <OperationalConnectorPanel
            env={env}
            backendOffline={isOffline}
            tgOffline={tgOffline}
            onOpenUpload={() => setShowUpload(true)}
            onRefresh={refresh}
          />
        </div>

        {/* Upload pane (collapsed by default; expands when "Upload Custom Dataset" clicked) */}
        {showUpload && (
          <UploadPane
            dragOver={dragOver}
            schema={schema}
            isOffline={isOffline}
            tgOffline={tgOffline}
            fileInputRef={fileInputRef}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFiles(e.dataTransfer?.files ?? null);
            }}
            onSelect={(files) => {
              handleFiles(files);
              if (fileInputRef.current) fileInputRef.current.value = '';
            }}
          />
        )}

        {/* Latest promotion outcome */}
        {latestPromotion && (
          <section className="surface px-3 py-3 border-l-2 border-[var(--color-emerald-500)]">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-emerald-400)]" />
              <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-emerald-400)]">
                promoted to live tigergraph
              </span>
              <span className="ml-auto font-mono text-[9.5px] text-[var(--color-text-muted)]">
                {latestPromotion.elapsedS}s
              </span>
            </div>
            <div className="text-[11.5px] text-[var(--color-text-secondary)] mt-1">
              Inserted{' '}
              <strong className="text-[var(--color-text-bright)]">
                {latestPromotion.inserted}
              </strong>{' '}
              records · skipped <strong>{latestPromotion.skipped}</strong>.
            </div>
          </section>
        )}

        {/* Sample ingestion stage report */}
        {sampleResult && <SampleResultPanel result={sampleResult} />}

        {/* Recent uploads */}
        {uploads.length > 0 && (
          <UploadListPanel
            uploads={uploads}
            promotingId={promotingId}
            canPromote={!isOffline && !tgOffline}
            onPromote={promote}
            onDelete={remove}
          />
        )}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Active environment header                                                  */
/* -------------------------------------------------------------------------- */

function ActiveEnvironmentStrip({
  env,
  backendOffline,
  tgOffline,
  busy,
  onRefresh,
}: {
  env: BackendEnvironmentState | null;
  backendOffline: boolean;
  tgOffline: boolean;
  busy: boolean;
  onRefresh: () => void;
}) {
  const totalVertices = env?.total_vertices ?? 0;
  const tone =
    backendOffline ? 'rose'
    : tgOffline ? 'amber'
    : 'emerald';
  const label =
    backendOffline ? 'orchestrator offline'
    : tgOffline ? 'tigergraph offline · investigations limited'
    : 'tigergraph connected';
  const color =
    tone === 'rose'
      ? 'var(--color-rose-400)'
      : tone === 'amber'
      ? 'var(--color-amber-400)'
      : 'var(--color-emerald-400)';
  return (
    <section className="surface px-4 py-2.5 flex items-center gap-3 flex-wrap">
      <span className="w-1.5 h-1.5 rounded-full anim-drift" style={{ background: color }} />
      <span className="font-mono text-[10px] tracking-[0.32em] uppercase" style={{ color }}>
        active environment · {label}
      </span>
      {env && (
        <>
          <span className="text-[var(--color-text-ghost)] mx-1">·</span>
          <span className="font-mono text-[10.5px] text-[var(--color-text-bright)]">
            {totalVertices.toLocaleString()} vertices
          </span>
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
            ({env.uploads_total} uploads · {env.uploads_promoted} promoted)
          </span>
        </>
      )}
      <button
        onClick={onRefresh}
        disabled={busy}
        className="ml-auto h-6 px-2 inline-flex items-center gap-1.5 rounded-sm font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.04)]"
      >
        <RefreshCw className={cn('w-3 h-3', busy && 'animate-spin')} />
        refresh
      </button>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* Three landing cards                                                        */
/* -------------------------------------------------------------------------- */

function SampleEcosystemCard({
  running,
  result,
  canLaunch,
  onLaunch,
}: {
  running: boolean;
  result: BackendSampleIngestResult | null;
  canLaunch: boolean;
  onLaunch: () => void;
}) {
  const promoted = result != null;
  return (
    <section className="surface p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Sparkles className="w-3.5 h-3.5 text-[var(--color-emerald-400)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          sample fraud ecosystem
        </span>
      </div>
      <div className="text-[13px] text-[var(--color-text-bright)] font-light leading-snug">
        Launch a curated adversarial topology.
      </div>
      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
        ~25,000 entities · hidden rings · laundering chains · intermediary
        shells · shared infrastructure · benchmark-ready investigations.
      </p>
      <ul className="text-[10.5px] text-[var(--color-text-muted)] leading-relaxed space-y-0.5 mt-1">
        {[
          'Persons · Companies · Accounts · Addresses · Devices · Transactions',
          '15 fraud rings · structural cross-references',
          'directly investigatable after ingestion',
        ].map((b) => (
          <li key={b} className="flex items-start gap-1">
            <span className="text-[var(--color-emerald-400)]">▸</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>
      <button
        onClick={onLaunch}
        disabled={!canLaunch || running}
        className={cn(
          'mt-auto h-9 px-3 inline-flex items-center justify-center gap-2 rounded-sm text-[10.5px] font-mono tracking-[0.26em] uppercase',
          canLaunch && !running
            ? 'border border-[rgba(16,185,129,0.4)] bg-[rgba(16,185,129,0.07)] text-[var(--color-emerald-400)] hover:bg-[rgba(16,185,129,0.12)]'
            : 'border border-[var(--color-line)] text-[var(--color-text-muted)] cursor-not-allowed',
        )}
      >
        {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
        {running ? 'hydrating tigergraph…' : promoted ? 're-launch' : 'launch ecosystem'}
      </button>
      {!canLaunch && (
        <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] text-center">
          requires tigergraph online
        </div>
      )}
    </section>
  );
}

function UploadCustomCard({
  expanded,
  onToggle,
  disabled,
  uploads,
}: {
  expanded: boolean;
  onToggle: () => void;
  disabled: boolean;
  uploads: number;
}) {
  return (
    <section className="surface p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <UploadCloud className="w-3.5 h-3.5 text-[var(--color-ice-400)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-ice-400)]">
          custom dataset
        </span>
      </div>
      <div className="text-[13px] text-[var(--color-text-bright)] font-light leading-snug">
        Upload your own topology.
      </div>
      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
        CSV or TSV per vertex type · schema sniffed against the live graph ·
        promote to TigerGraph on demand.
      </p>
      <ul className="text-[10.5px] text-[var(--color-text-muted)] leading-relaxed space-y-0.5 mt-1">
        {[
          'Person · Company · Account · Address · Device · Transaction',
          'column rename + type coercion handled automatically',
          'uploaded vertices become live-investigatable',
        ].map((b) => (
          <li key={b} className="flex items-start gap-1">
            <span className="text-[var(--color-ice-400)]">▸</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>
      <button
        onClick={onToggle}
        disabled={disabled}
        className={cn(
          'mt-auto h-9 px-3 inline-flex items-center justify-center gap-2 rounded-sm text-[10.5px] font-mono tracking-[0.26em] uppercase',
          !disabled
            ? 'border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.12)]'
            : 'border border-[var(--color-line)] text-[var(--color-text-muted)] cursor-not-allowed',
        )}
      >
        <Upload className="w-3 h-3" />
        {expanded ? 'hide upload pane' : 'open upload pane'}
        {uploads > 0 && (
          <span className="chip text-[8.5px] ml-1">{uploads}</span>
        )}
      </button>
    </section>
  );
}

// Static connector gallery removed — superseded by
// `<OperationalConnectorPanel>` (src/components/sources/OperationalConnectorPanel.tsx)
// which renders live state per adapter + real actions.

/* -------------------------------------------------------------------------- */
/* Upload pane (expanded)                                                     */
/* -------------------------------------------------------------------------- */

function UploadPane({
  dragOver,
  schema,
  isOffline,
  tgOffline,
  fileInputRef,
  onDragOver,
  onDragLeave,
  onDrop,
  onSelect,
}: {
  dragOver: boolean;
  schema: BackendIngestSchema | null;
  isOffline: boolean;
  tgOffline: boolean;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  onSelect: (files: FileList | null) => void;
}) {
  return (
    <section
      className={cn(
        'surface px-4 py-6 transition-colors',
        dragOver && 'bg-[rgba(34,211,238,0.04)]',
      )}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="flex flex-col items-center justify-center gap-2 py-4 text-center">
        <UploadCloud className="w-7 h-7 text-[var(--color-ice-400)] opacity-80" />
        <div className="text-[12.5px] text-[var(--color-text-bright)] font-light mt-1">
          Drop a CSV here · or click to browse
        </div>
        <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
          POST /api/v1/ingest/upload · live TigerGraph endpoint
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.tsv,.txt"
          className="hidden"
          onChange={(e) => onSelect(e.target.files)}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isOffline || tgOffline}
          className="mt-1 h-8 px-3 inline-flex items-center gap-2 rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.12)] disabled:opacity-40 disabled:cursor-not-allowed text-[10.5px] font-mono tracking-[0.26em] uppercase"
        >
          <Upload className="w-3 h-3" />
          choose file
        </button>
        {schema && (
          <div className="mt-3 max-w-[640px]">
            <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
              recognized schemas
            </div>
            <div className="flex flex-wrap justify-center gap-1">
              {/* Backward-compat: backend returns both `vertex_schemas`
                  (canonical) and `supported` (alias). Render whichever the
                  current backend version emits; never crash if both are
                  absent or the response shape changes. */}
              {(schema.vertex_schemas ?? schema.supported ?? []).map((s) => (
                <span
                  key={s.vertex_type}
                  title={`required: ${(s.required ?? []).join(', ')}\noptional: ${(s.optional ?? []).join(', ')}`}
                  className="chip text-[8.5px] border-[rgba(34,211,238,0.28)] text-[var(--color-ice-400)]"
                >
                  {s.vertex_type}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* Sample ingestion stage report                                              */
/* -------------------------------------------------------------------------- */

function SampleResultPanel({ result }: { result: BackendSampleIngestResult }) {
  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Sparkles className="w-3 h-3 text-[var(--color-emerald-400)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          sample ecosystem · hydration report
        </span>
        <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {result.elapsed_s}s total · {result.total_records.toLocaleString()} records
        </span>
      </div>
      <div className="divide-y divide-[var(--color-line-soft)]">
        {result.stages.map((s) => (
          <div key={s.vertex_type} className="px-4 py-2 flex items-center gap-3">
            <Layers className="w-3 h-3 text-[var(--color-text-muted)]" />
            <span className="font-mono text-[10.5px] text-[var(--color-text-bright)] w-28">
              {s.vertex_type}
            </span>
            <span className="font-mono text-[9.5px] text-[var(--color-text-muted)] truncate">
              {s.file}
            </span>
            <span className="ml-auto font-mono text-[10.5px] text-[var(--color-emerald-400)]">
              {s.records.toLocaleString()}
            </span>
            <span className="font-mono text-[9.5px] text-[var(--color-text-muted)] w-16 text-right">
              {s.elapsed_s}s
            </span>
          </div>
        ))}
      </div>
      {result.vertex_counts && (
        <div className="px-4 py-2 border-t border-[var(--color-line-soft)] flex flex-wrap gap-1">
          {Object.entries(result.vertex_counts).map(([t, n]) => (
            <span key={t} className="chip text-[8.5px]">
              {t}:{' '}
              <span className="font-mono text-[var(--color-text-bright)] ml-1">
                {n.toLocaleString()}
              </span>
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* Recent uploads list                                                        */
/* -------------------------------------------------------------------------- */

function UploadListPanel({
  uploads,
  promotingId,
  canPromote,
  onPromote,
  onDelete,
}: {
  uploads: BackendUploadManifest[];
  promotingId: string | null;
  canPromote: boolean;
  onPromote: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <FileText className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          recent uploads
        </span>
        <span className="chip ml-1 text-[8.5px]">{uploads.length}</span>
      </div>
      <div className="divide-y divide-[var(--color-line-soft)]">
        {uploads.map((u) => (
          <UploadCard
            key={u.upload_id}
            upload={u}
            promoting={promotingId === u.upload_id}
            canPromote={canPromote && !u.promoted}
            onPromote={() => onPromote(u.upload_id)}
            onDelete={() => onDelete(u.upload_id)}
          />
        ))}
      </div>
    </section>
  );
}

function UploadCard({
  upload: u,
  promoting,
  canPromote,
  onPromote,
  onDelete,
}: {
  upload: BackendUploadManifest;
  promoting: boolean;
  canPromote: boolean;
  onPromote: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-3 flex-wrap">
        <FileText className="w-3.5 h-3.5 text-[var(--color-ice-400)] shrink-0" />
        <span className="text-[12px] font-medium text-[var(--color-text-bright)]">
          {u.filename}
        </span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {u.row_count.toLocaleString()} rows · {(u.size_bytes / 1024).toFixed(1)} KB
        </span>
        {u.detected_type ? (
          <span className="chip text-[8.5px] inline-flex items-center gap-1 border-[rgba(16,185,129,0.32)] text-[var(--color-emerald-400)]">
            <CheckCircle2 className="w-2.5 h-2.5" />
            schema · {u.detected_type}
          </span>
        ) : (
          <span className="chip text-[8.5px] inline-flex items-center gap-1 border-[rgba(245,158,11,0.32)] text-[var(--color-amber-400)]">
            <AlertTriangle className="w-2.5 h-2.5" />
            unrecognized schema
          </span>
        )}
        {u.promoted && (
          <span className="chip chip-emerald text-[8.5px]">promoted</span>
        )}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
        >
          {expanded ? 'collapse' : 'preview'}
        </button>
        {canPromote && (
          <button
            onClick={onPromote}
            disabled={promoting}
            className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-400)] hover:bg-[rgba(168,85,247,0.12)] disabled:opacity-40 disabled:cursor-not-allowed text-[9.5px] font-mono tracking-[0.22em] uppercase"
          >
            {promoting ? <Loader2 className="w-3 h-3 animate-spin" /> : <UploadCloud className="w-3 h-3" />}
            promote
          </button>
        )}
        <button
          onClick={onDelete}
          className="h-6 w-6 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.05)]"
          title="delete this upload"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {expanded && (
        <div className="mt-3 panel-soft p-2 overflow-x-auto">
          <table className="w-full font-mono text-[10.5px]">
            <thead>
              <tr className="border-b border-[var(--color-line-soft)] text-[var(--color-text-muted)] uppercase tracking-[0.16em] text-[9px]">
                {u.header.map((h) => (
                  <th key={h} className="text-left px-2 py-1">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {u.preview.map((row, i) => (
                <tr key={i} className="border-b border-[var(--color-line-soft)] last:border-b-0">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1 text-[var(--color-text-secondary)] truncate max-w-[180px]">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
