import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertOctagon,
  Archive,
  Beaker,
  Bell,
  BookOpen,
  Check,
  CircleDot,
  Eye,
  FileText,
  GalleryVerticalEnd,
  Home,
  Hand,
  Maximize2,
  Minimize2,
  Moon,
  Network,
  Radar,
  Search,
  Sparkles,
  Swords,
  User,
  Waves,
  Workflow,
} from 'lucide-react';
import type { ComponentType } from 'react';
import { useIntelStore, type EnvMode } from '@/store/intel-store';
import { GlobalSearch } from './GlobalSearch';
import { NotificationCenter } from './NotificationCenter';
import { cn, formatTime } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: typeof Home;
  matchPrefix?: string;
}

const NAV: NavItem[] = [
  { to: '/home', label: 'Home', icon: Home },
  { to: '/sources', label: 'Sources', icon: Workflow, matchPrefix: '/sources' },
  { to: '/investigate', label: 'Investigate', icon: Hand, matchPrefix: '/investigate' },
  { to: '/autopilot', label: 'Autopilot', icon: Eye },
  { to: '/benchmark', label: 'Benchmark', icon: Swords },
  { to: '/methodology', label: 'Why GraphRAG', icon: BookOpen, matchPrefix: '/methodology' },
  { to: '/simulate', label: 'Simulate', icon: Beaker },
  { to: '/rings', label: 'Rings', icon: CircleDot, matchPrefix: '/rings' },
  { to: '/replay', label: 'Replay', icon: GalleryVerticalEnd, matchPrefix: '/replay' },
  { to: '/entities', label: 'Entities', icon: Network, matchPrefix: '/entity' },
  { to: '/reports', label: 'Reports', icon: FileText, matchPrefix: '/reports' },
  { to: '/alerts', label: 'Alerts', icon: AlertOctagon },
];

/**
 * FloatingNav — top-centered glass pill nav.
 *
 *  • Auto-fades when focusModeOn === true.
 *  • Auto-fades after 4s of mouse idle (re-appears on movement).
 *  • Provides global ⌘K, notifications, autosave indicator, focus toggle.
 *  • Persistent across all operational routes.
 */
