import { CheckCircle2, XCircle } from 'lucide-react';
import type {
  BackendEnvironmentReadiness,
  BackendEnvironmentReadinessSignal,
} from '@/lib/api-client';
import { cn } from '@/lib/utils';

/**
 * EnvironmentReadinessStrip — single operational verdict surface for the
 * Sources page. Reads directly from the backend's structured `readiness`
 * block (graph / topology / retrieval / benchmark / reasoning).
 *
 * Hard contracts:
 *   • If `readiness` is missing (older backend), render nothing — never
 *     fabricate green dots.
 *   • Honest tone-down: when ANY signal is not-ready, the strip degrades
 *     to amber/rose so the rest of the page can't claim "ready".
 *   • Tooltips show the backend's `reason` string verbatim — no
 *     paraphrasing, no synthesized prose.
 */
export function EnvironmentReadinessStrip({
  readiness,
  investigationReady,
  freshProbe,
  probeFailed,
  reconnectAttempted,
}: {
  readiness?: BackendEnvironmentReadiness | null;
  investigationReady?: boolean | null;
  freshProbe?: boolean | null;
  probeFailed?: boolean | null;
  reconnectAttempted?: boolean | null;
}) {
  if (!readiness) return null;

  const signals: Array<{ key: keyof BackendEnvironmentReadiness; label: string }> = [
    { key: 'graph',     label: 'graph' },
    { key: 'topology',  label: 'topology' },
    { key: 'retrieval', label: 'retrieval' },
    { key: 'benchmark', label: 'benchmark' },
    { key: 'reasoning', label: 'reasoning' },
  ];

  const verdict = investigationReady
    ? { color: 'var(--color-emerald-400)', label: 'investigation-ready' }
    : { color: 'var(--color-rose-400)', label: 'degraded' };

  return (
    <div
      className="panel-soft px-3 py-2 flex items-center gap-3 flex-wrap"
      style={{ borderLeft: `2px solid ${verdict.color}` }}
    >
      <div className="flex items-center gap-1.5 shrink-0">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: verdict.color }}
        />
        <span
          className="font-mono text-[9.5px] tracking-[0.32em] uppercase"
          style={{ color: verdict.color }}
        >
          {verdict.label}
        </span>
      </div>

      <div className="h-3 w-px bg-[var(--color-line-soft)]" />

      <div className="flex items-center gap-2 flex-wrap">
        {signals.map(({ key, label }) => (
          <SignalDot key={key} label={label} signal={readiness[key]} />
        ))}
      </div>

      {(freshProbe || probeFailed || reconnectAttempted) && (
        <>
          <div className="h-3 w-px bg-[var(--color-line-soft)] hidden md:block" />
          <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] flex items-center gap-2 flex-wrap">
            {freshProbe && !probeFailed && (
              <span className="text-[var(--color-ice-400)]">probe ✓</span>
            )}
            {probeFailed && (
              <span className="text-[var(--color-rose-400)]">probe failed</span>
            )}
            {reconnectAttempted && (
              <span className="text-[var(--color-amber-400)]">self-heal attempted</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SignalDot({
  label,
  signal,
}: {
  label: string;
  signal: BackendEnvironmentReadinessSignal;
}) {
  const color = signal.ready ? 'var(--color-emerald-400)' : 'var(--color-rose-400)';
  const Icon = signal.ready ? CheckCircle2 : XCircle;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 h-5 px-1.5 rounded-sm font-mono text-[9px] tracking-[0.22em] uppercase',
      )}
      style={{ color, background: `${color}0d`, borderColor: `${color}55` }}
      title={signal.reason}
    >
      <Icon className="w-2.5 h-2.5" />
      {label}
    </span>
  );
}
