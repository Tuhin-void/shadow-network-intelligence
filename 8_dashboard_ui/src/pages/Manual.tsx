import { useEffect, useState } from 'react';
import {
  Brain,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  RotateCcw,
  ScanSearch,
  Target,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphHud, GraphLegend } from '@/components/graph/GraphHud';
import { EntityInspector } from '@/components/investigation/EntityInspector';
import { IntelligencePanel } from '@/components/investigation/IntelligencePanel';
import { TimelineFeed } from '@/components/investigation/TimelineFeed';
import { CommandDock } from '@/components/investigation/CommandDock';
import { CognitivePanel } from '@/components/cognitive/CognitivePanel';
import { TacticalRail } from '@/components/layout/TacticalRail';
import { WorkspaceTabs } from '@/components/layout/WorkspaceTabs';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

type RightTab = 'inspector' | 'report' | 'cognitive';

/**
 * Manual — analyst workstation.
 *
 * Layout philosophy: GRAPH IS DOMINANT.
 *   • Top: header (40 px)
 *   • Body grid:
 *       - Left  (240 px): cases + queries
 *       - Center (1fr × 1fr): graph (with HUD + Legend overlays)
 *       - Right (340 px): tabbed [Inspector WHY] | [Report]
 *   • Bottom (160 px under center): step controls + timeline strip
 *
 * Keyboard:
 *   ← / →  / space → step prev/next
 *   1 / 2  → switch right-tab Inspector / Report
 */
