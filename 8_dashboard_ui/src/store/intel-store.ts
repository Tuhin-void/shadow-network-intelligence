import { create } from 'zustand';
import type {
  Entity,
  PresetSnapshot,
  Session,
  StreamEvent,
} from '@/types/intel';
import { listPresets, getPreset, defaultPreset } from '@/lib/presets';
import { playStream, type StreamHandle } from '@/lib/sse-engine';
import type { QueryTransform } from '@/lib/queries';
import type { DataSource, IngestionRun, SchemaMapping } from '@/types/sources';
import {
  INITIAL_SOURCES,
  INITIAL_MAPPINGS,
  INITIAL_RUNS,
} from '@/lib/sources-mock';
import {
  loadPersisted,
  savePersisted,
  type EnvMode,
  type PersistedShape,
} from './persistence';
import { api } from '@/lib/api-client';
import {
  buildSnapshotFromBackendReport,
  transformBackendStreamEvent,
  transformOrchestratorStatus,
  transformBackendPresetList,
  type ConnectionStatus,
  type LivePresetSummary,
} from '@/lib/adapters';
import {
  transformDeepReport,
  type BackendDeepReport,
  type CognitiveReport,
} from '@/lib/adapters/cognitive';

export type { EnvMode };

type FocusMode = 'overview' | 'rings' | 'hidden' | 'paths' | 'risk';
type StreamingPhase = 'idle' | 'streaming' | 'complete';
type RunMode = 'auto' | 'manual';
export type TacticalTab =
  | 'cases'
  | 'bookmarks'
  | 'rings'
  | 'evidence'
  | 'filters'
  | 'replay';

interface IntelState {
  presets: PresetSnapshot[];

  activePresetId: string;
  active: PresetSnapshot;

  events: StreamEvent[];
  /** map of section -> count seen, for progressive 9-section panel */
  sectionCounts: Record<string, number>;
  /** entity ids that have been "discovered" so far during the current run */
  discoveredEntities: Set<string>;
  /** edge ids that have been "traversed" so far */
  traversedEdges: Set<string>;
  /** path ids that have been surfaced */
  surfacedPaths: Set<string>;
  /** ring ids surfaced */
  surfacedRings: Set<string>;

  selectedEntityId: string | null;
  focusMode: FocusMode;
  streamingPhase: StreamingPhase;
  progress: number;
  speed: 0.5 | 1 | 2 | 4;

  /** auto = play stream automatically; manual = analyst steps through events */
  runMode: RunMode;
  /** position in preset.stream when in manual mode */
  stepIndex: number;

  sessions: Session[];

  /* actions */
  selectPreset: (id: string) => void;
  startStream: () => void;
  stopStream: () => void;
  resetStream: () => void;
  pushEvent: (e: StreamEvent, progress: number) => void;
  selectEntity: (id: string | null) => void;
  setFocusMode: (m: FocusMode) => void;
  setSpeed: (s: 0.5 | 1 | 2 | 4) => void;
  setRunMode: (m: RunMode) => void;
  stepForward: () => void;
  stepBack: () => void;
  saveSession: (title?: string) => void;
  replaySession: (sessionId: string) => void;
  /** Apply a graph-transforming investigation query result. */
  applyQuery: (t: QueryTransform) => void;

  /** Optional narration line set by the last query (or stream event). */
  narration: string | null;

  /** When true, the chrome (nav, rails) fades so the graph dominates. */
  focusModeOn: boolean;
  setFocusModeOn: (v: boolean) => void;
  /** Bumps every time focusModeOn toggles — used by the focus button to
   *  trigger a one-shot halo pulse regardless of which actor flipped it. */
  focusTransitionId: number;
  /** ISO timestamp of the last autosave-eligible state change. */
  lastSavedAt: string;
  /** Dismissed notification ids. */
  dismissedNotifications: Set<string>;
  dismissNotification: (id: string) => void;
  clearDismissedNotifications: () => void;

  /** Bookmarked entities — analyst's pinned-of-interest set. */
  bookmarkedEntities: Set<string>;
  toggleBookmark: (id: string) => void;
  /** Pinned evidence — selected evidence the analyst wants to keep visible. */
  pinnedEvidence: Set<string>;
  togglePinEvidence: (id: string) => void;