export function FloatingNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    focusModeOn,
    setFocusModeOn,
    lastSavedAt,
    dismissedNotifications,
    presets,
  } = useIntelStore();

  const [searchOpen, setSearchOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [hidden, setHidden] = useState(false);
  const idleTimer = useRef<number | null>(null);
  const bellRef = useRef<HTMLButtonElement>(null);

  /** Compute panel anchor from the bell's actual position every time it opens
   *  (and on resize) — survives window resize + nav re-layout. */
  const computeNotifAnchor = () => {
    const el = bellRef.current;
    if (!el) return { x: window.innerWidth - 24, y: 64 };
    const r = el.getBoundingClientRect();
    return { x: r.right, y: r.bottom + 6 };
  };
  const [notifAnchor, setNotifAnchor] = useState<{ x: number; y: number }>(() => ({
    x: window.innerWidth - 24,
    y: 64,
  }));
  useEffect(() => {
    if (!notifOpen) return;
    const update = () => setNotifAnchor(computeNotifAnchor());
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, [notifOpen]);

  // Auto-hide after idle — only on graph-immersive routes where the analyst
  // wants the topology to breathe. Reading routes (home/alerts/reports/etc.)
  // keep the nav permanently visible.
  const graphRoute =
    location.pathname === '/investigate' ||
    location.pathname.startsWith('/rings') ||
    location.pathname.startsWith('/replay') ||
    location.pathname.startsWith('/entity/');

  useEffect(() => {
    if (focusModeOn) {
      setHidden(true);
      return;
    }
    if (!graphRoute) {
      setHidden(false);
      return;
    }
    const resetIdle = () => {
      setHidden(false);
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(() => setHidden(true), 6000);
    };
    resetIdle();
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('keydown', resetIdle);
    return () => {
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('keydown', resetIdle);
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
    };
  }, [focusModeOn, graphRoute]);

  // ⌘K / Ctrl+K → search · F → focus · ⌘⇧B / Ctrl+⇧+B → replay awakening
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen((s) => !s);
        setNotifOpen(false);
      }
      // F = focus mode toggle (ignored when typing)
      if (
        e.key === 'f' &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !e.metaKey &&
        !e.ctrlKey
      ) {
        setFocusModeOn(!focusModeOn);
      }
      // ⌘⇧B / Ctrl+⇧+B = replay the operational awakening. Clears the
      // session boot flag, then routes to /?boot=1 so it runs even
      // through the session-cache fast-path.
      if (
        (e.metaKey || e.ctrlKey) &&
        e.shiftKey &&
        e.key.toLowerCase() === 'b'
      ) {
        e.preventDefault();
        try {
          sessionStorage.removeItem('shadow:booted');
        } catch {
          /* sessionStorage disabled */
        }
        navigate('/?boot=1');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [focusModeOn, setFocusModeOn, navigate]);

  const isMatch = (item: NavItem) =>
    item.matchPrefix
      ? location.pathname.startsWith(item.matchPrefix)
      : location.pathname === item.to;

  // Notification count
  const notifTotal = Math.max(0, presets.length * 3 + 1 - dismissedNotifications.size);

  return (
    <>
      {/* Floating nav */}
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{
          y: hidden ? -80 : 0,
          opacity: hidden ? 0 : 1,
        }}
        transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
        className="fixed top-3 left-1/2 -translate-x-1/2 z-[60] pointer-events-none"
      >
        <div className="pointer-events-auto veil flex items-center gap-1 pl-3 pr-2 h-11 rounded-full">
          {/* Logo */}
          <button
            onClick={() => navigate('/home')}
            className="flex items-center gap-2 pr-3 mr-1 border-r border-[var(--color-line-soft)] h-7"
            title="home"
          >
            <span className="relative inline-flex items-center justify-center w-6 h-6 rounded-sm border border-[rgba(34,211,238,0.3)] bg-[rgba(34,211,238,0.05)]">
              <span className="absolute inset-0 rounded-sm anim-pulse-ring-slow bg-[rgba(34,211,238,0.32)] opacity-20" />
              <Radar className="w-3 h-3 text-[var(--color-ice-400)]" strokeWidth={1.5} />
            </span>
            <span className="text-[10px] font-semibold tracking-[0.28em] text-[var(--color-text-bright)] hidden sm:inline">
              SHADOW
            </span>
          </button>

          {/* Nav */}
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = isMatch(item);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={item.label}
                className={cn(
                  'relative h-7 px-2.5 inline-flex items-center gap-1.5 rounded-full transition-colors font-mono text-[10px] tracking-[0.22em] uppercase',
                  active
                    ? 'text-[var(--color-ice-400)] bg-[rgba(34,211,238,0.10)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[rgba(148,163,184,0.04)]'
                )}
              >
                <Icon className="w-3 h-3" strokeWidth={1.4} />
                <span className="hidden lg:inline">{item.label}</span>
              </NavLink>
            );
          })}

          <span className="w-px h-5 bg-[var(--color-line-soft)] mx-1" />

          {/* Right cluster */}
          <button
            onClick={() => {
              setSearchOpen(true);
              setNotifOpen(false);
            }}
            title="search · ⌘K"
            className="h-7 px-2.5 inline-flex items-center gap-1.5 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.05)]"
          >
            <Search className="w-3 h-3" strokeWidth={1.4} />
            <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase hidden md:inline">
              search
            </span>
            <span className="kbd text-[8.5px] hidden md:inline">⌘K</span>
          </button>

          <button
            ref={bellRef}
            data-nav-bell="1"
            onClick={() => {
              setNotifAnchor(computeNotifAnchor());
              setNotifOpen((v) => !v);
              setSearchOpen(false);
            }}
            title="notifications"
            className={cn(
              'relative h-7 px-2 inline-flex items-center justify-center rounded-full',
              notifOpen
                ? 'text-[var(--color-ice-400)] bg-[rgba(34,211,238,0.08)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.05)]'
            )}
          >
            <Bell className="w-3 h-3" strokeWidth={1.4} />
            {notifTotal > 0 && (
              <span
                className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] px-1 inline-flex items-center justify-center rounded-full font-mono text-[8.5px] font-medium text-[var(--color-void)]"
                style={{ background: 'var(--color-rose-400)' }}
              >
                {notifTotal > 99 ? '99+' : notifTotal}
              </span>
            )}
          </button>

          <EnvironmentControl />
          <FocusModeButton />

          {/* Analyst chip */}
          <div className="h-7 pl-2 pr-1 ml-1 inline-flex items-center gap-1.5 rounded-full border border-[var(--color-line-soft)]">
            <span
              className="inline-flex items-center justify-center w-5 h-5 rounded-full"
              style={{
                background: 'rgba(34,211,238,0.10)',
                color: 'var(--color-ice-400)',
              }}
            >
              <User className="w-2.5 h-2.5" strokeWidth={1.5} />
            </span>
            <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-secondary)] pr-1 hidden md:inline">
              0xA1
            </span>
          </div>
        </div>
      </motion.div>

      {/* Autosave + session vault chip — bottom-right unless focus mode */}
      <AnimatePresence>
        {!focusModeOn && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.25 }}
            className="fixed bottom-3 right-3 z-[55] pointer-events-auto"
          >
            <button
              onClick={() => navigate('/sessions')}
              className="veil flex items-center gap-2 h-7 px-2.5 rounded-full font-mono text-[9.5px] tracking-[0.12em] lowercase text-[var(--color-text-muted)] hover:text-[var(--color-emerald-400)] transition-colors"
              title="autosaved · open vault"
            >
              <span className="relative inline-flex w-1.5 h-1.5">
                <span className="absolute inset-0 rounded-full bg-[var(--color-emerald-400)] anim-pulse-ring-slow opacity-40" />
                <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-[var(--color-emerald-400)]" />
              </span>
              <span>synced · {formatTime(lastSavedAt)}</span>
              <span className="text-[var(--color-text-faint)]">·</span>
              <Archive className="w-3 h-3" />
              <span className="hidden md:inline">vault</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search modal */}
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Notification panel */}
      <NotificationCenter
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
        anchor={notifAnchor}
      />

      {/* Tiny ghost edge — when nav is hidden, show a thin tab to summon it */}
      <AnimatePresence>
        {hidden && !focusModeOn && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            whileHover={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setHidden(false)}
            className="fixed top-0 left-1/2 -translate-x-1/2 z-[55] w-24 h-1 rounded-b bg-gradient-to-b from-[rgba(34,211,238,0.4)] to-transparent"
            aria-label="show nav"
          />
        )}
      </AnimatePresence>
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* EnvironmentControl                                                          */
/*                                                                             */
/* Replaces the binary reduce-motion toggle with a 3-mode operational           */
/* atmosphere selector. Each mode coordinates motion intensity, fog density,   */
/* and glow restraint via the global `data-env-mode` attribute + store state.  */
/* -------------------------------------------------------------------------- */

