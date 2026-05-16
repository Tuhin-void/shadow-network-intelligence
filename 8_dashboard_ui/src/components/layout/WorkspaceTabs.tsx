import {
  Bookmark,
  CircleDot,
  FolderOpen,
  GalleryVerticalEnd,
  Layers,
  Pin,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useIntelStore, type TacticalTab } from '@/store/intel-store';
import { cn } from '@/lib/utils';
import type { ComponentType } from 'react';

const TABS: Array<{
  id: TacticalTab;
  label: string;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
}> = [
  { id: 'cases', label: 'Cases', icon: FolderOpen },
  { id: 'rings', label: 'Rings', icon: CircleDot },
  { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark },
  { id: 'evidence', label: 'Pinned', icon: Pin },
  { id: 'filters', label: 'Filters', icon: Layers },
  { id: 'replay', label: 'Replay', icon: GalleryVerticalEnd },
];

/**
 * WorkspaceTabs — horizontal micro-strip just below the floating nav.
 *
 * Provides instant 1-click discoverability for investigation tooling.
 * Each tab drives the same `tacticalTab` store state as the rail —
 * clicking a tab opens its panel; clicking it again collapses.
 *
 * Auto-hides in focus mode.
 */
export function WorkspaceTabs({
  bookmarkedCount = 0,
  pinnedCount = 0,
}: {
  bookmarkedCount?: number;
  pinnedCount?: number;
}) {
  const tab = useIntelStore((s) => s.tacticalTab);
  const setTab = useIntelStore((s) => s.setTacticalTab);
  const focusModeOn = useIntelStore((s) => s.focusModeOn);

  return (
    <AnimatePresence>
      {!focusModeOn && (
        <motion.div
          key="workspace-tabs"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1], delay: 0 }}
          className="absolute top-[56px] left-0 right-0 z-20 flex items-center justify-center pointer-events-none"
        >
      <div className="pointer-events-auto veil h-8 px-1 flex items-center gap-0.5 rounded-full">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          const count =
            t.id === 'bookmarks'
              ? bookmarkedCount
              : t.id === 'evidence'
              ? pinnedCount
              : null;
          return (
            <button
              key={t.id}
              onClick={() => setTab(active ? null : t.id)}
              className={cn(
                'h-6 px-2.5 inline-flex items-center gap-1.5 rounded-full font-mono text-[10px] tracking-[0.22em] uppercase transition-colors',
                active
                  ? 'text-[var(--color-ice-400)] bg-[rgba(34,211,238,0.10)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[rgba(148,163,184,0.04)]'
              )}
            >
              <Icon className="w-3 h-3" strokeWidth={1.4} />
              <span className="hidden sm:inline">{t.label}</span>
              {count !== null && count > 0 && (
                <span
                  className="font-mono text-[8.5px] tracking-normal px-1 rounded-full"
                  style={{
                    background: 'rgba(34,211,238,0.18)',
                    color: 'var(--color-ice-400)',
                  }}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
