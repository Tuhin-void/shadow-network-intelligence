import { AlertTriangle, Database } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * SyntheticScenarioRibbon — a thin, honest top-of-page banner that tells
 * the operator a surface is rendering pre-built explanatory data rather
 * than live TigerGraph evidence.
 *
 * Used on pages that read from the curated preset corpus (Alerts, Rings,
 * Entities, Reports, Replay, Simulate, Autopilot, SessionVault). The
 * label is intentionally subtle — the worldspace aesthetic is preserved
 * but the credibility contract is honored: a judge can never confuse a
 * scenario walkthrough for live structural evidence.
 *
 * Two intensities:
 *   - `default`: standard amber ribbon for explanatory surfaces
 *   - `whisper`: low-intensity for surfaces that already make context clear
 */
export function SyntheticScenarioRibbon({
  label = 'synthetic scenario',
  hint,
  whisper = false,
}: {
  label?: string;
  hint?: string;
  whisper?: boolean;
}) {
  return (
    <div
      className={cn(
        // Self-positioning at the top of the viewport, below FloatingNav
        // (z-60) and above page content. Pages that import this don't have
        // to restructure their layout.
        'fixed top-[60px] left-0 right-0 z-[35] border-b backdrop-blur-md',
        whisper
          ? 'border-[rgba(245,158,11,0.12)] bg-[rgba(7,9,14,0.85)]'
          : 'border-[rgba(245,158,11,0.18)] bg-[rgba(7,9,14,0.9)]',
      )}
      role="note"
    >
      <div className="max-w-[1480px] mx-auto px-6 py-1.5 flex items-center gap-2.5 flex-wrap">
        <AlertTriangle className="w-3 h-3 text-[var(--color-amber-400)] shrink-0" />
        <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-amber-400)] shrink-0">
          {label}
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1 shrink-0">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          explanatory surface · not live graph evidence
        </span>
        {hint && (
          <>
            <span className="text-[var(--color-text-ghost)] mx-1 shrink-0 hidden md:inline">·</span>
            <span className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] hidden md:inline">
              {hint}
            </span>
          </>
        )}
        <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] inline-flex items-center gap-1 shrink-0">
          <Database className="w-2.5 h-2.5" />
          live investigations · /home /investigate /benchmark
        </span>
      </div>
    </div>
  );
}
