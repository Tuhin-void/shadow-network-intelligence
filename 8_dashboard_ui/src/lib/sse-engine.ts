import type { PresetSnapshot, StreamEvent } from '@/types/intel';

/**
 * Replays a preset's canonical SSE stream with believable pacing.
 * Pacing is varied per-event-kind to feel like real backend topology work.
 */
export interface StreamHandle {
  stop: () => void;
}

const baseDelay: Record<StreamEvent['kind'], number> = {
  'session.start': 360,
  'topology.expanded': 520,
  'entity.discovered': 280,
  'edge.traversed': 220,
  'ring.detected': 760,
  'hidden.relationship': 560,
  'path.discovered': 520,
  'suspicion.escalated': 720,
  'evidence.collected': 540,
  'signal.surfaced': 460,
  'report.section': 620,
  'session.complete': 540,
};

export function playStream(
  preset: PresetSnapshot,
  onEvent: (e: StreamEvent, progress: number) => void,
  opts: { speed?: number; onComplete?: () => void } = {}
): StreamHandle {
  const speed = opts.speed ?? 1;
  const events = preset.stream;
  let cancelled = false;
  let i = 0;

  const tick = () => {
    if (cancelled || i >= events.length) {
      if (!cancelled) opts.onComplete?.();
      return;
    }
    const e = events[i];
    const stamped: StreamEvent = { ...e, at: new Date().toISOString() };
    onEvent(stamped, (i + 1) / events.length);
    i += 1;
    const delay = (baseDelay[e.kind] ?? 400) / speed;
    setTimeout(tick, delay);
  };

  // Slight pre-roll to make the first event feel intentional.
  const handle = setTimeout(tick, 200 / speed);

  return {
    stop: () => {
      cancelled = true;
      clearTimeout(handle);
    },
  };
}
