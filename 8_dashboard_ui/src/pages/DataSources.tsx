import { useMemo, useState } from 'react';
import { useIntelStore } from '@/store/intel-store';
import { cn, formatTime } from '@/lib/utils';
import {
  Activity,
  AlertOctagon,
  Boxes,
  CheckCircle2,
  Cpu,
  Database,
  FileJson,
  FileText,
  GitBranch,
  HardDrive,
  Network,
  Pause,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Webhook,
  Workflow,
  X,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  AVAILABLE_KINDS,
  CATEGORY_LABEL,
  KIND_LABEL,
  KIND_TO_CATEGORY,
} from '@/lib/sources-mock';
import type {
  DataSource,
  IngestionRun,
  SourceCategory,
  SourceHealth,
  SourceKind,
} from '@/types/sources';
import { SchemaMappingView } from '@/components/sources/SchemaMappingView';
import { AnimatePresence, motion } from 'framer-motion';

type Tab = 'overview' | 'schema' | 'ingestion';

const CATEGORY_ICON: Record<SourceCategory, typeof Database> = {
  database: Database,
  file: FileText,
  streaming: Webhook,
  cloud_storage: HardDrive,
  api: Network,
};

const HEALTH_COLOR: Record<SourceHealth, string> = {
  healthy: 'var(--color-emerald-400)',
  degraded: 'var(--color-amber-400)',
  failing: 'var(--color-rose-400)',
  idle: 'var(--color-text-faint)',
};

