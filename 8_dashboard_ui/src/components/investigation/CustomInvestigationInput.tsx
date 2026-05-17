import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  CornerDownLeft,
  Square,
  Target,
  Zap,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';
import { IntentChip } from './IntentChip';

/**
 * Custom investigation entrypoint — a single tactical input field that
 * runs an ad-hoc natural-language query through the REAL backend
 * (`/investigate/deep/stream`).
 *
 * Hard constraints (NOT a chatbot):
 *   • single line input
 *   • no message history, no avatars, no typing bubbles
 *   • no conversational UX
 *   • the unfolding investigation appears in the existing graph + timeline +
 *     cognitive surfaces — not in a chat transcript
 *
 * The investigation is REAL: cold latency ~7-23s against TigerGraph; warm
 * cache returns in <2s. SSE events stream into the same pipeline that
 * powers the curated preset flow.
 */
export function CustomInvestigationInput({
  variant = 'launchpad',
  autoNavigate = true,
}: {
  /** 'launchpad' = full card layout (used inside LiveLaunchpad on Home)
   *  'inline'    = compact one-row layout (used inside Manual workstation header) */
  variant?: 'launchpad' | 'inline';
  /** When true, navigates to /investigate after submit so the unfolding
   *  investigation is in view immediately. */
  autoNavigate?: boolean;
}) {
  const navigate = useNavigate();
  const backendStatus = useIntelStore((s) => s.backendStatus);
  const cognitivePhase = useIntelStore((s) => s.cognitivePhase);
  const cognitiveError = useIntelStore((s) => s.cognitiveError);
  const liveStreamPhase = useIntelStore((s) => s.liveStreamPhase);
  const runCustom = useIntelStore((s) => s.runCustomDeepStream);
  const stopCustom = useIntelStore((s) => s.stopCustomDeepStream);
  const history = useIntelStore((s) => s.customQueryHistory);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const [q, setQ] = useState('');
  // Rotating placeholder — calm cycle through topology-aware hints
  // so the input subtly teaches what kinds of investigations work best.
  const [hintIndex, setHintIndex] = useState(0);
  useEffect(() => {
    if (q || cognitivePhase === 'running' || liveStreamPhase === 'streaming') return;
    const id = setInterval(() => {
      setHintIndex((i) => (i + 1) % SUGGESTIONS.length);
    }, 4200);
    return () => clearInterval(id);
  }, [q, cognitivePhase, liveStreamPhase]);
  const rotatingPlaceholder = useMemo(
    () => `e.g. ${SUGGESTIONS[hintIndex]}`,
    [hintIndex],
  );

  const isRunning = cognitivePhase === 'running' || liveStreamPhase === 'streaming';
  const isOffline = !backendStatus;
  const canSubmit = !!q.trim() && !isOffline && !isRunning;

  const submit = async () => {
    const trimmed = q.trim();
    if (!trimmed) return;
    if (autoNavigate) navigate('/investigate');
    await runCustom(trimmed, { top_k: 5, depth: 2 });
  };

  // Kbd shortcut: Ctrl/Cmd+K focuses the input (only the launchpad variant).
  useEffect(() => {
    if (variant !== 'launchpad') return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [variant]);

  // ── Inline variant — one row, no card ───────────────────────────────────
  if (variant === 'inline') {
    return (
      <div className="flex items-center gap-2 panel-soft px-2 h-7 border border-[rgba(34,211,238,0.18)]">
        <Target className="w-3 h-3 text-[var(--color-ice-400)] shrink-0" />
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && canSubmit) submit();
          }}
          placeholder={
            isOffline
              ? 'orchestrator offline — start backend on :8000'
              : rotatingPlaceholder
          }
          disabled={isOffline || isRunning}
          className={cn(
            'flex-1 bg-transparent border-0 outline-none',
            'font-mono text-[11px] text-[var(--color-text-bright)]',
            'placeholder:text-[var(--color-text-muted)] placeholder:tracking-wider',
            'disabled:opacity-50',
          )}
        />
        {isRunning ? (
          <button
            onClick={stopCustom}
            className="h-5 px-2 inline-flex items-center gap-1 rounded-sm border border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.05)] text-[var(--color-rose-400)] text-[9px] font-mono tracking-[0.22em] uppercase"
            title="Abort the in-flight investigation"
          >
            <Square className="w-2.5 h-2.5" />
            abort
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!canSubmit}
            className={cn(
              'h-5 px-2 inline-flex items-center gap-1 rounded-sm text-[9px] font-mono tracking-[0.22em] uppercase',
              canSubmit
                ? 'border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.12)]'
                : 'border border-[var(--color-line)] text-[var(--color-text-muted)] cursor-not-allowed',
            )}
          >
            run
            <CornerDownLeft className="w-2.5 h-2.5" />
          </button>
        )}
      </div>
    );
  }

  // ── Launchpad variant — full card ───────────────────────────────────────
  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Target className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="heading-tactical">Custom investigation</span>
        <span className="chip text-[8.5px] inline-flex items-center gap-1 border-[rgba(34,211,238,0.32)] text-[var(--color-ice-400)]">
          <Zap className="w-2.5 h-2.5" />
          real GraphRAG · SSE stream
        </span>
        <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {phaseLabel(cognitivePhase, liveStreamPhase, isOffline)}
        </span>
      </div>

      <div className="px-3 py-3">
        <div
          className={cn(
            'flex items-center gap-2 panel-soft pl-3 pr-1 h-10 transition-colors',
            isRunning && 'border-[rgba(34,211,238,0.25)] bg-[rgba(34,211,238,0.04)]',
          )}
        >
          <Target className="w-3.5 h-3.5 text-[var(--color-ice-400)] shrink-0" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && canSubmit) submit();
            }}
            placeholder={
              isOffline
                ? 'orchestrator offline — start backend on :8000'
                : rotatingPlaceholder
            }
            disabled={isOffline || isRunning}
            className={cn(
              'flex-1 bg-transparent border-0 outline-none',
              'text-[12.5px] text-[var(--color-text-bright)]',
              'placeholder:text-[var(--color-text-muted)] placeholder:tracking-wide',
              'disabled:opacity-50',
            )}
          />
          {isRunning ? (
            <button
              onClick={stopCustom}
              className="h-8 px-3 inline-flex items-center gap-1.5 rounded-sm border border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.06)] text-[var(--color-rose-400)] text-[10px] font-mono tracking-[0.26em] uppercase hover:bg-[rgba(244,63,94,0.12)]"
              title="Abort the in-flight investigation"
            >
              <Square className="w-3 h-3" />
              abort
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={!canSubmit}
              className={cn(
                'h-8 px-3 inline-flex items-center gap-1.5 rounded-sm text-[10px] font-mono tracking-[0.26em] uppercase',
                canSubmit
                  ? 'border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.12)]'
                  : 'border border-[var(--color-line)] text-[var(--color-text-muted)] cursor-not-allowed',
              )}
            >
              run
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Intent preview — debounced backend classification. Shows the
            mapped workflow + entity IDs detected. When intent is 'unknown'
            it surfaces operational suggestions instead of chatbot prose. */}
        {q.trim() && (
          <div className="mt-2">
            <IntentChip
              query={q}
              onPickSuggestion={(seed) => {
                setQ(seed);
                inputRef.current?.focus();
              }}
            />
          </div>
        )}

        {/* Suggestion chips — clicking populates the input. These are not
            curated presets; they're hint examples. */}
        <div className="flex flex-wrap gap-1 mt-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => {
                setQ(s);
                inputRef.current?.focus();
              }}
              disabled={isRunning || isOffline}
              className="chip text-[9px] hover:bg-[rgba(34,211,238,0.06)] hover:border-[rgba(34,211,238,0.32)] hover:text-[var(--color-ice-400)] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Session history — click any prior query to re-run.
            Only renders when the operator has submitted at least one query
            this session, so the UI stays clean for first-time users. */}
        {history.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--color-line-soft)]">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Clock className="w-3 h-3 text-[var(--color-text-muted)]" />
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                recent · session history
              </span>
              <span className="ml-auto font-mono text-[9px] text-[var(--color-text-muted)]">
                {history.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {history.slice(0, 5).map((h) => (
                <button
                  key={h}
                  onClick={async () => {
                    setQ(h);
                    if (autoNavigate) navigate('/investigate');
                    await runCustom(h, { top_k: 5, depth: 2 });
                  }}
                  disabled={isRunning || isOffline}
                  className="chip text-[9.5px] inline-flex items-center gap-1 max-w-[280px] truncate hover:bg-[rgba(168,85,247,0.06)] hover:border-[rgba(168,85,247,0.32)] hover:text-[var(--color-violet-400)] disabled:opacity-40 disabled:cursor-not-allowed"
                  title={`re-run: ${h}`}
                >
                  <span className="text-[var(--color-text-muted)]">↻</span>
                  <span className="truncate">{h}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Status / error */}
        {cognitivePhase === 'error' && cognitiveError && (
          <div className="mt-2 flex items-start gap-2 panel-soft p-2 border-l-2 border-[var(--color-rose-500)]">
            <AlertTriangle className="w-3 h-3 text-[var(--color-rose-400)] mt-0.5 shrink-0" />
            <span className="font-mono text-[10.5px] text-[var(--color-rose-300)] break-all">
              {cognitiveError.slice(0, 240)}
            </span>
          </div>
        )}
      </div>

      <div className="px-3 py-2 border-t border-[var(--color-line-soft)] font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] flex items-center gap-2">
        <kbd className="kbd text-[8.5px]">Ctrl</kbd>
        <span>+</span>
        <kbd className="kbd text-[8.5px]">K</kbd>
        <span className="ml-1">to focus</span>
        <span className="ml-auto">
          query → POST /api/v1/investigate/deep/stream → TigerGraph traversal
        </span>
      </div>
    </section>
  );
}

const SUGGESTIONS = [
  'Trace laundering paths connected to FR-002',
  'Find shared-device fraud clusters',
  'Identify intermediary shell companies',
  'Expand ownership chains around P-005027',
  'Detect persons in multiple rings',
];

function phaseLabel(
  cognitive: string,
  stream: string,
  offline: boolean,
): string {
  if (offline) return 'BACKEND OFFLINE';
  if (cognitive === 'running' || stream === 'streaming') return 'STREAMING';
  if (cognitive === 'complete') return 'COMPLETE';
  if (cognitive === 'error') return 'ERROR';
  return 'IDLE';
}