  /** Analyst notes keyed by entity id — survives reload */
  notes: Record<string, string>;
  setNote: (entityId: string, body: string) => void;
  clearNote: (entityId: string) => void;

  /** Comfort prefs */
  reduceMotion: boolean;
  graphCalmMode: boolean;
  setReduceMotion: (v: boolean) => void;
  setGraphCalmMode: (v: boolean) => void;

  /** Coordinated operational atmosphere — the single source of truth for
   *  ambient motion intensity, fog density, glow restraint. */
  envMode: EnvMode;
  setEnvMode: (m: EnvMode) => void;

  /** Tactical rail's currently-open tab. null = panel collapsed. */
  tacticalTab: TacticalTab | null;
  setTacticalTab: (t: TacticalTab | null) => void;

  /** Connected data sources */
  dataSources: DataSource[];
  /** Per-source schema mappings */
  schemaMappings: Record<string, SchemaMapping>;
  /** Recent ingestion runs (oldest → newest) */
  ingestionRuns: IngestionRun[];
  /** Currently focused source id in the workspace */
  focusedSourceId: string | null;
  focusSource: (id: string | null) => void;
  /** Toggle source pause/resume */
  setSourceStatus: (id: string, status: DataSource['status']) => void;
  /** Trigger a mock ingestion run for the given source */
  triggerIngestionRun: (sourceId: string) => void;

  /* -------- Live backend integration (opt-in; mock pathway untouched) ----- */
  /** ConnectionStatus from /orchestrator/status, or null if backend unreached. */
  backendStatus: ConnectionStatus | null;
  /** Last connection-probe error message, if any. */
  backendError: string | null;
  /** Curated demo presets fetched from /demo/presets. */
  livePresets: LivePresetSummary[];
  /** Active live-preset key, if a live investigation is currently selected. */
  activeLivePresetKey: string | null;
  /** Phase of a live SSE stream. Mirrors `streamingPhase` but lives separately
   *  so mock and live can coexist without state collisions. */
  liveStreamPhase: 'idle' | 'streaming' | 'complete' | 'error';
  /** Last live-stream error message, if any. */
  liveStreamError: string | null;

  /** Probe /orchestrator/status — populates `backendStatus` or `backendError`. */
  checkBackend: () => Promise<void>;
  /** Fetch /demo/presets — populates `livePresets`. */
  loadLivePresets: () => Promise<void>;
  /** Run a live preset synchronously; activates the resulting snapshot. */
  runLivePreset: (presetKey: string) => Promise<void>;
  /** Stream a live preset; pushes adapted events through `pushEvent` and
   *  swaps `active` to the synthesized snapshot when report.finalized fires. */
  startLiveStream: (presetKey: string) => Promise<void>;
  /** Abort any in-flight live SSE stream. */
  stopLiveStream: () => void;
  /** Activate a synthesized PresetSnapshot (built from a live report) as if
   *  the analyst had clicked it in the preset queue. Mock presets are
   *  unaffected. */
  activateLiveSnapshot: (snap: PresetSnapshot) => void;

  /* -------- Cognitive deep-investigation slice -------------------------- */
  /** Most recent CognitiveReport from POST /investigate/deep. */
  cognitiveReport: CognitiveReport | null;
  /** Phase of the deep-investigation request. */
  cognitivePhase: 'idle' | 'running' | 'complete' | 'error';
  /** Last deep-investigation error message, if any. */
  cognitiveError: string | null;
  /** Run a deep investigation for the named live preset. */
  runDeepInvestigation: (presetKey: string) => Promise<void>;
  /** Run a deep investigation for an ad-hoc query. */
  runDeepQuery: (query: string, opts?: { top_k?: number; depth?: number }) => Promise<void>;
  /** Clear cognitive state. */
  clearCognitiveReport: () => void;
}

let handle: StreamHandle | null = null;
/** Module-scoped abort controller for the active live SSE stream. */
let liveAbort: AbortController | null = null;

