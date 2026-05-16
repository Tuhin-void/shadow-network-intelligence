import { useEffect, useState } from 'react';
import {
  Play,
  Square,
  RotateCcw,
  FastForward,
  Clock,
  Activity,
  ChevronLeft,
  ChevronRight,
  Hand,
  Zap,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { cn, formatTime } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';
import { StatusIndicator } from '@/components/shared/StatusIndicator';
import { BackendStatusPill } from '@/components/shared/BackendStatusPill';
import { CommandBar } from '@/components/investigation/CommandBar';

const SPEEDS: Array<0.5 | 1 | 2 | 4> = [0.5, 1, 2, 4];

export function TopBar() {
  const {
    active,
    events,
    streamingPhase,
    progress,
    speed,
    runMode,
    stepIndex,
    startStream,
    stopStream,
    resetStream,
    setSpeed,
    setRunMode,
    stepForward,
    stepBack,
  } = useIntelStore();

  const totalSteps = active.stream.length;

  const last = events[events.length - 1];

  // Heartbeat clock for tactical feel
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="h-12 shrink-0 flex items-center px-3 gap-3 bg-[var(--color-graphite-900)] border-b border-[var(--color-line)] relative">
      {/* Preset breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--color-text-muted)]">
          PRESET
        </span>
        <span className="font-medium text-[12px] text-[var(--color-text-bright)] truncate">
          {active.label}
        </span>
        <span className="chip hidden md:inline-flex">{active.id}</span>
      </div>

      <div className="w-px h-5 bg-[var(--color-line)] mx-1" />

      {/* Mode toggle: AUTO vs MANUAL */}
      <div className="flex items-center gap-0.5 panel-soft p-0.5">
        <button
          onClick={() => setRunMode('auto')}
          className={cn(
            'h-6 px-2 inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider rounded-sm',
            runMode === 'auto'
              ? 'bg-[rgba(34,211,238,0.12)] text-[var(--color-ice-400)]'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
          )}
          title="Auto: stream plays automatically"
        >
          <Zap className="w-3 h-3" />
          Auto
        </button>
        <button
          onClick={() => setRunMode('manual')}
          className={cn(
            'h-6 px-2 inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider rounded-sm',
            runMode === 'manual'
              ? 'bg-[rgba(168,85,247,0.14)] text-[var(--color-violet-400)]'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
          )}
          title="Manual: step through events"
        >
          <Hand className="w-3 h-3" />
          Manual
        </button>
      </div>

      {/* Stream controls — different per mode */}
      <div className="flex items-center gap-1">
        {runMode === 'auto' ? (
          <>
            {streamingPhase !== 'streaming' ? (
              <button
                onClick={startStream}
                className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[11px] font-medium rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)] transition-colors"
              >
                <Play className="w-3 h-3" />
                LAUNCH
              </button>
            ) : (
              <button
                onClick={stopStream}
                className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[11px] font-medium rounded-sm border border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.06)] text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.1)] transition-colors"
              >
                <Square className="w-3 h-3" />
                ABORT
              </button>
            )}
            <div className="flex items-center gap-0.5 ml-1 panel-soft p-0.5">
              <FastForward className="w-3 h-3 text-[var(--color-text-muted)] mx-1" />
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  className={cn(
                    'h-6 px-2 text-[10px] font-mono rounded-sm',
                    speed === s
                      ? 'bg-[rgba(34,211,238,0.12)] text-[var(--color-ice-400)]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                  )}
                >
                  {s}x
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <button
              onClick={stepBack}
              disabled={stepIndex === 0}
              className="h-7 w-7 inline-flex items-center justify-center rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:bg-[rgba(168,85,247,0.06)] hover:border-[rgba(168,85,247,0.35)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Step back"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={stepForward}
              disabled={stepIndex >= totalSteps}
              className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[11px] font-medium rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-400)] hover:bg-[rgba(168,85,247,0.1)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Step forward"
            >
              <ChevronRight className="w-3 h-3" />
              STEP
              <span className="font-mono text-[10px] text-[var(--color-text-muted)] ml-1">
                {stepIndex}/{totalSteps}
              </span>
            </button>
          </>
        )}
        <button
          onClick={resetStream}
          className="h-7 w-7 inline-flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] rounded-sm hover:bg-[rgba(148,163,184,0.06)] transition-colors"
          aria-label="Reset"
        >
          <RotateCcw className="w-3 h-3" />
        </button>
      </div>

      {/* Tactical research command bar */}
      <div className="w-[300px] shrink-0 ml-2">
        <CommandBar />
      </div>

      {/* Streaming event ticker */}
      <div className="flex-1 min-w-0 mx-2 h-7 panel-soft overflow-hidden relative">
        <div className="absolute inset-0 flex items-center pl-3 pr-3 gap-2 min-w-0">
          <Activity
            className={cn(
              'w-3 h-3 shrink-0',
              streamingPhase === 'streaming'
                ? 'text-[var(--color-ice-400)] anim-drift'
                : 'text-[var(--color-text-muted)]'
            )}
            strokeWidth={1.5}
          />
          <span className="label-tactical shrink-0">EVENT</span>
          <AnimatePresence mode="popLayout">
            {last ? (
              <motion.span
                key={last.id}
                initial={{ x: 12, opacity: 0, filter: 'blur(3px)' }}
                animate={{ x: 0, opacity: 1, filter: 'blur(0)' }}
                exit={{ x: -12, opacity: 0 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                className="font-mono text-[11px] text-[var(--color-text-primary)] truncate min-w-0"
              >
                <span className="text-[var(--color-text-muted)]">
                  [{String(last.seq).padStart(3, '0')}]
                </span>{' '}
                <span className="text-[var(--color-ice-400)]">{last.kind}</span>{' '}
                {last.title}
              </motion.span>
            ) : (
              <span className="font-mono text-[11px] text-[var(--color-text-muted)] truncate">
                idle • {runMode === 'auto' ? 'awaiting LAUNCH' : 'press STEP to advance'}
              </span>
            )}
          </AnimatePresence>
          <span className="ml-auto font-mono text-[10px] text-[var(--color-text-muted)] shrink-0">
            {events.length} events
          </span>
        </div>
      </div>

      {/* Stream phase */}
      <StatusIndicator
        status={
          streamingPhase === 'streaming'
            ? 'streaming'
            : streamingPhase === 'complete'
            ? 'complete'
            : 'idle'
        }
        label={`${Math.round(progress * 100)}%`}
      />

      {/* Backend connection — live orchestrator probe */}
      <div className="ml-1">
        <BackendStatusPill compact />
      </div>

      {/* Clock */}
      <div className="flex items-center gap-2 ml-2 pl-3 border-l border-[var(--color-line)]">
        <Clock className="w-3 h-3 text-[var(--color-text-muted)]" strokeWidth={1.5} />
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-text-secondary)]">
          {formatTime(now.toISOString())} UTC
        </span>
      </div>
    </header>
  );
}
