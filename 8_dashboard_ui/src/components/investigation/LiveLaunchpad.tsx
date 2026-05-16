import { useNavigate } from 'react-router-dom';
import { ArrowRight, Brain, Radio, Zap } from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { cn, toneClass } from '@/lib/utils';

/**
 * Live launchpad — surfaces curated demo presets from the orchestrator's
 * `/demo/presets` endpoint. Only renders when the backend is reachable.
 *
 * Clicking a preset starts an SSE stream against `/demo/stream/{key}` and
 * navigates to the workstation so the analyst sees events flow in.
 */
export function LiveLaunchpad() {
  const navigate = useNavigate();
  const status = useIntelStore((s) => s.backendStatus);
  const presets = useIntelStore((s) => s.livePresets);
  const liveStreamPhase = useIntelStore((s) => s.liveStreamPhase);
  const activeLivePresetKey = useIntelStore((s) => s.activeLivePresetKey);
  const startLive = useIntelStore((s) => s.startLiveStream);
  const runDeep = useIntelStore((s) => s.runDeepInvestigation);
  const cognitivePhase = useIntelStore((s) => s.cognitivePhase);

  if (!status || presets.length === 0) return null;

  return (
    <section className="surface overflow-hidden mt-3">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Radio className="w-3 h-3 text-[var(--color-emerald-400)] anim-drift" />
        <span className="heading-tactical">Live orchestrator · curated investigations</span>
        <span className="chip chip-emerald ml-auto text-[8.5px]">
          {status.tigergraphOffline ? 'TG-OFF' : 'GRAPH LIVE'}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-y divide-[var(--color-line-soft)]">
        {presets.map((p, i) => {
          const tone = toneClass(p.tone);
          const isActive = activeLivePresetKey === p.key;
          const streaming =
            isActive && liveStreamPhase === 'streaming';
          return (
            <div
              key={p.key}
              className={cn(
                'group text-left px-3 py-3 flex items-start gap-3 transition-colors',
                'hover:bg-[rgba(34,211,238,0.04)]',
                isActive && 'bg-[rgba(34,211,238,0.05)]',
              )}
            >
              <span className="font-mono text-[9px] text-[var(--color-text-faint)] w-5 pt-0.5">
                {String(i + 1).padStart(2, '0')}
              </span>
              <button
                onClick={async () => {
                  await startLive(p.key);
                  navigate('/investigate');
                }}
                className="flex-1 min-w-0 text-left"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('chip text-[8.5px]', tone.text, tone.border)}>
                    {p.key}
                  </span>
                  {streaming && (
                    <span className="chip chip-emerald text-[8.5px] inline-flex items-center gap-1">
                      <Zap className="w-2.5 h-2.5 anim-drift" /> streaming
                    </span>
                  )}
                </div>
                <div className="text-[12.5px] font-medium text-[var(--color-text-bright)] leading-snug">
                  {p.title}
                </div>
                <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mt-1 flex flex-wrap gap-x-2">
                  {p.showcases.map((s) => (
                    <span key={s}>{s}</span>
                  ))}
                </div>
              </button>
              <div className="flex flex-col gap-1 shrink-0">
                <button
                  onClick={async () => {
                    await runDeep(p.key);
                    navigate('/investigate');
                  }}
                  disabled={cognitivePhase === 'running'}
                  className="h-6 px-2 inline-flex items-center gap-1 rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-400)] hover:bg-[rgba(168,85,247,0.12)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  title="Run cognitive deep investigation (agents + reasoning)"
                >
                  <Brain className="w-3 h-3" />
                  <span className="font-mono text-[9px] tracking-[0.22em] uppercase">
                    deep
                  </span>
                </button>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--color-text-muted)] group-hover:text-[var(--color-ice-400)] group-hover:translate-x-0.5 transition-all self-end mr-1" />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