function applyEventToState(state: IntelState, e: StreamEvent): Partial<IntelState> {
  const discovered = new Set(state.discoveredEntities);
  const traversed = new Set(state.traversedEdges);
  const surfacedPaths = new Set(state.surfacedPaths);
  const surfacedRings = new Set(state.surfacedRings);
  const sectionCounts = { ...state.sectionCounts };

  const refs = e.refs ?? [];
  if (e.kind === 'entity.discovered' || e.kind === 'topology.expanded') {
    refs.forEach((id) => {
      const ent = state.active.graph.entities.find((x) => x.id === id);
      if (ent) discovered.add(id);
    });
  }
  if (e.kind === 'edge.traversed') {
    refs.forEach((id) => traversed.add(id));
  }
  if (e.kind === 'path.discovered') {
    refs.forEach((id) => surfacedPaths.add(id));
    // pull entities + edges from path
    const p = state.active.paths.find((x) => x.id === refs[0]);
    if (p) {
      p.nodes.forEach((n) => discovered.add(n));
    }
  }
  if (e.kind === 'ring.detected') {
    refs.forEach((id) => surfacedRings.add(id));
    const ring = state.active.rings.find((r) => r.id === refs[0]);
    if (ring) ring.members.forEach((m) => discovered.add(m));
  }
  if (e.kind === 'hidden.relationship') {
    const h = state.active.hidden.find((x) => x.id === refs[0]);
    if (h) {
      discovered.add(h.from);
      discovered.add(h.to);
      h.via.forEach((v) => discovered.add(v));
    }
  }

  if (e.section) {
    sectionCounts[e.section] = (sectionCounts[e.section] ?? 0) + 1;
  }

  return {
    discoveredEntities: discovered,
    traversedEdges: traversed,
    surfacedPaths,
    surfacedRings,
    sectionCounts,
  };
}

