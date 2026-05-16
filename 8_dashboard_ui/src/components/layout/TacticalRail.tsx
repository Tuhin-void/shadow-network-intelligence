import { useEffect, useRef, useState, type ComponentType } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Bookmark,
  CircleDot,
  Eye,
  FolderOpen,
  GalleryVerticalEnd,
  Layers,
  Pin,
  ScanLine,
  X,
} from 'lucide-react';
import { useIntelStore, type TacticalTab } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';

/**
 * TacticalRail — semi-expanded contextual operational layer.
 *
 *   • Always-visible icon + label column (80 px wide) — analysts immediately
 *     see what tools exist.
 *   • Click a tab → panel expands to 300 px alongside it.
 *   • Tab state is in the store so the WorkspaceTabs micro-strip can drive it.
 *   • Fades to nothing only in graph focus mode.
 *
 * The graph stays dominant — the rail supports, doesn't compete.
 */
type Tab = TacticalTab;

interface TabDef {
  id: Tab;
  label: string;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
}

const TABS: TabDef[] = [
  { id: 'cases', label: 'Cases', icon: FolderOpen },
  { id: 'rings', label: 'Rings', icon: CircleDot },
  { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark },
  { id: 'evidence', label: 'Pinned', icon: Pin },
  { id: 'filters', label: 'Filters', icon: Layers },
  { id: 'replay', label: 'Replay', icon: GalleryVerticalEnd },
];

export function TacticalRail({ defaultTab }: { defaultTab?: Tab }) {
  const openTab = useIntelStore((s) => s.tacticalTab);
  const setOpenTab = useIntelStore((s) => s.setTacticalTab);
  const focusModeOn = useIntelStore((s) => s.focusModeOn);
  const location = useLocation();

  // Seed the default tab once on mount, only if user hasn't already chosen one.
  useEffect(() => {
    if (defaultTab && openTab === null) {
      setOpenTab(defaultTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultTab]);

  // Adaptive chrome — on graph routes, fade the rail to ambient after idle.
  // Restored by any cursor movement (the user is engaging again) and by hover
  // over the rail itself. On reading routes the rail stays fully present.
  const graphRoute =
    location.pathname === '/investigate' ||
    location.pathname.startsWith('/rings') ||
    location.pathname.startsWith('/replay') ||
    location.pathname.startsWith('/entity');
  const [faded, setFaded] = useState(false);
  const idleTimer = useRef<number | null>(null);
  useEffect(() => {
    if (!graphRoute || openTab !== null) {
      setFaded(false);
      return;
    }
    const onMove = () => {
      setFaded(false);
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(() => setFaded(true), 9000);
    };
    onMove();
    window.addEventListener('mousemove', onMove);
    return () => {
      window.removeEventListener('mousemove', onMove);
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
    };
  }, [graphRoute, openTab]);

  return (
    <AnimatePresence>
      {!focusModeOn && (
        <motion.div
          key="tactical-rail"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -14 }}
          transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
          className="chrome-adaptive absolute top-[100px] bottom-3 left-3 z-30 flex items-stretch gap-2 pointer-events-none"
          data-faded={faded ? 'true' : 'false'}
        >
      {/* Always-visible icon + label column (80px) — ambient veil, no chrome */}
      <nav className="veil-soft pointer-events-auto flex flex-col py-2 px-1.5 w-[80px]">
        <div className="flex flex-col gap-0.5">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = openTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setOpenTab(active ? null : t.id)}
                title={t.label}
                className={cn(
                  'relative w-full h-[52px] inline-flex flex-col items-center justify-center gap-1 rounded-sm transition-colors',
                  active
                    ? 'text-[var(--color-ice-400)] bg-[rgba(34,211,238,0.10)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[rgba(148,163,184,0.04)]'
                )}
              >
                {active && (
                  <span className="absolute left-[-6px] top-2 bottom-2 w-[2px] rounded-r-sm bg-[var(--color-ice-400)]" />
                )}
                <Icon className="w-4 h-4" strokeWidth={1.4} />
                <span className="font-mono text-[9px] tracking-[0.14em] uppercase leading-none">
                  {t.label}
                </span>
              </button>
            );
          })}
        </div>
        <div className="mt-auto" />
        <RailFooter />
      </nav>

      {/* Expanded panel — opens to the right of the icon column */}
      <AnimatePresence>
        {openTab && (
          <motion.div
            key={openTab}
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 300, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="veil-soft pointer-events-auto overflow-hidden"
            style={{ height: '100%' }}
          >
            <RailPanel tab={openTab} onClose={() => setOpenTab(null)} />
          </motion.div>
        )}
      </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* -------------------------------------------------------------------------- */

