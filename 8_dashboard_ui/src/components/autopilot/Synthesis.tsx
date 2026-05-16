import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useIntelStore } from '@/store/intel-store';
import { entityGlyph, tierColor } from '@/lib/utils';
import {
  ShieldAlert,
  Sparkles,
  Spline,
  GitBranch,
  CircleDot,
  Archive,
  Eye,
  X,
  ChevronUp,
  ChevronDown,
  Bookmark,
  GalleryVerticalEnd,
  Hand,
  Layers,
  Pin,
  Swords,
  Target,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

/**
 * The Synthesis — cinematic dossier reveal at session.complete.
 *
 * No-trap rules:
 *  • ESC dismisses
 *  • Click backdrop dismisses
 *  • X button dismisses
 *  • Minimize button collapses to a floating chip — graph stays visible
 */
export function Synthesis() {
  const navigate = useNavigate();
  const {
    active,
    applyQuery,
    selectEntity,
    setFocusMode,
    toggleBookmark,
    bookmarkedEntities,
    togglePinEvidence,
    pinnedEvidence,
  } = useIntelStore();
  const r = active.report;
  const [visible, setVisible] = useState(true);
  const [minimized, setMinimized] = useState(false);

  // ESC dismiss
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setVisible(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [visible]);

  if (!visible) {
    return null;
  }

  // Minimized state — small reopen chip, graph fully visible
  if (minimized) {
    return (
      <motion.button
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        onClick={() => setMinimized(false)}
        className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40 surface-floating h-9 px-3 inline-flex items-center gap-2 rounded-full"
        title="restore synthesis"
      >
        <Sparkles className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="font-mono text-[10px] tracking-[0.26em] uppercase text-[var(--color-text-bright)]">
          synthesis ready
        </span>
        <span className="text-[var(--color-text-faint)]">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] truncate max-w-[260px]">
          {r.narrative.headline.slice(0, 56)}…
        </span>
        <ChevronUp className="w-3 h-3 text-[var(--color-text-muted)]" />
      </motion.button>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.8 }}
      className="fill z-40 flex items-center justify-center"
      style={{ background: 'rgba(0,0,3,0.55)', backdropFilter: 'blur(6px)' }}
      // click backdrop to minimize so graph stays accessible
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) setMinimized(true);
      }}
    >
      <motion.div
        initial={{ y: 36, opacity: 0, scale: 0.97, filter: 'blur(8px)' }}
        animate={{ y: 0, opacity: 1, scale: 1, filter: 'blur(0)' }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        className="surface-floating relative w-[1080px] max-w-[92vw] max-h-[88vh] overflow-hidden"
      >
        <div className="fill tactical-grid-fine opacity-30 pointer-events-none" />

        {/* Classified stamp ribbon */}
        <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
          <ClassifiedStamp />
          <button
            onClick={() => setMinimized(true)}
            className="w-7 h-7 inline-flex items-center justify-center rounded-sm border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[rgba(34,211,238,0.4)] bg-[rgba(7,9,14,0.6)]"
            title="minimize · graph stays visible"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setVisible(false)}
            className="w-7 h-7 inline-flex items-center justify-center rounded-sm border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)] hover:border-[rgba(244,63,94,0.4)] bg-[rgba(7,9,14,0.6)]"
            title="dismiss · ESC"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Header */}
        <div className="px-8 pt-7 pb-4 border-b border-[var(--color-line-soft)] relative">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="w-4 h-4 text-[var(--color-ice-400)]" />
            <span className="font-mono text-[10px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
              intelligence synthesis · investigation 0x{active.id.slice(0, 4).toUpperCase()}
            </span>
          </div>
          <motion.h1
            initial={{ opacity: 0, y: 12, letterSpacing: '0.16em' }}
            animate={{ opacity: 1, y: 0, letterSpacing: '0.02em' }}
            transition={{ duration: 1.0, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="text-[28px] font-light tracking-tight text-[var(--color-text-bright)] leading-snug"
          >
            {r.narrative.headline}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, delay: 0.5 }}
            className="mt-3 text-[12.5px] text-[var(--color-text-secondary)] leading-relaxed max-w-[820px]"
          >
            {r.narrative.body}
          </motion.p>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.7 }}
            className="mt-4 flex flex-wrap gap-1.5"
          >
            {r.narrative.highlights.map((h) => (
              <span key={h} className="chip chip-ice">{h}</span>
            ))}
          </motion.div>
        </div>

        {/* 3-column conclusion */}
        <div className="grid grid-cols-3 divide-x divide-[var(--color-line-soft)]">
          <Column
            icon={ShieldAlert}
            label="prime suspects"
            tone="rose"
            delay={0.9}
          >
            <div className="space-y-1.5">
              {r.suspects.slice(0, 5).map((s) => {
                const bookmarked = bookmarkedEntities.has(s.id);
                return (
                  <div
                    key={s.id}
                    className="group flex items-center gap-2.5 px-2 py-1.5 rounded-sm bg-[rgba(255,255,255,0.012)] hover:bg-[rgba(34,211,238,0.05)] transition-colors"
                  >
                    <button
                      onClick={() => navigate(`/entity/${s.id}`)}
                      className="flex items-center gap-2.5 flex-1 min-w-0 text-left"
                      title="open dossier"
                    >
                      <span
                        className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[11px] shrink-0"
                        style={{
                          borderColor: tierColor(s.tier),
                          color: tierColor(s.tier),
                          background: `${tierColor(s.tier)}10`,
                        }}
                      >
                        {entityGlyph(s.kind)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] text-[var(--color-text-bright)] truncate">
                          {s.label}
                        </div>
                        <div className="font-mono text-[9px] uppercase tracking-wider text-[var(--color-text-muted)]">
                          {s.kind.replace('_', ' ')} · {s.id}
                        </div>
                      </div>
                      <span
                        className="font-mono text-[11px]"
                        style={{ color: tierColor(s.tier) }}
                      >
                        {s.risk}
                      </span>
                    </button>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => toggleBookmark(s.id)}
                        className={`w-5 h-5 inline-flex items-center justify-center rounded-sm ${
                          bookmarked
                            ? 'text-[var(--color-ice-400)]'
                            : 'text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]'
                        }`}
                        title={bookmarked ? 'unbookmark' : 'bookmark'}
                      >
                        <Bookmark
                          className="w-3 h-3"
                          fill={bookmarked ? 'currentColor' : 'none'}
                          strokeWidth={1.5}
                        />
                      </button>
                      <button
                        onClick={() => {
                          selectEntity(s.id);
                          setFocusMode('overview');
                          navigate('/investigate');
                        }}
                        className="w-5 h-5 inline-flex items-center justify-center rounded-sm text-[var(--color-text-muted)] hover:text-[var(--color-violet-400)]"
                        title="investigate"
                      >
                        <Target className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </Column>

          <Column icon={CircleDot} label="topology findings" tone="violet" delay={1.1}>
            <div className="space-y-2">
              {/* Rings — click to isolate on graph */}
              {r.rings.length > 0 && (
                <div>
                  <Subhead icon={CircleDot} label="rings detected" tone="rose" />
                  <div className="mt-1 space-y-1">
                    {r.rings.map((ring) => (
                      <button
                        key={ring.id}
                        onClick={() => {
                          applyQuery({
                            focusMode: 'rings',
                            surfaceRings: [ring.id],
                            discoverEntities: ring.members,
                            selectEntityId: ring.members[0],
                            narrationLine: `Ring isolated · ${ring.name}`,
                          });
                          navigate('/rings');
                        }}
                        className="w-full text-left text-[11px] text-[var(--color-text-primary)] flex items-start gap-2 px-1.5 py-1 rounded-sm hover:bg-[rgba(244,63,94,0.06)] transition-colors"
                        title="isolate ring on graph"
                      >
                        <span className="text-[var(--color-rose-400)] mt-1">●</span>
                        <div className="flex-1">
                          <div>{ring.name}</div>
                          <div className="font-mono text-[9px] text-[var(--color-text-muted)] uppercase tracking-wider">
                            cohesion {ring.cohesion.toFixed(2)} · {ring.signal.replace('_', ' ')}
                          </div>
                        </div>
                        <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-rose-400)] opacity-0 group-hover:opacity-100">
                          ▸ open
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {/* Hidden — click to focus on graph */}
              {r.hiddenRelationships.length > 0 && (
                <div>
                  <Subhead icon={Spline} label="hidden ties" tone="violet" />
                  <div className="mt-1 space-y-1">
                    {r.hiddenRelationships.slice(0, 4).map((h) => (
                      <button
                        key={h.id}
                        onClick={() => {
                          applyQuery({
                            focusMode: 'hidden',
                            discoverEntities: [h.from, h.to, ...h.via],
                            selectEntityId: h.from,
                            narrationLine: `Hidden tie · ${h.from} → ${h.to}`,
                          });
                        }}
                        className="w-full text-left text-[11px] text-[var(--color-text-primary)] flex items-start gap-2 px-1.5 py-1 rounded-sm hover:bg-[rgba(168,85,247,0.06)] transition-colors"
                        title="highlight hidden tie on graph"
                      >
                        <span className="text-[var(--color-violet-400)] mt-1">◌</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-violet-300)] truncate">
                            {h.from} → {h.to}
                          </div>
                          <div className="text-[11px] text-[var(--color-text-secondary)] line-clamp-2">
                            {h.reason}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {/* Paths — click to surface on graph */}
              {r.traversalPaths.length > 0 && (
                <div>
                  <Subhead icon={GitBranch} label="key paths" tone="amber" />
                  <div className="mt-1 space-y-1">
                    {r.traversalPaths.slice(0, 3).map((p) => (
                      <button
                        key={p.id}
                        onClick={() => {
                          applyQuery({
                            focusMode: 'paths',
                            surfacePaths: [p.id],
                            discoverEntities: p.nodes,
                            selectEntityId: p.nodes[0],
                            narrationLine: `Path surfaced · ${p.label}`,
                          });
                        }}
                        className="w-full text-left text-[11px] text-[var(--color-text-primary)] px-1.5 py-1 rounded-sm hover:bg-[rgba(245,158,11,0.06)] transition-colors"
                        title="surface path on graph"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[var(--color-amber-400)]">→</span>
                          <span className="truncate">{p.label}</span>
                          <span className="ml-auto font-mono text-[9px] text-[var(--color-text-muted)] shrink-0">
                            {p.hops} hops
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Column>

          <Column icon={Sparkles} label="evidence chain" tone="emerald" delay={1.3}>
            <div className="relative pl-4">
              <span className="absolute left-1 top-1 bottom-1 w-px bg-[var(--color-line)]" />
              <div className="space-y-2">
                {r.evidence.slice(0, 6).map((ev, i) => {
                  const pinned = pinnedEvidence.has(ev.id);
                  return (
                    <motion.div
                      key={ev.id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.4, delay: 1.5 + i * 0.12 }}
                      className="group relative px-1.5 py-1 rounded-sm hover:bg-[rgba(16,185,129,0.05)]"
                    >
                      <span
                        className="absolute -left-[10px] top-2 w-1.5 h-1.5 rounded-full bg-[var(--color-emerald-400)]"
                      />
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[9px] uppercase tracking-wider text-[var(--color-text-muted)]">
                          {ev.basis} · conf {ev.confidence.toFixed(2)}
                        </span>
                        <button
                          onClick={() => togglePinEvidence(ev.id)}
                          className={`ml-auto w-4 h-4 inline-flex items-center justify-center rounded-sm opacity-0 group-hover:opacity-100 transition-opacity ${
                            pinned
                              ? 'text-[var(--color-emerald-400)] opacity-100'
                              : 'text-[var(--color-text-muted)] hover:text-[var(--color-emerald-400)]'
                          }`}
                          title={pinned ? 'unpin' : 'pin evidence'}
                        >
                          <Pin
                            className="w-3 h-3"
                            fill={pinned ? 'currentColor' : 'none'}
                            strokeWidth={1.5}
                          />
                        </button>
                      </div>
                      <div className="text-[11px] text-[var(--color-text-primary)] leading-snug mt-0.5">
                        {ev.claim}
                      </div>
                      {/* Provenance refs — click to navigate */}
                      {ev.refs.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {ev.refs.slice(0, 3).map((ref) => (
                            <button
                              key={ref}
                              onClick={() => {
                                // Try to route the ref to its workspace
                                const ring = active.rings.find((x) => x.id === ref);
                                const path = active.paths.find((x) => x.id === ref);
                                if (ring) {
                                  applyQuery({
                                    focusMode: 'rings',
                                    surfaceRings: [ring.id],
                                    discoverEntities: ring.members,
                                    selectEntityId: ring.members[0],
                                    narrationLine: `Evidence trail → ${ring.name}`,
                                  });
                                } else if (path) {
                                  applyQuery({
                                    focusMode: 'paths',
                                    surfacePaths: [path.id],
                                    discoverEntities: path.nodes,
                                    selectEntityId: path.nodes[0],
                                    narrationLine: `Evidence trail → ${path.label}`,
                                  });
                                }
                              }}
                              className="font-mono text-[8.5px] tracking-[0.12em] uppercase px-1.5 py-0.5 rounded-sm border border-[rgba(16,185,129,0.3)] text-[var(--color-emerald-400)] hover:bg-[rgba(16,185,129,0.06)]"
                            >
                              {ref}
                            </button>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </Column>
        </div>

        {/* Continue investigation rail */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.8 }}
          className="border-t border-[var(--color-line-soft)] px-6 py-3"
        >
          <div className="flex items-center gap-3 font-mono text-[9.5px] tracking-[0.26em] uppercase text-[var(--color-text-muted)] mb-2 flex-wrap">
            <span>case sealed · {new Date().toISOString().slice(0, 19).replace('T', ' ')}</span>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span className="text-[var(--color-emerald-400)]">analyst.0xA1</span>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span>{r.suspects.length} suspects · {r.rings.length} rings · {r.evidence.length} evidence</span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {/* Primary: continue manual */}
            <ContinueAction
              icon={Hand}
              label="continue in manual"
              tone="violet"
              primary
              onClick={() => {
                setVisible(false);
                navigate('/investigate');
              }}
            />
            <ContinueAction
              icon={CircleDot}
              label="open ring analysis"
              tone="rose"
              onClick={() => {
                setVisible(false);
                navigate('/rings');
              }}
            />
            <ContinueAction
              icon={Spline}
              label="focus hidden ties"
              tone="violet"
              onClick={() => {
                setFocusMode('hidden');
                setMinimized(true);
              }}
            />
            <ContinueAction
              icon={GalleryVerticalEnd}
              label="replay"
              tone="ice"
              onClick={() => {
                setVisible(false);
                navigate('/replay');
              }}
            />
            <ContinueAction
              icon={Swords}
              label="compare pipelines"
              tone="amber"
              onClick={() => {
                setVisible(false);
                navigate('/benchmark');
              }}
            />
            <ContinueAction
              icon={Layers}
              label="branch · prime suspect"
              tone="ice"
              onClick={() => {
                if (r.suspects[0]) {
                  setVisible(false);
                  navigate(`/entity/${r.suspects[0].id}`);
                }
              }}
            />
            <span className="ml-auto flex items-center gap-1.5">
              <button
                onClick={() => navigate('/sessions')}
                className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[9.5px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:border-[rgba(34,211,238,0.35)] hover:text-[var(--color-ice-400)]"
              >
                <Archive className="w-3 h-3" />
                archive
              </button>
              <button
                onClick={() => setMinimized(true)}
                className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[9.5px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:border-[rgba(168,85,247,0.4)] hover:text-[var(--color-violet-400)]"
              >
                <ChevronDown className="w-3 h-3" />
                minimize · stay on graph
              </button>
            </span>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */

function Column({
  icon: Icon,
  label,
  tone,
  delay,
  children,
}: {
  icon: typeof Sparkles;
  label: string;
  tone: 'rose' | 'amber' | 'ice' | 'violet' | 'emerald';
  delay: number;
  children: React.ReactNode;
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    amber: 'var(--color-amber-400)',
    ice: 'var(--color-ice-400)',
    violet: 'var(--color-violet-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className="p-5"
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[10px] tracking-[0.32em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      {children}
    </motion.div>
  );
}

function ContinueAction({
  icon: Icon,
  label,
  tone,
  onClick,
  primary,
}: {
  icon: typeof Sparkles;
  label: string;
  tone: 'ice' | 'rose' | 'violet' | 'amber' | 'emerald';
  onClick: () => void;
  primary?: boolean;
}) {
  const color = {
    ice: 'var(--color-ice-400)',
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
    amber: 'var(--color-amber-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <button
      onClick={onClick}
      className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[9.5px] font-mono tracking-[0.26em] uppercase rounded-sm border transition-colors"
      style={{
        borderColor: primary ? color : 'var(--color-line)',
        background: primary ? `${color}10` : 'transparent',
        color: primary ? color : 'var(--color-text-secondary)',
      }}
    >
      <Icon className="w-3 h-3" style={{ color }} />
      <span>{label}</span>
    </button>
  );
}

function Subhead({
  icon: Icon,
  label,
  tone,
}: {
  icon: typeof Sparkles;
  label: string;
  tone: 'rose' | 'amber' | 'violet';
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    amber: 'var(--color-amber-400)',
    violet: 'var(--color-violet-400)',
  }[tone];
  return (
    <div className="flex items-center gap-1.5 text-[var(--color-text-muted)] font-mono text-[9px] uppercase tracking-[0.22em]">
      <Icon className="w-2.5 h-2.5" style={{ color }} />
      <span style={{ color }}>{label}</span>
    </div>
  );
}

function ClassifiedStamp() {
  return (
    <motion.div
      initial={{ opacity: 0, rotate: -8, scale: 1.2 }}
      animate={{ opacity: 1, rotate: -3, scale: 1 }}
      transition={{ duration: 0.6, delay: 1.1, ease: [0.16, 1, 0.3, 1] }}
      className="font-mono text-[10px] tracking-[0.4em] uppercase px-3 py-1 border-2 text-[var(--color-rose-400)] border-[var(--color-rose-400)] select-none"
      style={{
        textShadow: '0 0 12px rgba(244,63,94,0.45)',
      }}
    >
      classified · case sealed
    </motion.div>
  );
}