export const useIntelStore = create<IntelState>((set, get) => ({
  presets: listPresets(),
  activePresetId: defaultPreset().id,
  active: defaultPreset(),

  events: [],
  sectionCounts: {},
  discoveredEntities: new Set([defaultPreset().seed]),
  traversedEdges: new Set(),
  surfacedPaths: new Set(),
  surfacedRings: new Set(),

  selectedEntityId: defaultPreset().seed,
  focusMode: 'overview',
  streamingPhase: 'idle',
  progress: 0,
  speed: 1,

  runMode: 'auto',
  stepIndex: 0,

  // Sessions + dismissed notifications rehydrate from localStorage too
  sessions: loadPersisted().sessions,
  narration: null,
  focusModeOn: false,
  focusTransitionId: 0,
  lastSavedAt: new Date().toISOString(),
  dismissedNotifications: new Set(loadPersisted().dismissedNotifications),
  // Rehydrated from localStorage if available
  bookmarkedEntities: new Set(loadPersisted().bookmarkedEntities),
  pinnedEvidence: new Set(loadPersisted().pinnedEvidence),
  notes: loadPersisted().notes,
  reduceMotion:
    loadPersisted().envMode === 'calm' ? true : loadPersisted().reduceMotion,
  graphCalmMode:
    loadPersisted().envMode === 'calm' ? true : loadPersisted().graphCalmMode,
  envMode: loadPersisted().envMode,
  tacticalTab: null,
  dataSources: INITIAL_SOURCES,
  schemaMappings: INITIAL_MAPPINGS,
  ingestionRuns: INITIAL_RUNS,
  focusedSourceId: INITIAL_SOURCES[0]?.id ?? null,

  selectPreset: (id) => {
    const preset = getPreset(id);
    if (!preset) return;
    if (handle) {
      handle.stop();
      handle = null;
    }
    set({
      activePresetId: id,
      active: preset,
      events: [],
      sectionCounts: {},
      discoveredEntities: new Set([preset.seed]),
      traversedEdges: new Set(),
      surfacedPaths: new Set(),
      surfacedRings: new Set(),
      selectedEntityId: preset.seed,
      streamingPhase: 'idle',
      progress: 0,
      stepIndex: 0,
    });
  },

  startStream: () => {
    const state = get();
    if (handle) handle.stop();
    set({
      events: [],
      sectionCounts: {},
      discoveredEntities: new Set([state.active.seed]),
      traversedEdges: new Set(),
      surfacedPaths: new Set(),
      surfacedRings: new Set(),
      streamingPhase: 'streaming',
      progress: 0,
      stepIndex: 0,
    });
    // In manual mode, just arm the run — analyst will step.
    if (state.runMode === 'manual') {
      set({ streamingPhase: 'idle' });
      return;
    }
    handle = playStream(
      state.active,
      (e, progress) => get().pushEvent(e, progress),
      {
        speed: state.speed,
        onComplete: () => {
          set({ streamingPhase: 'complete', progress: 1 });
          get().saveSession();
          handle = null;
        },
      }
    );
  },

  stopStream: () => {
    if (handle) {
      handle.stop();
      handle = null;
    }
    set({ streamingPhase: 'complete' });
  },

  resetStream: () => {
    if (handle) {
      handle.stop();
      handle = null;
    }
    const preset = get().active;
    set({
      events: [],
      sectionCounts: {},
      discoveredEntities: new Set([preset.seed]),
      traversedEdges: new Set(),
      surfacedPaths: new Set(),
      surfacedRings: new Set(),
      streamingPhase: 'idle',
      progress: 0,
      stepIndex: 0,
    });
  },

  setRunMode: (m) => {
    if (handle) {
      handle.stop();
      handle = null;
    }
    const preset = get().active;
    set({
      runMode: m,
      events: [],
      sectionCounts: {},
      discoveredEntities: new Set([preset.seed]),
      traversedEdges: new Set(),
      surfacedPaths: new Set(),
      surfacedRings: new Set(),
      streamingPhase: 'idle',
      progress: 0,
      stepIndex: 0,
    });
  },

  stepForward: () => {
    const state = get();
    const stream = state.active.stream;
    if (state.stepIndex >= stream.length) return;
    const next = stream[state.stepIndex];
    const stamped: StreamEvent = { ...next, at: new Date().toISOString() };
    const newIndex = state.stepIndex + 1;
    const progress = newIndex / stream.length;
    set({
      events: [...state.events, stamped],
      progress,
      stepIndex: newIndex,
      streamingPhase: newIndex >= stream.length ? 'complete' : 'streaming',
      ...applyEventToState(state, stamped),
    });
    if (newIndex >= stream.length) {
      get().saveSession();
    }
  },

  stepBack: () => {
    const state = get();
    if (state.stepIndex <= 0) return;
    const newIndex = state.stepIndex - 1;
    const truncated = state.events.slice(0, newIndex);
    // Rebuild derived sets from scratch by replaying the truncated events.
    const preset = state.active;
    let rebuilt: Partial<IntelState> = {
      events: truncated,
      sectionCounts: {},
      discoveredEntities: new Set([preset.seed]),
      traversedEdges: new Set(),
      surfacedPaths: new Set(),
      surfacedRings: new Set(),
    };
    let scratch: IntelState = { ...state, ...rebuilt } as IntelState;
    truncated.forEach((e) => {
      const delta = applyEventToState(scratch, e);
      scratch = { ...scratch, ...delta } as IntelState;
      rebuilt = { ...rebuilt, ...delta };
    });
    set({
      ...rebuilt,
      stepIndex: newIndex,
      progress: newIndex / preset.stream.length,
      streamingPhase: newIndex === 0 ? 'idle' : 'streaming',
    });
  },

  pushEvent: (e, progress) => {
    const state = get();
    set({
      events: [...state.events, e].slice(-200),
      progress,
      lastSavedAt: new Date().toISOString(),
      ...applyEventToState(state, e),
    });
  },

  selectEntity: (id) => set({ selectedEntityId: id }),
  setFocusMode: (m) => set({ focusMode: m }),
  setSpeed: (s) => set({ speed: s }),

  saveSession: (title?: string) => {
    const state = get();
    const id = `S-${Date.now().toString(36).toUpperCase()}`;
    const session: Session = {
      id,
      presetId: state.activePresetId,
      title: title ?? `${state.active.label} • ${new Date().toLocaleTimeString()}`,
      status: state.streamingPhase === 'complete' ? 'complete' : 'streaming',
      startedAt: state.events[0]?.at ?? new Date().toISOString(),
      completedAt:
        state.streamingPhase === 'complete' ? new Date().toISOString() : undefined,
      events: state.events,
      progress: state.progress,
      analyst: 'analyst.0xA1',
    };
    set({ sessions: [session, ...state.sessions].slice(0, 24) });
  },

  setFocusModeOn: (v) =>
    set((s) => ({
      focusModeOn: v,
      focusTransitionId: s.focusTransitionId + 1,
    })),
  toggleBookmark: (id) =>
    set((state) => {
      const next = new Set(state.bookmarkedEntities);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { bookmarkedEntities: next };
    }),
  togglePinEvidence: (id) =>
    set((state) => {
      const next = new Set(state.pinnedEvidence);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { pinnedEvidence: next };
    }),
  focusSource: (id) => set({ focusedSourceId: id }),
  setSourceStatus: (id, status) =>
    set((state) => ({
      dataSources: state.dataSources.map((s) =>
        s.id === id
          ? { ...s, status, health: status === 'paused' ? 'idle' : s.health }
          : s
      ),
      lastSavedAt: new Date().toISOString(),
    })),
  /* ----- Live backend slice ----- */
  backendStatus: null,
  backendError: null,
  livePresets: [],
  activeLivePresetKey: null,
  liveStreamPhase: 'idle',
  liveStreamError: null,

  checkBackend: async () => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 4000);
    try {
      const raw = await api.orchestratorStatus(ctrl.signal);
      set({
        backendStatus: transformOrchestratorStatus(raw),
        backendError: null,
      });
    } catch (e) {
      set({
        backendStatus: null,
        backendError: e instanceof Error ? e.message : String(e),
      });
    } finally {
      clearTimeout(timer);
    }
  },

  loadLivePresets: async () => {
    try {
      const { presets } = await api.listPresets();
      set({ livePresets: transformBackendPresetList(presets) });
    } catch {
      // Silent — UI inspects `livePresets.length === 0` to know.
    }
  },

  runLivePreset: async (presetKey) => {
    const meta = get().livePresets.find((p) => p.key === presetKey) ?? {
      key: presetKey,
      title: presetKey,
      showcases: [],
      tone: 'ice' as const,
    };
    set({
      activeLivePresetKey: presetKey,
      liveStreamPhase: 'streaming',
      liveStreamError: null,
    });
    try {
      const res = await api.runDemoPreset(presetKey);
      const snap = buildSnapshotFromBackendReport(meta, res.report);
      get().activateLiveSnapshot(snap);
      set({ liveStreamPhase: 'complete', progress: 1 });
    } catch (e) {
      set({
        liveStreamPhase: 'error',
        liveStreamError: e instanceof Error ? e.message : String(e),
      });
    }
  },

  startLiveStream: async (presetKey) => {
    if (liveAbort) liveAbort.abort();
    liveAbort = new AbortController();
    const meta = get().livePresets.find((p) => p.key === presetKey) ?? {
      key: presetKey,
      title: presetKey,
      showcases: [],
      tone: 'ice' as const,
    };
    set({
      activeLivePresetKey: presetKey,
      liveStreamPhase: 'streaming',
      liveStreamError: null,
      events: [],
      sectionCounts: {},
      progress: 0,
    });
    try {
      let seq = 0;
      for await (const env of api.streamDemoPreset(
        presetKey,
        {},
        liveAbort.signal,
      )) {
        // Build live snapshot when report finalizes; swap `active` to it.
        if (env.kind === 'report.finalized') {
          const report = env.payload as unknown as Parameters<
            typeof buildSnapshotFromBackendReport
          >[1];
          const snap = buildSnapshotFromBackendReport(meta, report);
          get().activateLiveSnapshot(snap);
        }
        const ev = transformBackendStreamEvent(env, { seqOffset: 0 });
        if (!ev) continue;
        seq += 1;
        // The local seq overrides backend seq to keep UI ordering monotonic
        // across multiple streams within a session.
        const stamped: StreamEvent = { ...ev, seq };
        // Synthetic progress: monotonically increase toward 1 with each
        // event, snapping to 1 on session.complete.
        const progress =
          stamped.kind === 'session.complete'
            ? 1
            : Math.min(0.95, (get().progress ?? 0) + 0.06);
        get().pushEvent(stamped, progress);
      }
      set({ liveStreamPhase: 'complete', progress: 1 });
    } catch (e) {
      if ((e as { name?: string })?.name === 'AbortError') {
        set({ liveStreamPhase: 'idle' });
      } else {
        set({
          liveStreamPhase: 'error',
          liveStreamError: e instanceof Error ? e.message : String(e),
        });
      }
    } finally {
      liveAbort = null;
    }
  },

  stopLiveStream: () => {
    if (liveAbort) {
      liveAbort.abort();
      liveAbort = null;
    }
    set({ liveStreamPhase: 'idle' });
  },

  /* ----- Cognitive slice ----- */
  cognitiveReport: null,
  cognitivePhase: 'idle',
  cognitiveError: null,

  runDeepInvestigation: async (presetKey) => {
    set({ cognitivePhase: 'running', cognitiveError: null });
    try {
      const raw = await api.runDemoDeep(presetKey);
      const report = transformDeepReport(raw as unknown as BackendDeepReport);
      set({
        cognitiveReport: report,
        cognitivePhase: 'complete',
      });
    } catch (e) {
      set({
        cognitivePhase: 'error',
        cognitiveError: e instanceof Error ? e.message : String(e),
      });
    }
  },

  runDeepQuery: async (query, opts) => {
    set({ cognitivePhase: 'running', cognitiveError: null });
    try {
      const raw = await api.investigateDeep({
        query,
        top_k: opts?.top_k ?? 5,
        depth: opts?.depth ?? 2,
      });
      const report = transformDeepReport(raw as unknown as BackendDeepReport);
      set({
        cognitiveReport: report,
        cognitivePhase: 'complete',
      });
    } catch (e) {
      set({
        cognitivePhase: 'error',
        cognitiveError: e instanceof Error ? e.message : String(e),
      });
    }
  },

  clearCognitiveReport: () =>
    set({ cognitiveReport: null, cognitivePhase: 'idle', cognitiveError: null }),

  activateLiveSnapshot: (snap) => {
    // Stop any mock stream that's running so we don't interleave timelines.
    if (handle) {
      handle.stop();
      handle = null;
    }
    set({
      activePresetId: snap.id,
      active: snap,
      discoveredEntities: new Set(snap.graph.entities.map((e) => e.id)),
      traversedEdges: new Set(snap.graph.edges.map((e) => e.id)),
      surfacedPaths: new Set(snap.paths.map((p) => p.id)),
      surfacedRings: new Set(snap.rings.map((r) => r.id)),
      selectedEntityId: snap.seed,
      streamingPhase: 'complete',
      stepIndex: 0,
      narration: snap.report.narrative.headline,
    });
  },

  triggerIngestionRun: (sourceId) => {
    const state = get();
    const src = state.dataSources.find((s) => s.id === sourceId);
    if (!src) return;
    const run: IngestionRun = {
      id: `run_${Date.now().toString(36).toUpperCase()}`,
      sourceId,
      startedAt: new Date().toISOString(),
      status: 'running',
      rowsRead: 0,
      entitiesAdded: 0,
      edgesAdded: 0,
      ringsDiscovered: 0,
      hiddenLinksFound: 0,
      errors: 0,
      log: [`triggered · cadence ${src.cadence}`, 'connecting…'],
    };
    set({
      ingestionRuns: [run, ...state.ingestionRuns].slice(0, 40),
      dataSources: state.dataSources.map((s) =>
        s.id === sourceId ? { ...s, status: 'syncing' } : s
      ),
      lastSavedAt: new Date().toISOString(),
    });
    // Simulate completion ~2.4s later
    setTimeout(() => {
      const rowsRead = Math.floor(2000 + Math.random() * 18_000);
      const entitiesAdded = Math.floor(rowsRead * (0.04 + Math.random() * 0.08));
      const edgesAdded = Math.floor(entitiesAdded * (1.4 + Math.random() * 1.2));
      const ringsDiscovered = Math.random() > 0.6 ? 1 : 0;
      const hiddenLinksFound = Math.floor(Math.random() * 4);

      // Inject 2-4 fresh entities + edges into the LIVE preset graph so the
      // analyst sees their data alter the investigation world. Tag them with
      // an `ingested: true` attr so they're identifiable as new.
      const cur = useIntelStore.getState();
      const newEntityCount = 2 + Math.floor(Math.random() * 3);
      const runShort = run.id.slice(-5);
      const ingestedEntities: Entity[] = Array.from({ length: newEntityCount }, (_, i) => {
        const id = `ing_${runShort}_${i}`;
        const kindRoll = Math.random();
        const kind: Entity['kind'] =
          kindRoll < 0.32
            ? 'account'
            : kindRoll < 0.55
            ? 'transaction'
            : kindRoll < 0.74
            ? 'device'
            : kindRoll < 0.88
            ? 'address'
            : 'person';
        const risk = 30 + Math.floor(Math.random() * 65);
        return {
          id,
          label: labelForIngested(kind, runShort, i),
          kind,
          risk,
          tier: risk >= 80 ? 'critical' : risk >= 60 ? 'high' : risk >= 35 ? 'medium' : 'low',
          importance: 3 + Math.floor(Math.random() * 4),
          attrs: { ingested: true, sourceId },
        };
      });
      // Connect each new entity to an existing high-risk anchor in the active graph
      const anchors = cur.active.graph.entities
        .filter((e) => e.risk >= 60)
        .slice(0, 6);
      const ingestedEdges = ingestedEntities.flatMap((ent, i) => {
        const anchor = anchors[i % anchors.length];
        if (!anchor) return [];
        return [
          {
            id: `e_${ent.id}_${anchor.id}`,
            source: ent.id,
            target: anchor.id,
            kind:
              ent.kind === 'transaction' || ent.kind === 'account'
                ? ('transfers' as const)
                : ent.kind === 'device'
                ? ('shares_device' as const)
                : ent.kind === 'address'
                ? ('shares_address' as const)
                : ('controls' as const),
            confidence: 0.7 + Math.random() * 0.25,
            weight: 3 + Math.random() * 4,
            meta: { ingested: true, sourceId },
          },
        ];
      });

      useIntelStore.setState((s) => {
        // Build a new active preset with the ingested elements appended
        const newActive: PresetSnapshot = {
          ...s.active,
          graph: {
            entities: [...s.active.graph.entities, ...ingestedEntities],
            edges: [...s.active.graph.edges, ...ingestedEdges],
          },
        };
        return {
          ingestionRuns: s.ingestionRuns.map((r) =>
            r.id === run.id
              ? {
                  ...r,
                  status: 'success',
                  finishedAt: new Date().toISOString(),
                  rowsRead,
                  entitiesAdded,
                  edgesAdded,
                  ringsDiscovered,
                  hiddenLinksFound,
                  log: [
                    ...r.log,
                    `read ${rowsRead.toLocaleString()} rows`,
                    `entities · +${entitiesAdded.toLocaleString()}`,
                    `edges · +${edgesAdded.toLocaleString()}`,
                    `graph sync · ✓ · +${ingestedEntities.length} live entities into ${s.active.label}`,
                  ],
                }
              : r
          ),
          dataSources: s.dataSources.map((d) =>
            d.id === sourceId
              ? {
                  ...d,
                  status: 'connected',
                  lastSyncAt: new Date().toISOString(),
                  rowsIngested: d.rowsIngested + rowsRead,
                  entitiesProduced: d.entitiesProduced + entitiesAdded,
                  edgesProduced: d.edgesProduced + edgesAdded,
                }
              : d
          ),
          active: newActive,
          // Mark the newly ingested as discovered so they show on the live graph
          discoveredEntities: new Set([
            ...s.discoveredEntities,
            ...ingestedEntities.map((e) => e.id),
          ]),
          narration: `+${ingestedEntities.length} entities ingested into ${s.active.label}`,
          lastSavedAt: new Date().toISOString(),
        };
      });
    }, 2400);
  },
  dismissNotification: (id) =>
    set((state) => ({
      dismissedNotifications: new Set([...state.dismissedNotifications, id]),
    })),
  clearDismissedNotifications: () => set({ dismissedNotifications: new Set() }),

  setNote: (entityId, body) =>
    set((state) => {
      const next = { ...state.notes };
      if (body.trim()) next[entityId] = body;
      else delete next[entityId];
      return { notes: next, lastSavedAt: new Date().toISOString() };
    }),
  clearNote: (entityId) =>
    set((state) => {
      const next = { ...state.notes };
      delete next[entityId];
      return { notes: next };
    }),

  setReduceMotion: (v) => set({ reduceMotion: v }),
  setGraphCalmMode: (v) => set({ graphCalmMode: v }),
  setEnvMode: (m) => {
    applyEnvModeAttribute(m);
    if (m === 'calm') set({ envMode: m, reduceMotion: true, graphCalmMode: true });
    else if (m === 'cinematic')
      set({ envMode: m, reduceMotion: false, graphCalmMode: false });
    else set({ envMode: m, reduceMotion: false, graphCalmMode: false });
  },
  setTacticalTab: (t) => set({ tacticalTab: t }),

  applyQuery: (t) => {
    const state = get();
    const discovered = new Set(state.discoveredEntities);
    (t.discoverEntities ?? []).forEach((id) => discovered.add(id));
    const surfacePaths = new Set(state.surfacedPaths);
    (t.surfacePaths ?? []).forEach((id) => surfacePaths.add(id));
    const surfaceRings = new Set(state.surfacedRings);
    (t.surfaceRings ?? []).forEach((id) => surfaceRings.add(id));
    set({
      focusMode: t.focusMode ?? state.focusMode,
      selectedEntityId:
        t.selectEntityId !== undefined ? t.selectEntityId : state.selectedEntityId,
      discoveredEntities: discovered,
      surfacedPaths: surfacePaths,
      surfacedRings: surfaceRings,
      narration: t.narrationLine,
    });
  },

  replaySession: (sessionId) => {
    const state = get();
    const s = state.sessions.find((x) => x.id === sessionId);
    if (!s) return;
    const preset = getPreset(s.presetId);
    if (!preset) return;
    set({
      activePresetId: preset.id,
      active: preset,
      events: s.events,
      streamingPhase: 'complete',
      progress: 1,
      discoveredEntities: new Set(preset.graph.entities.map((e) => e.id)),
      traversedEdges: new Set(preset.graph.edges.map((e) => e.id)),
      surfacedPaths: new Set(preset.paths.map((p) => p.id)),
      surfacedRings: new Set(preset.rings.map((r) => r.id)),
    });
  },
}));