export function DataSources() {
  const {
    dataSources,
    ingestionRuns,
    schemaMappings,
    focusedSourceId,
    focusSource,
    setSourceStatus,
    triggerIngestionRun,
  } = useIntelStore();

  const [tab, setTab] = useState<Tab>('overview');
  const [showCatalog, setShowCatalog] = useState(false);

  const focused = useMemo(
    () => dataSources.find((s) => s.id === focusedSourceId) ?? dataSources[0],
    [dataSources, focusedSourceId]
  );

  // Aggregate stats
  const stats = useMemo(() => {
    const totalEntities = dataSources.reduce((a, s) => a + s.entitiesProduced, 0);
    const totalEdges = dataSources.reduce((a, s) => a + s.edgesProduced, 0);
    const totalRows = dataSources.reduce((a, s) => a + s.rowsIngested, 0);
    const active = dataSources.filter((s) => s.status === 'connected' || s.status === 'syncing').length;
    const failing = dataSources.filter((s) => s.health === 'failing' || s.health === 'degraded').length;
    return { active, total: dataSources.length, totalRows, totalEntities, totalEdges, failing };
  }, [dataSources]);

  // Sources grouped by category
  const grouped = useMemo(() => {
    const groups: Record<SourceCategory, DataSource[]> = {
      database: [],
      file: [],
      streaming: [],
      cloud_storage: [],
      api: [],
    };
    dataSources.forEach((s) => groups[s.category].push(s));
    return groups;
  }, [dataSources]);

  const runsForSource = useMemo(
    () => ingestionRuns.filter((r) => r.sourceId === focused?.id).slice(0, 20),
    [ingestionRuns, focused?.id]
  );

  return (
    <div className="fill overflow-hidden">
      <div className="absolute top-[56px] inset-x-0 z-10">
        <PageHeader
          icon={Workflow}
          eyebrow="data sources"
          title="Intelligence ingestion"
          meta={`${stats.active} of ${stats.total} connected · ${stats.totalEntities.toLocaleString()} entities · ${stats.totalEdges.toLocaleString()} edges`}
          action={
            <button
              onClick={() => setShowCatalog(true)}
              className="h-7 px-2.5 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
            >
              <Plus className="w-3 h-3" />
              connect source
            </button>
          }
        />
      </div>

      {/* Top stat strip */}
      <div className="absolute top-[100px] inset-x-0 px-3 z-10">
        <div className="grid grid-cols-6 gap-2">
          <Stat label="active sources" value={`${stats.active}/${stats.total}`} icon={CheckCircle2} tone="emerald" />
          <Stat label="rows ingested" value={formatBig(stats.totalRows)} icon={Activity} tone="ice" />
          <Stat label="entities" value={formatBig(stats.totalEntities)} icon={Boxes} tone="ice" />
          <Stat label="edges" value={formatBig(stats.totalEdges)} icon={GitBranch} tone="amber" />
          <Stat
            label="degraded / failing"
            value={String(stats.failing)}
            icon={AlertOctagon}
            tone={stats.failing > 0 ? 'rose' : 'emerald'}
          />
          <Stat label="topology coverage" value="94%" icon={ShieldCheck} tone="emerald" />
        </div>
      </div>

      {/* Body grid */}
      <div
        className="absolute inset-x-0 bottom-0 px-3 pb-3 pt-3"
        style={{
          top: 188,
          display: 'grid',
          gridTemplateColumns: '300px minmax(0, 1fr) 320px',
          gap: 8,
        }}
      >
        {/* LEFT — source rail grouped by category */}
        <div className="surface overflow-hidden flex flex-col min-h-0">
          <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
            <span className="heading-tactical">Sources</span>
            <span className="chip ml-auto text-[9px]">{stats.total}</span>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto scroll-tactical">
            {(Object.keys(grouped) as SourceCategory[]).map((cat) => {
              const items = grouped[cat];
              if (items.length === 0) return null;
              const Icon = CATEGORY_ICON[cat];
              return (
                <div key={cat}>
                  <div className="px-3 h-7 flex items-center gap-2 bg-[rgba(255,255,255,0.012)] border-b border-[var(--color-line-soft)] sticky top-0 z-[1]">
                    <Icon className="w-3 h-3 text-[var(--color-text-muted)]" />
                    <span className="font-mono text-[9px] tracking-[0.26em] uppercase text-[var(--color-text-muted)]">
                      {CATEGORY_LABEL[cat]}
                    </span>
                    <span className="chip ml-auto text-[8.5px]">{items.length}</span>
                  </div>
                  {items.map((s) => (
                    <SourceRow
                      key={s.id}
                      source={s}
                      active={s.id === focused?.id}
                      onClick={() => focusSource(s.id)}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        </div>

        {/* CENTER — focused source detail */}
        <div className="surface overflow-hidden flex flex-col min-h-0">
          {focused ? (
            <>
              <FocusedHeader
                source={focused}
                tab={tab}
                setTab={setTab}
                onTrigger={() => triggerIngestionRun(focused.id)}
                onTogglePause={() =>
                  setSourceStatus(
                    focused.id,
                    focused.status === 'paused' ? 'connected' : 'paused'
                  )
                }
              />
              <div className="flex-1 min-h-0 overflow-y-auto scroll-tactical">
                {tab === 'overview' && <OverviewTab source={focused} />}
                {tab === 'schema' && (
                  <SchemaMappingView
                    sourceId={focused.id}
                    mapping={schemaMappings[focused.id]}
                  />
                )}
                {tab === 'ingestion' && <IngestionTab runs={runsForSource} />}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              no source selected
            </div>
          )}
        </div>

        {/* RIGHT — data health */}
        <div className="surface overflow-hidden flex flex-col min-h-0">
          <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
            <ShieldCheck className="w-3 h-3 text-[var(--color-emerald-400)]" />
            <span className="heading-tactical">Data health</span>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto scroll-tactical p-3 space-y-3">
            <HealthGauge label="Topology completeness" value={0.94} />
            <HealthGauge label="Edge density" value={0.81} />
            <HealthGauge label="Relationship confidence" value={0.88} />
            <HealthGauge label="Schema coverage" value={0.92} />
            <div className="divider-h" />
            <SmallStat label="Orphan entities" value="12,402" tone="amber" />
            <SmallStat label="Duplicate suspects" value="3,118" tone="amber" />
            <SmallStat label="Unmapped fields" value="6" tone="ice" />
            <SmallStat label="Validation errors" value="14" tone="rose" />
            <div className="divider-h" />
            <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              recent advisories
            </div>
            <Advisory
              icon={AlertOctagon}
              tone="rose"
              title="Vendor risk webhook · 401 Unauthorized"
              body="rotate vault:vendor-risk-2024 · paged on-call"
            />
            <Advisory
              icon={Sparkles}
              tone="ice"
              title="GraphRAG suggests · merge 4 duplicate persons"
              body="Levenshtein + device-fingerprint match · conf 0.91"
            />
            <Advisory
              icon={FileJson}
              tone="amber"
              title="Card CSV · 14 malformed dates"
              body="auto-quarantine · retry tomorrow at 06:00 UTC"
            />
          </div>
        </div>
      </div>

      {/* Connect-source catalog overlay */}
      <AnimatePresence>
        {showCatalog && <ConnectCatalog onClose={() => setShowCatalog(false)} />}
      </AnimatePresence>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Stat({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
  tone: 'ice' | 'rose' | 'amber' | 'emerald';
}) {
  const color = {
    ice: 'var(--color-ice-400)',
    rose: 'var(--color-rose-400)',
    amber: 'var(--color-amber-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <div className="surface px-3 py-2">
      <div className="flex items-center gap-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.22em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <div className="font-mono text-[17px] font-light leading-none mt-1.5" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function SourceRow({
  source,
  active,
  onClick,
}: {
  source: DataSource;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-3 py-2 flex items-center gap-2.5 border-l-2 transition-colors',
        active
          ? 'bg-[rgba(34,211,238,0.06)] border-[var(--color-ice-500)]'
          : 'border-transparent hover:bg-[rgba(34,211,238,0.04)]'
      )}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: HEALTH_COLOR[source.health] }}
        title={source.health}
      />
      <div className="flex-1 min-w-0">
        <div className="text-[11.5px] text-[var(--color-text-bright)] truncate">
          {source.name}
        </div>
        <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] truncate">
          {KIND_LABEL[source.kind]} · {source.cadence.replace('_', ' ')}
        </div>
      </div>
      <SourceStatusChip status={source.status} />
    </button>
  );
}

function SourceStatusChip({ status }: { status: DataSource['status'] }) {
  const meta = {
    connected: { color: 'var(--color-emerald-400)', label: 'ok' },
    syncing: { color: 'var(--color-ice-400)', label: 'sync' },
    paused: { color: 'var(--color-text-muted)', label: 'paused' },
    error: { color: 'var(--color-rose-400)', label: 'error' },
    configured: { color: 'var(--color-text-secondary)', label: 'idle' },
  }[status];
  return (
    <span
      className="font-mono text-[8.5px] tracking-[0.22em] uppercase px-1.5 h-4 inline-flex items-center rounded-sm border shrink-0"
      style={{
        borderColor: `${meta.color}55`,
        color: meta.color,
        background: `${meta.color}0c`,
      }}
    >
      {meta.label}
    </span>
  );
}

/* -------------------------------------------------------------------------- */

function FocusedHeader({
  source,
  tab,
  setTab,
  onTrigger,
  onTogglePause,
}: {
  source: DataSource;
  tab: Tab;
  setTab: (t: Tab) => void;
  onTrigger: () => void;
  onTogglePause: () => void;
}) {
  return (
    <div className="border-b border-[var(--color-line-soft)]">
      <div className="px-3 py-2.5 flex items-start gap-3">
        <div
          className="w-8 h-8 rounded-sm border inline-flex items-center justify-center shrink-0"
          style={{
            borderColor: HEALTH_COLOR[source.health],
            color: HEALTH_COLOR[source.health],
            background: `${HEALTH_COLOR[source.health]}10`,
          }}
        >
          <Cpu className="w-3.5 h-3.5" strokeWidth={1.4} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium text-[var(--color-text-bright)] truncate">
              {source.name}
            </span>
            <SourceStatusChip status={source.status} />
          </div>
          <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mt-0.5 truncate">
            {KIND_LABEL[source.kind]} · {source.cadence.replace('_', ' ')} ·{' '}
            {source.region ?? 'multi-region'} · {source.owner}
          </div>
          <div className="text-[11px] text-[var(--color-text-secondary)] mt-1.5">
            {source.description}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
              uri
            </span>
            <code className="font-mono text-[10px] text-[var(--color-text-primary)] truncate">
              {source.uri}
            </code>
          </div>
        </div>
        <div className="flex flex-col gap-1.5 shrink-0">
          <button
            onClick={onTrigger}
            disabled={source.status === 'paused'}
            className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.22em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <RefreshCw className="w-3 h-3" />
            run now
          </button>
          <button
            onClick={onTogglePause}
            className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.22em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:text-[var(--color-violet-400)] hover:border-[rgba(168,85,247,0.4)]"
          >
            {source.status === 'paused' ? (
              <>
                <Play className="w-3 h-3" />
                resume
              </>
            ) : (
              <>
                <Pause className="w-3 h-3" />
                pause
              </>
            )}
          </button>
        </div>
      </div>
      {/* Tab strip */}
      <div className="px-2 h-8 flex items-center gap-1 border-t border-[var(--color-line-soft)]">
        {(['overview', 'schema', 'ingestion'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'h-6 px-2.5 rounded-sm font-mono text-[10px] tracking-[0.26em] uppercase',
              tab === t
                ? 'text-[var(--color-ice-400)] bg-[rgba(34,211,238,0.10)] border border-[rgba(34,211,238,0.32)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-transparent'
            )}
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function OverviewTab({ source }: { source: DataSource }) {
  return (
    <div className="p-3 space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <KV label="rows ingested" value={formatBig(source.rowsIngested)} />
        <KV label="entities produced" value={formatBig(source.entitiesProduced)} />
        <KV label="edges produced" value={formatBig(source.edgesProduced)} />
        <KV label="last sync" value={source.lastSyncAt ? formatTime(source.lastSyncAt) : '—'} />
        <KV label="connected" value={formatRelative(source.connectedAt)} />
        <KV label="recent errors" value={String(source.errorCount)} tone={source.errorCount > 0 ? 'rose' : 'emerald'} />
      </div>

      <div className="surface px-3 py-2">
        <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1.5">
          credentials · masked
        </div>
        <code className="font-mono text-[11px] text-[var(--color-text-primary)] block truncate">
          {source.credentialRef}
        </code>
      </div>

      <div className="surface px-3 py-2.5">
        <div className="flex items-center gap-2 mb-2">
          <Activity className="w-3 h-3 text-[var(--color-ice-400)]" />
          <span className="heading-tactical">Pipeline</span>
        </div>
        <PipelineFlow source={source} />
      </div>
    </div>
  );
}

function PipelineFlow({ source }: { source: DataSource }) {
  const steps = [
    { id: 'extract', label: 'Extract', icon: Database, sub: KIND_LABEL[source.kind] },
    { id: 'normalize', label: 'Normalize', icon: Workflow, sub: 'PII vaulted · UTF-8' },
    { id: 'map', label: 'Schema map', icon: GitBranch, sub: 'entity + edge rules' },
    { id: 'dedupe', label: 'Dedupe', icon: ShieldCheck, sub: 'fingerprint match' },
    { id: 'graph', label: 'Graph sync', icon: Network, sub: 'topology write' },
  ];
  return (
    <div className="flex items-stretch gap-2">
      {steps.map((s, i) => (
        <div key={s.id} className="flex items-center gap-2 flex-1 min-w-0">
          <div className="flex-1 px-2 py-2 rounded-sm border border-[var(--color-line-soft)] bg-[rgba(255,255,255,0.012)] min-w-0">
            <div className="flex items-center gap-1.5">
              <s.icon className="w-3 h-3 text-[var(--color-ice-400)]" />
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-secondary)] truncate">
                {s.label}
              </span>
            </div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] mt-0.5 truncate">
              {s.sub}
            </div>
          </div>
          {i < steps.length - 1 && (
            <span className="text-[var(--color-text-muted)] font-mono text-[10px] shrink-0">→</span>
          )}
        </div>
      ))}
    </div>
  );
}

function KV({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: 'rose' | 'emerald' | 'ice';
}) {
  const color = tone
    ? { rose: 'var(--color-rose-400)', emerald: 'var(--color-emerald-400)', ice: 'var(--color-ice-400)' }[tone]
    : 'var(--color-text-bright)';
  return (
    <div className="surface px-3 py-2">
      <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        {label}
      </div>
      <div
        className="font-mono text-[14px] font-light mt-0.5 truncate"
        style={{ color }}
      >
        {value}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function IngestionTab({ runs }: { runs: IngestionRun[] }) {
  if (runs.length === 0) {
    return (
      <div className="p-6 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        no ingestion runs yet
      </div>
    );
  }
  return (
    <div className="divide-y divide-[var(--color-line-soft)]">
      {runs.map((r) => (
        <div key={r.id} className="px-3 py-2.5">
          <div className="flex items-center gap-2">
            <RunStatusDot status={r.status} />
            <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              {r.id}
            </span>
            <span className="text-[11.5px] text-[var(--color-text-bright)]">
              {formatTime(r.startedAt)}
              {r.finishedAt && ` → ${formatTime(r.finishedAt)}`}
            </span>
            <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase">
              <RunStatusLabel status={r.status} />
            </span>
          </div>
          <div className="grid grid-cols-5 gap-1.5 mt-2 text-[10.5px]">
            <RunMetric label="rows" value={r.rowsRead.toLocaleString()} />
            <RunMetric label="+entities" value={`+${r.entitiesAdded.toLocaleString()}`} tone="ice" />
            <RunMetric label="+edges" value={`+${r.edgesAdded.toLocaleString()}`} tone="amber" />
            <RunMetric
              label="rings"
              value={`+${r.ringsDiscovered}`}
              tone={r.ringsDiscovered > 0 ? 'rose' : undefined}
            />
            <RunMetric
              label="hidden"
              value={`+${r.hiddenLinksFound}`}
              tone={r.hiddenLinksFound > 0 ? 'violet' : undefined}
            />
          </div>
          {r.log.length > 0 && (
            <div className="mt-2 font-mono text-[10px] text-[var(--color-text-muted)] space-y-0.5">
              {r.log.map((l, i) => (
                <div key={i} className="truncate">
                  <span className="text-[var(--color-text-faint)]">›</span> {l}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function RunStatusDot({ status }: { status: IngestionRun['status'] }) {
  const color = {
    queued: 'var(--color-text-faint)',
    running: 'var(--color-ice-400)',
    success: 'var(--color-emerald-400)',
    partial: 'var(--color-amber-400)',
    failed: 'var(--color-rose-400)',
  }[status];
  return (
    <span className="relative inline-flex w-1.5 h-1.5">
      {status === 'running' && (
        <span
          className="absolute inset-0 rounded-full anim-pulse-ring"
          style={{ background: color }}
        />
      )}
      <span
        className="relative inline-flex w-1.5 h-1.5 rounded-full"
        style={{ background: color }}
      />
    </span>
  );
}

function RunStatusLabel({ status }: { status: IngestionRun['status'] }) {
  const meta = {
    queued: { label: 'queued', color: 'var(--color-text-muted)' },
    running: { label: 'running', color: 'var(--color-ice-400)' },
    success: { label: '✓ success', color: 'var(--color-emerald-400)' },
    partial: { label: '◑ partial', color: 'var(--color-amber-400)' },
    failed: { label: '✕ failed', color: 'var(--color-rose-400)' },
  }[status];
  return <span style={{ color: meta.color }}>{meta.label}</span>;
}

function RunMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: 'ice' | 'amber' | 'rose' | 'violet';
}) {
  const color = tone
    ? {
        ice: 'var(--color-ice-400)',
        amber: 'var(--color-amber-400)',
        rose: 'var(--color-rose-400)',
        violet: 'var(--color-violet-400)',
      }[tone]
    : 'var(--color-text-primary)';
  return (
    <div className="rounded-sm bg-[rgba(255,255,255,0.012)] border border-[var(--color-line-soft)] px-1.5 py-1">
      <div className="font-mono text-[8.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
        {label}
      </div>
      <div className="font-mono text-[11px]" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Right-side helpers                                                         */
/* -------------------------------------------------------------------------- */

function HealthGauge({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    value >= 0.9
      ? 'var(--color-emerald-400)'
      : value >= 0.75
      ? 'var(--color-ice-400)'
      : value >= 0.55
      ? 'var(--color-amber-400)'
      : 'var(--color-rose-400)';
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {label}
        </span>
        <span className="font-mono text-[11px]" style={{ color: tone }}>
          {pct}%
        </span>
      </div>
      <div className="h-1 mt-1 rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="h-full"
          style={{ background: tone }}
        />
      </div>
    </div>
  );
}

function SmallStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'rose' | 'amber' | 'ice' | 'emerald';
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    amber: 'var(--color-amber-400)',
    ice: 'var(--color-ice-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
        {label}
      </span>
      <span className="font-mono text-[12px]" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

function Advisory({
  icon: Icon,
  tone,
  title,
  body,
}: {
  icon: typeof Activity;
  tone: 'rose' | 'amber' | 'ice';
  title: string;
  body: string;
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    amber: 'var(--color-amber-400)',
    ice: 'var(--color-ice-400)',
  }[tone];
  return (
    <div className="rounded-sm bg-[rgba(255,255,255,0.012)] border-l-2 px-2 py-1.5" style={{ borderColor: color }}>
      <div className="flex items-center gap-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        <span className="text-[11px] text-[var(--color-text-primary)] truncate">{title}</span>
      </div>
      <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">{body}</div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Connect-source catalog                                                     */
/* -------------------------------------------------------------------------- */

function ConnectCatalog({ onClose }: { onClose: () => void }) {
  const groups: Record<SourceCategory, SourceKind[]> = {
    database: [],
    file: [],
    streaming: [],
    cloud_storage: [],
    api: [],
  };
  AVAILABLE_KINDS.forEach((k) => groups[KIND_TO_CATEGORY[k]].push(k));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-[80] flex items-center justify-center"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="absolute inset-0 bg-[rgba(0,0,3,0.55)] backdrop-blur-sm" />
      <motion.div
        initial={{ y: 14, opacity: 0, scale: 0.98 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 6, opacity: 0 }}
        transition={{ duration: 0.22 }}
        className="relative surface-floating w-[800px] max-w-[92vw] max-h-[80vh] overflow-hidden"
      >
        <div className="h-10 px-4 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
          <Plus className="w-3.5 h-3.5 text-[var(--color-ice-400)]" />
          <span className="heading-tactical">Connect a source</span>
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] ml-2">
            {AVAILABLE_KINDS.length} connectors available
          </span>
          <button
            onClick={onClose}
            className="ml-auto w-6 h-6 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[rgba(148,163,184,0.06)]"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="p-3 max-h-[68vh] overflow-y-auto scroll-tactical">
          {(Object.keys(groups) as SourceCategory[]).map((cat) => {
            const items = groups[cat];
            const Icon = CATEGORY_ICON[cat];
            return (
              <div key={cat} className="mb-4 last:mb-0">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-3 h-3 text-[var(--color-text-muted)]" />
                  <span className="heading-tactical">{CATEGORY_LABEL[cat]}</span>
                  <span className="chip ml-auto text-[8.5px]">{items.length}</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {items.map((k) => (
                    <button
                      key={k}
                      className="text-left px-3 py-2.5 rounded-sm border border-[var(--color-line-soft)] hover:border-[rgba(34,211,238,0.32)] hover:bg-[rgba(34,211,238,0.04)] transition-colors"
                    >
                      <div className="text-[12px] text-[var(--color-text-bright)]">
                        {KIND_LABEL[k]}
                      </div>
                      <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mt-0.5">
                        connect → map → ingest
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        <div className="h-10 px-4 flex items-center gap-2 border-t border-[var(--color-line-soft)] font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          all connectors honor your vault-stored credentials · PII never leaves the source
          <span className="ml-auto">
            <span className="kbd text-[8.5px]">ESC</span> close
          </span>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */

function formatBig(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return `${Math.round(ms / 1000)}s ago`;
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.round(ms / 3_600_000)}h ago`;
  return `${Math.round(ms / 86_400_000)}d ago`;
}