export function Manual() {
  const {
    active,
    stepIndex,
    progress,
    stepForward,
    stepBack,
    resetStream,
    setRunMode,
    narration,
  } = useIntelStore();
  const total = active.stream.length;

  const [rightTab, setRightTab] = useState<RightTab>('inspector');

  useEffect(() => {
    setRunMode('manual');
  }, [setRunMode]);

  // Keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement | null)?.tagName === 'INPUT') return;
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        stepForward();
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        stepBack();
      }
      if (e.key === '1') setRightTab('inspector');
      if (e.key === '2') setRightTab('report');
      if (e.key === '3') setRightTab('cognitive');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [stepForward, stepBack]);

  return (
    <div className="fill bg-[var(--color-void)] overflow-hidden text-[var(--color-text-primary)]">
      {/* Workspace micro-tabs strip (top) + slim contextual rail (left) */}
      <WorkspaceTabs />
      <TacticalRail defaultTab="cases" />

      {/* Persistent CommandDock */}
      <CommandDock />

      {/* ─── BODY GRID — graph dominates ───────────────────────── */}
      <div
        className="absolute top-[96px] inset-x-0 bottom-0"
        style={{
          display: 'grid',
          // Reserve 92px gutter for the semi-expanded TacticalRail (80px + 6+6 margin)
          gridTemplateColumns: '92px minmax(0, 1fr) 340px',
          gridTemplateRows: 'minmax(0, 1fr) 160px',
          gap: '6px',
          padding: '6px',
        }}
      >
        {/* LEFT GUTTER — empty; TacticalRail floats inside it */}
        <div className="row-span-2" />

        {/* CENTER — graph */}
        <div className="relative surface overflow-hidden min-h-0">
          {/* Top label strip */}
          <div className="absolute top-0 left-0 right-0 h-7 flex items-center px-3 z-30 bg-[rgba(7,9,14,0.55)] backdrop-blur-sm border-b border-[var(--color-line-soft)]">
            <Target className="w-3 h-3 text-[var(--color-ice-400)]" />
            <span className="heading-tactical ml-2">Topology</span>
            <span className="chip chip-violet ml-2">manual</span>
            <NarrationBadge narration={narration} />
            <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              click any node to inspect · ← → step
            </span>
          </div>

          {/* Graph fills the rest */}
          <div className="absolute top-7 left-0 right-0 bottom-0">
            <GraphCanvas />
            <GraphHud />
            <GraphLegend />
          </div>
        </div>

        {/* RIGHT — tabbed inspector / report */}
        <div
          className="row-span-2 surface overflow-hidden min-h-0"
          style={{ display: 'grid', gridTemplateRows: 'auto minmax(0, 1fr)' }}
        >
          <TabStrip rightTab={rightTab} setRightTab={setRightTab} />
          <div className="min-h-0 overflow-y-auto scroll-tactical">
            {rightTab === 'inspector' && <EntityInspector />}
            {rightTab === 'report' && <IntelligencePanel />}
            {rightTab === 'cognitive' && (
              <div className="p-2">
                <CognitivePanel />
              </div>
            )}
          </div>
        </div>

        {/* BOTTOM — step controls + timeline (under center column) */}
        <div className="col-start-2 row-start-2 surface overflow-hidden min-h-0 flex flex-col">
          <div className="h-9 px-3 flex items-center gap-3 border-b border-[var(--color-line-soft)]">
            <button
              onClick={stepBack}
              disabled={stepIndex === 0}
              className="h-6 w-6 inline-flex items-center justify-center rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:bg-[rgba(168,85,247,0.06)] hover:border-[rgba(168,85,247,0.35)] disabled:opacity-30 disabled:cursor-not-allowed"
              title="Step back · ←"
            >
              <ChevronLeft className="w-3 h-3" />
            </button>
            <button
              onClick={stepForward}
              disabled={stepIndex >= total}
              className="h-6 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-400)] hover:bg-[rgba(168,85,247,0.1)] disabled:opacity-30 disabled:cursor-not-allowed"
              title="Step forward · → or Space"
            >
              <ChevronRight className="w-3 h-3" />
              step
              <span className="text-[var(--color-text-muted)]">
                {stepIndex}/{total}
              </span>
            </button>
            <button
              onClick={resetStream}
              className="h-6 w-6 inline-flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] rounded-sm hover:bg-[rgba(148,163,184,0.06)]"
              title="Reset"
            >
              <RotateCcw className="w-3 h-3" />
            </button>

            {/* Progress bar — takes remaining space, capped */}
            <div className="flex-1 min-w-[100px] max-w-[320px] h-1 rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
              <motion.div
                initial={false}
                animate={{ width: `${Math.round(progress * 100)}%` }}
                transition={{ duration: 0.4 }}
                className="h-full bg-gradient-to-r from-[var(--color-violet-500)] to-[var(--color-ice-500)]"
              />
            </div>
            <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] shrink-0 whitespace-nowrap">
              {Math.round(progress * 100)}% · {stepIndex}/{total}
            </span>

            {/* Keyboard hints — hide at narrow widths to prevent collision */}
            <div className="ml-auto hidden xl:flex items-center gap-1 font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-faint)] shrink-0">
              <span className="kbd">←</span>
              <span className="kbd">→</span>
              <span className="kbd">space</span>
              <span className="kbd">1</span>
              <span className="kbd">2</span>
            </div>
          </div>
          {/* Timeline */}
          <div className="flex-1 min-h-0">
            <TimelineFeed />
          </div>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function TabStrip({
  rightTab,
  setRightTab,
}: {
  rightTab: RightTab;
  setRightTab: (t: RightTab) => void;
}) {
  return (
    <div className="h-8 flex items-center border-b border-[var(--color-line-soft)] px-2 gap-1">
      <TabButton
        active={rightTab === 'inspector'}
        onClick={() => setRightTab('inspector')}
        icon={ScanSearch}
        label="inspector · why"
        kbd="1"
      />
      <TabButton
        active={rightTab === 'report'}
        onClick={() => setRightTab('report')}
        icon={FileText}
        label="report · 9 sections"
        kbd="2"
      />
      <TabButton
        active={rightTab === 'cognitive'}
        onClick={() => setRightTab('cognitive')}
        icon={Brain}
        label="cognitive · reasoning"
        kbd="3"
      />
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
  kbd,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Eye;
  label: string;
  kbd: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'h-6 px-2 flex items-center gap-1.5 rounded-sm font-mono text-[9.5px] tracking-[0.22em] uppercase',
        active
          ? 'bg-[rgba(34,211,238,0.10)] text-[var(--color-ice-400)] border border-[rgba(34,211,238,0.32)]'
          : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-transparent'
      )}
    >
      <Icon className="w-3 h-3" />
      <span>{label}</span>
      <span className="kbd text-[8.5px] ml-1">{kbd}</span>
    </button>
  );
}

function NarrationBadge({ narration }: { narration: string | null }) {
  if (!narration) return null;
  return (
    <motion.span
      key={narration}
      initial={{ opacity: 0, x: 6, filter: 'blur(2px)' }}
      animate={{ opacity: 1, x: 0, filter: 'blur(0)' }}
      transition={{ duration: 0.28 }}
      className="ml-3 font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-violet-300)] truncate"
    >
      → {narration}
    </motion.span>
  );
}
