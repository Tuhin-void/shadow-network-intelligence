import { useEffect, useMemo, useState } from 'react';
import { Activity, Cloud, CloudOff, Database, Zap } from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';

/**
 * Backend connection pill — tactical chip showing live-orchestrator state.
 *
 * Renders one of four operational modes:
 *   • LIVE     — orchestrator reachable + TigerGraph online
 *   • TG-OFF   — orchestrator reachable + TigerGraph in offline fallback
 *   • RECONN   — probe in flight (first paint or after error)
 *   • OFFLINE  — orchestrator unreachable (frontend stays on mock)
 *
 * Auto-probes every 20s. Manual refresh on click.
 */
export function BackendStatusPill({ compact = false }: { compact?: boolean }) {
  const status = useIntelStore((s) => s.backendStatus);
  const error = useIntelStore((s) => s.backendError);
  const check = useIntelStore((s) => s.checkBackend);
  const loadPresets = useIntelStore((s) => s.loadLivePresets);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      await check();
      // Lazy-load presets once we know the backend is alive.
      if (!cancelled && useIntelStore.getState().backendStatus &&
          useIntelStore.getState().livePresets.length === 0) {
        await loadPresets();
      }
    };
    tick();
    const id = setInterval(tick, 20_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [check, loadPresets]);

  const mode = useMemo(() => {
    if (!status) return error ? 'OFFLINE' : 'RECONN';
    return status.tigergraphOffline ? 'TG-OFF' : 'LIVE';
  }, [status, error]);

  const palette = MODE_PALETTE[mode];
  const Icon = palette.icon;

  return (
    <div className="relative">
      <button
        onClick={() => {
          setOpen((v) => !v);
          void check();
        }}
        className={cn(
          'h-7 inline-flex items-center gap-1.5 rounded-sm border px-2 transition-colors',
          palette.border,
          palette.bg,
          'hover:brightness-110',
        )}
        title="Backend connection · click to refresh"
      >
        <Icon className={cn('w-3 h-3', palette.text)} strokeWidth={1.5} />
        <span
          className={cn(
            'font-mono text-[10px] tracking-[0.22em] uppercase',
            palette.text,
          )}
        >
          {mode}
        </span>
        {!compact && status?.cache && (
          <span className="font-mono text-[9px] text-[var(--color-text-muted)] ml-1">
            ⟡ {Math.round(status.cache.hitRate * 100)}%
          </span>
        )}
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full ml-0.5',
            status ? 'bg-[var(--color-emerald-400)]' : 'bg-[var(--color-rose-400)]',
            status && 'anim-drift',
          )}
        />
      </button>

      {open && (
        <div
          className="absolute top-9 right-0 w-[280px] surface p-3 z-50 shadow-lg"
          onMouseLeave={() => setOpen(false)}
        >
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-[var(--color-line-soft)]">
            <Icon className={cn('w-3.5 h-3.5', palette.text)} strokeWidth={1.5} />
            <span className={cn('label-tactical', palette.text)}>
              {palette.headline}
            </span>
            <button
              onClick={() => check()}
              className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
            >
              refresh
            </button>
          </div>

          {status ? (
            <>
              <Row label="orchestrator" value="reachable" tone="emerald" />
              <Row
                label="tigergraph"
                value={status.tigergraphOffline ? 'offline fallback' : 'online'}
                tone={status.tigergraphOffline ? 'amber' : 'emerald'}
              />
              <Row
                label="prewarm"
                value={
                  status.prewarm.error
                    ? `error · ${status.prewarm.error.slice(0, 48)}`
                    : `${status.prewarm.warmed} entities${
                        status.prewarm.elapsedSec
                          ? ` · ${status.prewarm.elapsedSec.toFixed(1)}s`
                          : ''
                      }`
                }
                tone={status.prewarm.error ? 'rose' : 'ice'}
              />
              <Row
                label="cache"
                value={`${status.cache.hits} hits · ${status.cache.misses} miss`}
                tone="ice"
              />
              <Row
                label="sessions"
                value={`${status.sessionCount} active`}
                tone="ice"
              />
              <div className="mt-2 pt-2 border-t border-[var(--color-line-soft)]">
                <div className="font-mono text-[9px] text-[var(--color-text-muted)]">
                  last probe · {new Date(status.lastCheckedAt).toLocaleTimeString()}
                </div>
              </div>
            </>
          ) : (
            <>
              <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
                Orchestrator API is unreachable. The interface stays operational
                on mock fixtures — start the FastAPI server to enable live
                investigations.
              </p>
              {error && (
                <p className="font-mono text-[9.5px] text-[var(--color-rose-400)] mt-2 break-all">
                  {error.slice(0, 220)}
                </p>
              )}
              <div className="mt-3 panel-soft p-2">
                <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mb-1">
                  start command
                </div>
                <code className="font-mono text-[10.5px] text-[var(--color-ice-300)]">
                  uvicorn 4_orchestrator_api.main:app --port 8000
                </code>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'emerald' | 'amber' | 'ice' | 'rose';
}) {
  const color =
    tone === 'emerald'
      ? 'var(--color-emerald-400)'
      : tone === 'amber'
      ? 'var(--color-amber-400)'
      : tone === 'rose'
      ? 'var(--color-rose-400)'
      : 'var(--color-ice-400)';
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] w-[80px] shrink-0">
        {label}
      </span>
      <span className="font-mono text-[10.5px] truncate" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

const MODE_PALETTE: Record<
  string,
  {
    icon: typeof Activity;
    text: string;
    border: string;
    bg: string;
    headline: string;
  }
> = {
  LIVE: {
    icon: Zap,
    text: 'text-[var(--color-emerald-400)]',
    border: 'border-[rgba(16,185,129,0.4)]',
    bg: 'bg-[rgba(16,185,129,0.06)]',
    headline: 'Live · orchestrator + TigerGraph',
  },
  'TG-OFF': {
    icon: Database,
    text: 'text-[var(--color-amber-400)]',
    border: 'border-[rgba(245,158,11,0.4)]',
    bg: 'bg-[rgba(245,158,11,0.06)]',
    headline: 'Orchestrator live · TG offline fallback',
  },
  RECONN: {
    icon: Cloud,
    text: 'text-[var(--color-ice-400)]',
    border: 'border-[rgba(34,211,238,0.4)]',
    bg: 'bg-[rgba(34,211,238,0.06)]',
    headline: 'Probing orchestrator…',
  },
  OFFLINE: {
    icon: CloudOff,
    text: 'text-[var(--color-rose-400)]',
    border: 'border-[rgba(244,63,94,0.35)]',
    bg: 'bg-[rgba(244,63,94,0.05)]',
    headline: 'Orchestrator unreachable',
  },
};