/* -------------------------------------------------------------------------- */
/* Persistence — debounced auto-save of analyst-owned state                   */
/* -------------------------------------------------------------------------- */
{
  let pendingSave = 0;
  const persist = (state: IntelState) => {
    const shape: PersistedShape = {
      sessions: state.sessions,
      bookmarkedEntities: Array.from(state.bookmarkedEntities),
      pinnedEvidence: Array.from(state.pinnedEvidence),
      dismissedNotifications: Array.from(state.dismissedNotifications),
      notes: state.notes,
      reduceMotion: state.reduceMotion,
      graphCalmMode: state.graphCalmMode,
      envMode: state.envMode,
    };
    savePersisted(shape);
  };

  useIntelStore.subscribe((state, prev) => {
    // Only persist if a tracked slice changed
    if (
      state.sessions === prev.sessions &&
      state.bookmarkedEntities === prev.bookmarkedEntities &&
      state.pinnedEvidence === prev.pinnedEvidence &&
      state.dismissedNotifications === prev.dismissedNotifications &&
      state.notes === prev.notes &&
      state.reduceMotion === prev.reduceMotion &&
      state.graphCalmMode === prev.graphCalmMode &&
      state.envMode === prev.envMode
    ) {
      return;
    }
    if (pendingSave) cancelAnimationFrame(pendingSave);
    pendingSave = requestAnimationFrame(() => persist(state));
  });

  // One-shot: apply the persisted env mode to the document on boot so the
  // atmosphere matches the analyst's last session before the first paint.
  applyEnvModeAttribute(useIntelStore.getState().envMode);
}

function applyEnvModeAttribute(mode: EnvMode): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-env-mode', mode);
}

function labelForIngested(
  kind: Entity['kind'],
  shortId: string,
  i: number
): string {
  const tag = `${shortId.toUpperCase()}-${i + 1}`;
  switch (kind) {
    case 'account':
      return `ACCT-${tag}`;
    case 'transaction':
      return `TXN ${(1000 + i * 137).toLocaleString()} EUR`;
    case 'device':
      return `dev fp-${tag.toLowerCase()}`;
    case 'address':
      return `Address ${tag}`;
    case 'person':
      return `Person ${tag}`;
    default:
      return `${kind} ${tag}`;
  }
}

export function getEntityById(id: string | null | undefined): Entity | undefined {
  if (!id) return undefined;
  const { active } = useIntelStore.getState();
  return active.graph.entities.find((e) => e.id === id);
}