interface EnvOption {
  id: EnvMode;
  label: string;
  sub: string;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  accent: string;
  tint: string;
}

const ENV_OPTIONS: EnvOption[] = [
  {
    id: 'ambient',
    label: 'ambient',
    sub: 'default · breathing atmosphere',
    icon: Waves,
    accent: 'var(--color-ice-400)',
    tint: 'rgba(34,211,238,0.10)',
  },
  {
    id: 'calm',
    label: 'calm',
    sub: 'reduced motion · softened light',
    icon: Moon,
    accent: 'var(--color-emerald-400)',
    tint: 'rgba(16,185,129,0.10)',
  },
  {
    id: 'cinematic',
    label: 'cinematic',
    sub: 'heightened depth · richer glow',
    icon: Sparkles,
    accent: 'var(--color-violet-400)',
    tint: 'rgba(168,85,247,0.10)',
  },
];

function EnvironmentControl() {
  const envMode = useIntelStore((s) => s.envMode);
  const setEnvMode = useIntelStore((s) => s.setEnvMode);
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [anchor, setAnchor] = useState<{ x: number; y: number } | null>(null);

  const current = ENV_OPTIONS.find((o) => o.id === envMode) ?? ENV_OPTIONS[0];
  const CurIcon = current.icon;

  // Anchor the popover to the button center, recomputed on resize.
  useEffect(() => {
    if (!open) return;
    const compute = () => {
      const el = btnRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      setAnchor({ x: r.left + r.width / 2, y: r.bottom + 8 });
    };
    compute();
    window.addEventListener('resize', compute);
    return () => window.removeEventListener('resize', compute);
  }, [open]);

  // Dismiss on outside click + Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (!t) return;
      if (btnRef.current?.contains(t)) return;
      if (t.closest('[data-env-popover="1"]')) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <>
      <button
        ref={btnRef}
        onClick={() => setOpen((v) => !v)}
        title={`environment · ${current.label}`}
        className={cn(
          'relative h-7 w-7 inline-flex items-center justify-center rounded-full transition-colors active:scale-[0.94]'
        )}
        style={{
          color: open || envMode !== 'ambient' ? current.accent : 'var(--color-text-muted)',
          background: open ? current.tint : 'transparent',
        }}
      >
        <CurIcon className="w-3 h-3 relative" strokeWidth={1.4} />
        {/* Mode dot — tiny status pip under the icon */}
        <span
          className="absolute bottom-[3px] left-1/2 -translate-x-1/2 w-[3px] h-[3px] rounded-full transition-opacity"
          style={{
            background: current.accent,
            opacity: open || envMode !== 'ambient' ? 0.9 : 0.45,
          }}
        />
      </button>

      <AnimatePresence>
        {open && anchor && (
          <motion.div
            key="env-popover"
            data-env-popover="1"
            initial={{ opacity: 0, y: -6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="fixed z-[80]"
            style={{
              left: anchor.x,
              top: anchor.y,
              transform: 'translateX(-50%)',
            }}
          >
            <div className="surface-floating w-[268px] p-1.5">
              <div className="px-2 py-1.5 flex items-center gap-2">
                <span className="font-mono text-[9px] tracking-[0.28em] uppercase text-[var(--color-text-muted)]">
                  environment
                </span>
                <span className="ml-auto font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-faint)]">
                  {current.label}
                </span>
              </div>
              <div className="space-y-0.5">
                {ENV_OPTIONS.map((m) => {
                  const active = envMode === m.id;
                  const Icon = m.icon;
                  return (
                    <button
                      key={m.id}
                      onClick={() => {
                        setEnvMode(m.id);
                        setOpen(false);
                      }}
                      className="w-full text-left rounded-sm px-2 py-1.5 flex items-center gap-2.5 transition-colors hover:bg-[rgba(148,163,184,0.04)]"
                      style={active ? { background: m.tint } : undefined}
                    >
                      <span
                        className="inline-flex items-center justify-center w-6 h-6 rounded-sm shrink-0 transition-colors"
                        style={{
                          background: active ? m.tint : 'rgba(148,163,184,0.04)',
                          color: active ? m.accent : 'var(--color-text-muted)',
                        }}
                      >
                        <Icon className="w-3 h-3" strokeWidth={1.4} />
                      </span>
                      <div className="flex-1 min-w-0">
                        <div
                          className="text-[11.5px] leading-tight"
                          style={{
                            color: active
                              ? m.accent
                              : 'var(--color-text-primary)',
                          }}
                        >
                          {m.label}
                        </div>
                        <div className="font-mono text-[9.5px] tracking-[0.10em] lowercase text-[var(--color-text-muted)] truncate">
                          {m.sub}
                        </div>
                      </div>
                      {active && (
                        <Check
                          className="w-3 h-3 shrink-0"
                          style={{ color: m.accent }}
                          strokeWidth={1.8}
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* FocusModeButton                                                             */
/*                                                                             */
/* Cinematic focus toggle. The state flip is instantaneous (so the chrome      */
/* components can run their exit animations) — the button itself emits a      */
/* one-shot halo pulse keyed off `focusTransitionId`, which bumps on every     */
/* toggle regardless of source (mouse, F key, rail footer).                    */
/* -------------------------------------------------------------------------- */

function FocusModeButton() {
  const focusModeOn = useIntelStore((s) => s.focusModeOn);
  const setFocusModeOn = useIntelStore((s) => s.setFocusModeOn);
  const transitionId = useIntelStore((s) => s.focusTransitionId);

  return (
    <button
      onClick={() => setFocusModeOn(!focusModeOn)}
      title={focusModeOn ? 'exit focus · F' : 'graph focus · F'}
      className={cn(
        'relative h-7 w-7 inline-flex items-center justify-center rounded-full overflow-visible transition-colors active:scale-[0.94]',
        focusModeOn
          ? 'text-[var(--color-violet-400)] bg-[rgba(168,85,247,0.08)]'
          : 'text-[var(--color-text-muted)] hover:text-[var(--color-violet-400)] hover:bg-[rgba(168,85,247,0.05)]'
      )}
    >
      {/* One-shot halo pulse, keyed by transitionId so it replays on each toggle */}
      {transitionId > 0 && (
        <motion.span
          key={transitionId}
          initial={{ opacity: 0.55, scale: 1 }}
          animate={{ opacity: 0, scale: 2.6 }}
          transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            background:
              'radial-gradient(circle, rgba(168,85,247,0.45), rgba(168,85,247,0) 65%)',
          }}
        />
      )}
      {focusModeOn ? (
        <Minimize2 className="w-3 h-3 relative" strokeWidth={1.4} />
      ) : (
        <Maximize2 className="w-3 h-3 relative" strokeWidth={1.4} />
      )}
    </button>
  );
}
