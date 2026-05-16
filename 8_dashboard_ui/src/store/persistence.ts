/**
 * Persistence layer for the intel-store.
 *
 *  • Only analyst-owned state is persisted (bookmarks, notes, pinned evidence,
 *    saved sessions, dismissed notifications, comfort prefs).
 *  • Investigation runtime state (events, progress, surfaced sets) is NOT
 *    persisted — those reset on reload, which is correct: an analyst restarting
 *    the platform shouldn't resume mid-stream.
 *  • Sets are serialized as arrays; rehydrated back into Sets on load.
 */

import type { Session } from '@/types/intel';

const STORAGE_KEY = 'shadow:intel:v1';

export type EnvMode = 'ambient' | 'calm' | 'cinematic';

export interface PersistedShape {
  sessions: Session[];
  bookmarkedEntities: string[];
  pinnedEvidence: string[];
  dismissedNotifications: string[];
  notes: Record<string, string>;
  reduceMotion: boolean;
  graphCalmMode: boolean;
  envMode: EnvMode;
}

const DEFAULT: PersistedShape = {
  sessions: [],
  bookmarkedEntities: [],
  pinnedEvidence: [],
  dismissedNotifications: [],
  notes: {},
  reduceMotion: false,
  graphCalmMode: false,
  envMode: 'ambient',
};

/** Load — returns DEFAULT on first run or on parse failure. */
export function loadPersisted(): PersistedShape {
  if (typeof window === 'undefined') return DEFAULT;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT;
    const parsed = JSON.parse(raw) as Partial<PersistedShape>;
    const envMode: EnvMode =
      parsed.envMode === 'calm' || parsed.envMode === 'cinematic' || parsed.envMode === 'ambient'
        ? parsed.envMode
        : parsed.reduceMotion
        ? 'calm'
        : 'ambient';
    return {
      ...DEFAULT,
      ...parsed,
      envMode,
      // Defensive: coerce arrays
      sessions: Array.isArray(parsed.sessions) ? parsed.sessions : [],
      bookmarkedEntities: Array.isArray(parsed.bookmarkedEntities)
        ? parsed.bookmarkedEntities
        : [],
      pinnedEvidence: Array.isArray(parsed.pinnedEvidence) ? parsed.pinnedEvidence : [],
      dismissedNotifications: Array.isArray(parsed.dismissedNotifications)
        ? parsed.dismissedNotifications
        : [],
      notes:
        parsed.notes && typeof parsed.notes === 'object' && !Array.isArray(parsed.notes)
          ? (parsed.notes as Record<string, string>)
          : {},
    };
  } catch {
    return DEFAULT;
  }
}

/** Save — debounced via the caller (intel-store wraps writes in rAF). */
export function savePersisted(shape: PersistedShape): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(shape));
  } catch {
    /* quota / disabled storage — silent fail */
  }
}

/** Clear — used by a "reset platform" affordance if we add one. */
export function clearPersisted(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* silent */
  }
}