function RailFooter() {
  const focusModeOn = useIntelStore((s) => s.focusModeOn);
  const setFocusModeOn = useIntelStore((s) => s.setFocusModeOn);
  return (
    <button
      onClick={() => setFocusModeOn(!focusModeOn)}
      title={focusModeOn ? 'exit focus · F' : 'graph focus · F'}
      className={cn(
        'h-8 w-8 inline-flex items-center justify-center rounded-sm',
        focusModeOn
          ? 'text-[var(--color-violet-400)] bg-[rgba(168,85,247,0.08)]'
          : 'text-[var(--color-text-muted)] hover:text-[var(--color-violet-400)] hover:bg-[rgba(168,85,247,0.05)]'
      )}
    >
      <ScanLine className="w-3.5 h-3.5" strokeWidth={1.4} />
    </button>
  );
}

function RailPanel({ tab, onClose }: { tab: Tab; onClose: () => void }) {
  const labels: Record<Tab, string> = {
    cases: 'Cases',
    bookmarks: 'Bookmarked entities',
    rings: 'Detected rings',
    evidence: 'Pinned evidence',
    filters: 'Focus filters',
    replay: 'Replay session',
  };
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <span className="heading-tactical">{labels[tab]}</span>
        <button
          onClick={onClose}
          className="ml-auto w-5 h-5 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[rgba(148,163,184,0.06)]"
          aria-label="close"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto scroll-tactical">
        {tab === 'cases' && <CasesContent />}
        {tab === 'bookmarks' && <BookmarksContent />}
        {tab === 'rings' && <RingsContent />}
        {tab === 'evidence' && <EvidenceContent />}
        {tab === 'filters' && <FiltersContent />}
        {tab === 'replay' && <ReplayContent />}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Per-tab content                                                            */
/* -------------------------------------------------------------------------- */

function CasesContent() {
  const { presets, activePresetId, selectPreset } = useIntelStore();
  return (
    <div className="p-2 space-y-0.5">
      {presets.map((p) => {
        const isActive = p.id === activePresetId;
        return (
          <button
            key={p.id}
            onClick={() => selectPreset(p.id)}
            className={cn(
              'w-full text-left px-2 py-1.5 rounded-sm border transition-colors',
              isActive
                ? 'border-[rgba(34,211,238,0.32)] bg-[rgba(34,211,238,0.05)]'
                : 'border-transparent hover:bg-[rgba(148,163,184,0.04)]'
            )}
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'w-1 h-1 rounded-full',
                  isActive ? 'bg-[var(--color-ice-400)]' : 'bg-[var(--color-text-faint)]'
                )}
              />
              <span
                className={cn(
                  'text-[11.5px] truncate',
                  isActive
                    ? 'text-[var(--color-text-bright)]'
                    : 'text-[var(--color-text-secondary)]'
                )}
              >
                {p.label}
              </span>
            </div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] pl-3 truncate">
              {p.tags.slice(0, 3).join(' · ')}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function BookmarksContent() {
  const navigate = useNavigate();
  const { bookmarkedEntities, toggleBookmark, presets, active } = useIntelStore();
  if (bookmarkedEntities.size === 0) {
    return (
      <div className="p-4 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        no bookmarks yet
        <div className="text-[10.5px] normal-case tracking-normal mt-2 text-[var(--color-text-faint)]">
          pin entities from the inspector or dossier
        </div>
      </div>
    );
  }
  // Resolve each id across presets so bookmarks are case-spanning
  const resolved = Array.from(bookmarkedEntities).map((id) => {
    for (const p of presets) {
      const e = p.graph.entities.find((x) => x.id === id);
      if (e) return { entity: e, presetId: p.id, presetLabel: p.label };
    }
    return null;
  }).filter((x): x is NonNullable<typeof x> => Boolean(x));

  return (
    <div className="p-2 space-y-1">
      {resolved.map(({ entity: e, presetId, presetLabel }) => (
        <div
          key={`${presetId}_${e.id}`}
          className={cn(
            'rounded-sm px-2 py-1.5 flex items-center gap-2.5',
            'hover:bg-[rgba(34,211,238,0.04)]',
            presetId === active.id ? '' : 'opacity-80'
          )}
        >
          <button
            onClick={() => navigate(`/entity/${e.id}`)}
            className="flex items-center gap-2.5 flex-1 min-w-0 text-left"
          >
            <span
              className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[11px] shrink-0"
              style={{
                borderColor: tierColor(e.tier),
                color: tierColor(e.tier),
                background: `${tierColor(e.tier)}10`,
              }}
            >
              {entityGlyph(e.kind)}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[11.5px] text-[var(--color-text-bright)] truncate">
                {e.label}
              </div>
              <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                {presetLabel}
              </div>
            </div>
          </button>
          <button
            onClick={() => toggleBookmark(e.id)}
            className="w-5 h-5 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)]"
            title="remove bookmark"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}

function RingsContent() {
  const navigate = useNavigate();
  const { presets, active, selectPreset, applyQuery } = useIntelStore();
  const allRings = presets.flatMap((p) =>
    p.rings.map((r) => ({ ring: r, presetId: p.id, presetLabel: p.label }))
  );
  return (
    <div className="p-2 space-y-1">
      {allRings.map(({ ring, presetId, presetLabel }) => (
        <button
          key={ring.id}
          onClick={() => {
            if (presetId !== active.id) selectPreset(presetId);
            setTimeout(() => {
              applyQuery({
                focusMode: 'rings',
                surfaceRings: [ring.id],
                discoverEntities: ring.members,
                selectEntityId: ring.members[0],
                narrationLine: `Ring isolated · ${ring.name}`,
              });
            }, 60);
          }}
          className="w-full text-left rounded-sm px-2 py-1.5 hover:bg-[rgba(244,63,94,0.05)] border-l-2 border-[var(--color-rose-500)]"
        >
          <div className="text-[11.5px] text-[var(--color-text-primary)] truncate">
            {ring.name}
          </div>
          <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
            {presetLabel} · cohesion {ring.cohesion.toFixed(2)}
          </div>
        </button>
      ))}
      <button
        onClick={() => navigate('/rings')}
        className="w-full mt-2 h-7 inline-flex items-center justify-center font-mono text-[10px] tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] hover:border-[rgba(34,211,238,0.4)]"
      >
        open ring analysis →
      </button>
    </div>
  );
}

function EvidenceContent() {
  const { pinnedEvidence, togglePinEvidence, active } = useIntelStore();
  const resolved = Array.from(pinnedEvidence)
    .map((id) => active.report.evidence.find((e) => e.id === id))
    .filter((x): x is NonNullable<typeof x> => Boolean(x));
  if (resolved.length === 0) {
    return (
      <div className="p-4 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        no evidence pinned
        <div className="text-[10.5px] normal-case tracking-normal mt-2 text-[var(--color-text-faint)]">
          pin items from the evidence section
        </div>
      </div>
    );
  }
  return (
    <div className="p-2 space-y-1.5">
      {resolved.map((ev) => (
        <div
          key={ev.id}
          className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-emerald-500)]"
        >
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-emerald-400)]">
              {ev.basis}
            </span>
            <span className="ml-auto font-mono text-[9px] text-[var(--color-text-muted)]">
              {ev.confidence.toFixed(2)}
            </span>
            <button
              onClick={() => togglePinEvidence(ev.id)}
              className="w-4 h-4 inline-flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)]"
              title="unpin"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
          <div className="text-[11px] text-[var(--color-text-primary)] mt-0.5 leading-snug">
            {ev.claim}
          </div>
        </div>
      ))}
    </div>
  );
}

function FiltersContent() {
  const { focusMode, setFocusMode } = useIntelStore();
  const MODES: Array<{
    id: 'overview' | 'rings' | 'hidden' | 'paths' | 'risk';
    label: string;
    desc: string;
  }> = [
    { id: 'overview', label: 'Overview', desc: 'full topology' },
    { id: 'risk', label: 'Risk heat', desc: 'critical / high only' },
    { id: 'rings', label: 'Rings', desc: 'ring members only' },
    { id: 'hidden', label: 'Hidden links', desc: 'topology-derived ties' },
    { id: 'paths', label: 'Paths', desc: 'traversal evidence' },
  ];
  return (
    <div className="p-2 space-y-1">
      {MODES.map((m) => {
        const active = focusMode === m.id;
        return (
          <button
            key={m.id}
            onClick={() => setFocusMode(m.id)}
            className={cn(
              'w-full text-left rounded-sm px-2 py-1.5 border',
              active
                ? 'border-[rgba(34,211,238,0.32)] bg-[rgba(34,211,238,0.05)]'
                : 'border-transparent hover:bg-[rgba(148,163,184,0.04)]'
            )}
          >
            <div
              className={cn(
                'text-[11.5px]',
                active ? 'text-[var(--color-ice-400)]' : 'text-[var(--color-text-primary)]'
              )}
            >
              {m.label}
            </div>
            <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
              {m.desc}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ReplayContent() {
  const navigate = useNavigate();
  const { sessions, active } = useIntelStore();
  return (
    <div className="p-2 space-y-1">
      <div className="px-2 py-2 font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
        {sessions.length === 0
          ? 'no sessions yet — run an investigation'
          : `${sessions.length} saved`}
      </div>
      {sessions.slice(0, 6).map((s) => (
        <button
          key={s.id}
          onClick={() => navigate(`/replay/${s.id}`)}
          className="w-full text-left rounded-sm px-2 py-1.5 hover:bg-[rgba(34,211,238,0.04)]"
        >
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
              {s.id}
            </span>
            <span
              className={cn(
                'ml-auto w-1.5 h-1.5 rounded-full',
                s.status === 'complete' ? 'bg-[var(--color-emerald-400)]' : 'bg-[var(--color-ice-400)]'
              )}
            />
          </div>
          <div className="text-[11px] text-[var(--color-text-bright)] truncate mt-0.5">
            {s.title}
          </div>
        </button>
      ))}
      <button
        onClick={() => navigate('/replay')}
        className="w-full mt-2 h-7 inline-flex items-center justify-center gap-2 font-mono text-[10px] tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] hover:border-[rgba(34,211,238,0.4)]"
      >
        <Eye className="w-3 h-3" />
        open replay center →
      </button>
      <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] mt-1 px-2">
        active · {active.label}
      </div>
    </div>
  );
}
