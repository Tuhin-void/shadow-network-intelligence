import { useEffect, useMemo, useRef, useState } from 'react';
import cytoscape, { type Core, type ElementDefinition, type StylesheetCSS } from 'cytoscape';
import { useIntelStore } from '@/store/intel-store';
import type { Edge, Entity, PresetSnapshot, StreamEventKind } from '@/types/intel';
import { edgeLabel, entityGlyph } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';

/* -------------------------------------------------------------------------- */
/* Element builders                                                           */
/* -------------------------------------------------------------------------- */

function tierFill(risk: number): string {
  if (risk >= 80) return '#f43f5e';
  if (risk >= 60) return '#f59e0b';
  if (risk >= 35) return '#22d3ee';
  return '#10b981';
}
function tierStroke(risk: number): string {
  if (risk >= 80) return '#fb7185';
  if (risk >= 60) return '#fbbf24';
  if (risk >= 35) return '#67e8f9';
  return '#34d399';
}
function tierGlow(risk: number): string {
  if (risk >= 80) return 'rgba(244,63,94,0.55)';
  if (risk >= 60) return 'rgba(245,158,11,0.5)';
  if (risk >= 35) return 'rgba(34,211,238,0.5)';
  return 'rgba(16,185,129,0.45)';
}

function edgeClasses(edge: Edge): string {
  const cls: string[] = [];
  if (edge.hidden) cls.push('hidden-link');
  // semantic flow classes — money / ownership / shared infra
  if (edge.kind === 'transfers' || edge.kind === 'wires_to') cls.push('flow-money');
  if (edge.kind === 'owns' || edge.kind === 'controls') cls.push('flow-ownership');
  if (
    edge.kind === 'shares_device' ||
    edge.kind === 'shares_address' ||
    edge.kind === 'shares_phone'
  )
    cls.push('flow-infra');
  return cls.join(' ');
}

function buildElements(preset: PresetSnapshot): ElementDefinition[] {
  const elements: ElementDefinition[] = [];
  preset.graph.entities.forEach((e: Entity) => {
    elements.push({
      group: 'nodes',
      data: {
        id: e.id,
        label: e.label,
        kind: e.kind,
        risk: e.risk,
        tier: e.tier,
        glyph: entityGlyph(e.kind),
        importance: e.importance,
      },
    });
  });
  preset.graph.edges.forEach((edge: Edge) => {
    elements.push({
      group: 'edges',
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        kind: edge.kind,
        confidence: edge.confidence,
        weight: edge.weight,
        hidden: edge.hidden ?? false,
        label: edgeLabel(edge.kind),
        _kindShort: edgeLabel(edge.kind).toLowerCase().replace('_', ' '),
      },
      classes: edgeClasses(edge),
    });
  });
  return elements;
}

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

function styles(): StylesheetCSS[] {
  return [
    {
      selector: 'node',
      css: {
        'background-color': 'data(_fill)',
        'background-opacity': 0.95,
        'border-width': 1,
        'border-color': 'data(_stroke)',
        'border-opacity': 0.7,
        width: 'data(_size)',
        height: 'data(_size)',
        label: 'data(label)',
        color: '#e2e8f0',
        'font-family': 'Inter, sans-serif',
        'font-size': 9.5,
        'font-weight': 500,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 6,
        'text-outline-color': '#000003',
        'text-outline-width': 3,
        'text-outline-opacity': 1,
        // soft inner halo via overlay
        'overlay-color': 'data(_glow)',
        'overlay-opacity': 0.12,
        'overlay-padding': 5,
      },
    },
    {
      selector: 'node.faded',
      css: { opacity: 0.12, 'text-opacity': 0.2 },
    },
    {
      selector: 'node.highlight',
      css: {
        'border-width': 2,
        'border-color': '#22d3ee',
        'overlay-color': '#22d3ee',
        'overlay-opacity': 0.18,
        'overlay-padding': 8,
      },
    },
    {
      selector: 'node.selected-anchor',
      css: {
        'border-width': 3,
        'border-color': '#67e8f9',
        'overlay-color': '#22d3ee',
        'overlay-opacity': 0.28,
        'overlay-padding': 12,
      },
    },
    {
      selector: 'node.ring',
      css: {
        'border-color': '#fb7185',
        'border-width': 2,
        'overlay-color': '#f43f5e',
        'overlay-opacity': 0.16,
        'overlay-padding': 10,
      },
    },
    {
      selector: 'node.hidden-endpoint',
      css: {
        'border-color': '#c084fc',
        'border-width': 2,
        'overlay-color': '#a855f7',
        'overlay-opacity': 0.22,
        'overlay-padding': 12,
      },
    },
    {
      selector: 'node.pulse',
      css: {
        'overlay-color': '#22d3ee',
        'overlay-opacity': 0.55,
        'overlay-padding': 24,
      },
    },
    {
      selector: 'node.critical-anom',
      css: {
        'overlay-color': '#f43f5e',
        'overlay-opacity': 0.34,
        'overlay-padding': 18,
        'border-color': '#fb7185',
        'border-width': 2,
      },
    },
    {
      selector: 'edge',
      css: {
        width: 'data(_w)',
        'line-color': '#1f2530',
        'target-arrow-color': '#3a4555',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.8,
        'curve-style': 'bezier',
        opacity: 0.40,
        // labels hidden by default — surface only on focus / selection
        label: '',
        'font-size': 7.5,
        'font-family': 'JetBrains Mono, monospace',
        color: '#64748b',
        'text-background-color': '#000003',
        'text-background-opacity': 0.85,
        'text-background-padding': '2',
        'text-rotation': 'autorotate',
      },
    },
    /* Flow semantics: money — solid + slightly warmer; ownership — colder + stronger;
       shared infra — fainter, neutral. */
    {
      selector: 'edge.flow-money',
      css: {
        'line-color': '#3b4252',
        'target-arrow-color': '#94a3b8',
      },
    },
    {
      selector: 'edge.flow-ownership',
      css: {
        'line-color': '#2a3450',
        'target-arrow-color': '#67e8f9',
        'arrow-scale': 1.0,
      },
    },
    {
      selector: 'edge.flow-infra',
      css: {
        'line-color': '#1a2026',
        'target-arrow-color': '#475569',
        'line-style': 'dotted',
        opacity: 0.32,
      },
    },
    {
      selector: 'edge.hidden-link',
      css: {
        'line-color': '#a855f7',
        'line-style': 'dashed',
        'target-arrow-color': '#a855f7',
        opacity: 0.88,
        color: '#c084fc',
        width: 1.4,
      },
    },
    {
      selector: 'edge.traversed',
      css: {
        'line-color': '#22d3ee',
        'target-arrow-color': '#22d3ee',
        opacity: 0.95,
        width: 2.5,
      },
    },
    {
      selector: 'edge.path',
      css: {
        'line-color': '#fbbf24',
        'target-arrow-color': '#fbbf24',
        opacity: 0.95,
        width: 2.4,
        // surface label on path edges so analyst sees the chain
        label: 'data(_kindShort)',
      },
    },
    {
      selector: 'edge.path-hot',
      css: {
        'line-color': '#fcd34d',
        'target-arrow-color': '#fcd34d',
        opacity: 1,
        width: 3,
        label: 'data(_kindShort)',
        'font-size': 8,
      },
    },
    {
      selector: 'edge.flow-money.path, edge.flow-money.path-hot',
      css: {
        // dashed line — money flow direction
        'line-style': 'dashed',
        'line-dash-pattern': [6, 4],
      },
    },
    /* Selection / hover — reveal the edge kind label */
    {
      selector: 'edge.edge-focus',
      css: {
        label: 'data(_kindShort)',
        opacity: 1,
        'line-color': '#67e8f9',
        'target-arrow-color': '#67e8f9',
        width: 2,
      },
    },
    {
      selector: 'edge.faded',
      css: { opacity: 0.05 },
    },
  ];
}

/* -------------------------------------------------------------------------- */
/* Live shockwave layer — HTML rings layered over the cytoscape canvas        */
/* -------------------------------------------------------------------------- */

type Shockwave = {
  id: string;
  x: number;       // % within container
  y: number;       // % within container
  tone: 'ice' | 'rose' | 'violet' | 'amber';
};

const dramaticKinds = new Set<StreamEventKind>([
  'ring.detected',
  'hidden.relationship',
  'suspicion.escalated',
  'path.discovered',
  'session.complete',
]);

function toneFor(kind: StreamEventKind): Shockwave['tone'] {
  if (kind === 'ring.detected' || kind === 'suspicion.escalated') return 'rose';
  if (kind === 'hidden.relationship') return 'violet';
  if (kind === 'path.discovered') return 'amber';
  return 'ice';
}

/* -------------------------------------------------------------------------- */
/* Canvas                                                                     */
/* -------------------------------------------------------------------------- */

interface GraphCanvasProps {
  /** Cinematic mode: stronger breathing, larger pulses, narration-aware camera */
  cinematic?: boolean;
  /** Restrict graph to a neighborhood subset of entity ids. Empty/undefined = full preset. */
  neighborhood?: Set<string>;
}

export function GraphCanvas({
  cinematic = false,
  neighborhood,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const breatheRef = useRef<number>(0);

  const fullActive = useIntelStore((s) => s.active);
  const reduceMotion = useIntelStore((s) => s.reduceMotion);
  const graphCalmMode = useIntelStore((s) => s.graphCalmMode);

  // Reveal pulse: when a new investigation snapshot lands (i.e. fullActive.id
  // changes), emit a one-shot CSS pulse on the wrapper for ~1.4s.
  // Causally bound to real backend completion (activateLiveSnapshot fires on
  // report.finalized). Calm mode suppresses motion via the existing
  // data-env-mode CSS.
  const [revealPulse, setRevealPulse] = useState(false);
  const lastActiveIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (lastActiveIdRef.current === null) {
      lastActiveIdRef.current = fullActive.id;
      return;
    }
    if (lastActiveIdRef.current !== fullActive.id) {
      lastActiveIdRef.current = fullActive.id;
      if (reduceMotion) return;
      setRevealPulse(true);
      const t = setTimeout(() => setRevealPulse(false), 1500);
      return () => clearTimeout(t);
    }
  }, [fullActive.id, reduceMotion]);
  // Subgraph projection: if neighborhood passed, restrict to those entities + their interconnecting edges.
  const active = useMemo<PresetSnapshot>(() => {
    if (!neighborhood || neighborhood.size === 0) return fullActive;
    const keep = neighborhood;
    return {
      ...fullActive,
      graph: {
        entities: fullActive.graph.entities.filter((e) => keep.has(e.id)),
        edges: fullActive.graph.edges.filter(
          (e) => keep.has(e.source) && keep.has(e.target)
        ),
      },
    };
  }, [fullActive, neighborhood]);
  // (re-export to keep the rest of the file unchanged)
  void fullActive;
  const focusMode = useIntelStore((s) => s.focusMode);
  const selectedEntityId = useIntelStore((s) => s.selectedEntityId);
  const discoveredEntities = useIntelStore((s) => s.discoveredEntities);
  const surfacedPaths = useIntelStore((s) => s.surfacedPaths);
  const surfacedRings = useIntelStore((s) => s.surfacedRings);
  const streamingPhase = useIntelStore((s) => s.streamingPhase);
  const events = useIntelStore((s) => s.events);
  const selectEntity = useIntelStore((s) => s.selectEntity);

  const [shocks, setShocks] = useState<Shockwave[]>([]);
  const [hover, setHover] = useState<{
    id: string;
    label: string;
    kind: string;
    risk: number;
    tier: string;
    degree: number;
    x: number;
    y: number;
  } | null>(null);

  const elements = useMemo(() => buildElements(active), [active]);

  // Init / rebuild cy when preset changes
  useEffect(() => {
    if (!containerRef.current) return;
    if (cyRef.current) {
      try {
        cyRef.current.stop(true, true);
        cyRef.current.destroy();
      } catch {
        /* layout frame may throw post-destroy */
      }
      cyRef.current = null;
    }

    const enriched: ElementDefinition[] = elements.map((el) => {
      if (el.group === 'nodes') {
        const risk = el.data?.risk as number;
        const importance = el.data?.importance as number;
        return {
          ...el,
          data: {
            ...el.data,
            _fill: tierFill(risk),
            _stroke: tierStroke(risk),
            _glow: tierGlow(risk),
            _size: 14 + importance * 3.4,
          },
        };
      }
      return {
        ...el,
        data: {
          ...el.data,
          _w: Math.max(0.7, ((el.data?.weight as number) ?? 3) * 0.42),
        },
      };
    });

    const cy = cytoscape({
      container: containerRef.current,
      elements: enriched,
      minZoom: 0.3,
      maxZoom: 2.5,
      style: styles(),
      layout: {
        name: 'cose',
        padding: 80,
        animate: false,
        nodeRepulsion: () => 7800,
        idealEdgeLength: () => 122,
        edgeElasticity: () => 110,
        gravity: 0.35,
        randomize: false,
        fit: true,
      } as cytoscape.LayoutOptions,
    });

    cy.on('tap', 'node', (evt) => selectEntity(evt.target.id()));
    cy.on('tap', (evt) => {
      if (evt.target === cy) selectEntity(null);
    });

    // Hover tooltip — show entity preview without committing to a click
    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const id = node.id();
      const data = node.data();
      const bb = node.renderedBoundingBox();
      const containerRect = containerRef.current?.getBoundingClientRect();
      if (!containerRect) return;
      const degree = node.connectedEdges().length;
      setHover({
        id,
        label: data.label as string,
        kind: data.kind as string,
        risk: data.risk as number,
        tier: data.tier as string,
        degree,
        x: (bb.x1 + bb.x2) / 2,
        y: bb.y1 - 8,
      });
    });
    cy.on('mouseout', 'node', () => setHover(null));
    // also clear when zooming/panning so tooltip doesn't lag behind
    cy.on('pan zoom', () => setHover(null));

    cyRef.current = cy;

    const ro = new ResizeObserver(() => {
      if (!cyRef.current || !containerRef.current) return;
      cyRef.current.resize();
      cyRef.current.fit(undefined, 80);
    });
    ro.observe(containerRef.current);

    const raf = requestAnimationFrame(() => {
      cy.resize();
      cy.fit(undefined, 80);
    });

    // Living-organism breathing — gently modulate overlay opacity over time.
    // Always-on by default (very low amplitude, ≈±1.5%) so every graph feels
    // alive without competing for attention. Cinematic mode lifts amplitude
    // and shifts to a slightly faster rhythm. Suppressed only when the
    // analyst has explicitly chosen reduced motion or calm graph mode.
    let lastApply = 0;
    const breathe = (t: number) => {
      if (!cyRef.current) {
        breatheRef.current = 0;
        return;
      }
      // Throttle stylesheet updates to ~12 fps — the eye can't perceive
      // overlay-opacity modulation faster than that, and cytoscape's
      // style().update() is heavy.
      if (t - lastApply > 80) {
        lastApply = t;
        const s = t / 1000;
        const amp = cinematic ? 0.04 : 0.012;
        const base = cinematic ? 0.10 : 0.12;
        const freq = cinematic ? 0.9 : 0.55;
        const value = base + amp * (0.5 + 0.5 * Math.sin(s * freq));
        try {
          cyRef.current
            .style()
            .selector('node')
            .style('overlay-opacity', value)
            .update();
        } catch {
          /* destroyed mid-frame */
        }
      }
      breatheRef.current = requestAnimationFrame(breathe);
    };
    if (!reduceMotion && !graphCalmMode) {
      breatheRef.current = requestAnimationFrame(breathe);
    }

    return () => {
      cancelAnimationFrame(raf);
      if (breatheRef.current) cancelAnimationFrame(breatheRef.current);
      ro.disconnect();
      try {
        cy.stop(true, true);
        cy.destroy();
      } catch {
        /* stale frame */
      }
      cyRef.current = null;
    };
  }, [elements, selectEntity, cinematic, reduceMotion, graphCalmMode]);

  // Apply focus / discovery / selection state via class diff
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      cy.elements().removeClass(
        'faded highlight selected-anchor ring hidden-endpoint traversed path path-hot pulse critical-anom edge-focus'
      );

      const ringMembers = new Set<string>();
      active.rings.forEach((r) => {
        if (focusMode === 'rings' || surfacedRings.has(r.id)) {
          r.members.forEach((m) => ringMembers.add(m));
        }
      });

      const hiddenIds = new Set<string>();
      active.graph.edges
        .filter((e) => e.hidden)
        .forEach((e) => {
          hiddenIds.add(e.source);
          hiddenIds.add(e.target);
        });

      const pathNodeIds = new Set<string>();
      const pathEdgeIds = new Set<string>();
      active.paths.forEach((p) => {
        if (focusMode === 'paths' || surfacedPaths.has(p.id)) {
          p.nodes.forEach((n) => pathNodeIds.add(n));
          for (let i = 0; i < p.nodes.length - 1; i += 1) {
            const a = p.nodes[i];
            const b = p.nodes[i + 1];
            const eAB = cy.edges(
              `[source = "${a}"][target = "${b}"], [source = "${b}"][target = "${a}"]`
            );
            eAB.forEach((edge) => {
              pathEdgeIds.add(edge.id());
            });
          }
        }
      });

      cy.nodes().forEach((n) => {
        const id = n.id();
        if (focusMode === 'rings' && !ringMembers.has(id)) n.addClass('faded');
        if (focusMode === 'hidden' && !hiddenIds.has(id)) n.addClass('faded');
        if (focusMode === 'paths' && !pathNodeIds.has(id)) n.addClass('faded');
        if (focusMode === 'risk' && (n.data('risk') as number) < 60) n.addClass('faded');
        if (
          focusMode === 'overview' &&
          streamingPhase === 'streaming' &&
          !discoveredEntities.has(id) &&
          discoveredEntities.size < active.graph.entities.length * 0.85
        ) {
          n.addClass('faded');
        }

        if (ringMembers.has(id)) n.addClass('ring');
        if (hiddenIds.has(id)) n.addClass('hidden-endpoint');
        if (pathNodeIds.has(id)) n.addClass('highlight');

        // Critical anomaly halo: critical-tier nodes during streaming feel infectious
        if (
          cinematic &&
          (n.data('risk') as number) >= 80 &&
          (streamingPhase === 'streaming' || streamingPhase === 'complete')
        ) {
          n.addClass('critical-anom');
        }

        if (id === selectedEntityId) {
          n.addClass('selected-anchor');
          // Surface incident edge labels so the analyst sees relationship kinds
          n.connectedEdges().forEach((edge) => {
            edge.addClass('edge-focus');
          });
        }
      });

      cy.edges().forEach((e) => {
        const id = e.id();
        const src = e.source().id();
        const tgt = e.target().id();
        if (
          (focusMode === 'rings' && !(ringMembers.has(src) && ringMembers.has(tgt))) ||
          (focusMode === 'hidden' && !(hiddenIds.has(src) && hiddenIds.has(tgt))) ||
          (focusMode === 'paths' && !pathEdgeIds.has(id))
        ) {
          e.addClass('faded');
        }
        if (pathEdgeIds.has(id)) e.addClass(cinematic ? 'path-hot' : 'path');
      });
    });
  }, [
    active,
    focusMode,
    selectedEntityId,
    discoveredEntities,
    surfacedPaths,
    surfacedRings,
    streamingPhase,
    cinematic,
  ]);

  // Pulse on last event + emit a Shockwave for dramatic kinds.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || events.length === 0) return;
    const last = events[events.length - 1];
    const refs = last.refs ?? [];

    refs.forEach((id) => {
      const node = cy.getElementById(id);
      if (node.length === 0) return;
      node.addClass('pulse');
      setTimeout(() => node.removeClass('pulse'), 900);
    });

    // Cinematic shockwave on dramatic events — suppressed under reduce-motion
    if (
      cinematic &&
      !reduceMotion &&
      !graphCalmMode &&
      dramaticKinds.has(last.kind) &&
      containerRef.current
    ) {
      const rect = containerRef.current.getBoundingClientRect();
      const tone = toneFor(last.kind);
      const positions: { x: number; y: number }[] = [];

      refs.forEach((id) => {
        const node = cy.getElementById(id);
        if (node.length === 0) return;
        const bb = node.renderedBoundingBox();
        positions.push({
          x: ((bb.x1 + bb.x2) / 2 / rect.width) * 100,
          y: ((bb.y1 + bb.y2) / 2 / rect.height) * 100,
        });
      });
      // If no node refs (e.g. path with only path-id), center it.
      if (positions.length === 0) positions.push({ x: 50, y: 50 });

      const newShocks: Shockwave[] = positions.slice(0, 4).map((p, i) => ({
        id: `${last.id}_${i}`,
        x: p.x,
        y: p.y,
        tone,
      }));
      setShocks((prev) => [...prev.slice(-8), ...newShocks]);
      // Clean up after animation
      newShocks.forEach((s) =>
        setTimeout(() => setShocks((prev) => prev.filter((x) => x.id !== s.id)), 1500)
      );
    }
  }, [events, cinematic]);

  // Cinematic camera: gently center on the selected entity / last-event ref.
  // Suppressed under reduceMotion to avoid disorientation during long sessions.
  useEffect(() => {
    if (!cinematic || reduceMotion) return;
    const cy = cyRef.current;
    if (!cy) return;
    const targetId =
      events[events.length - 1]?.refs?.[0] ?? selectedEntityId ?? active.seed;
    const node = cy.getElementById(targetId);
    if (node.length === 0) return;
    cy.stop();
    cy.animate(
      {
        center: { eles: node },
        zoom: Math.max(cy.zoom(), 0.8),
      },
      { duration: 700, easing: 'ease-in-out-cubic' }
    );
  }, [events, cinematic, selectedEntityId, active.seed]);

  return (
    <div className={`fill overflow-hidden${revealPulse ? ' anim-graph-reveal' : ''}`}>
      <div className="fill tactical-grid-fine opacity-40" />
      <div
        ref={containerRef}
        className="fill"
        style={{
          background:
            'radial-gradient(800px 600px at 50% 50%, rgba(34,211,238,0.03), transparent 70%)',
        }}
      />
      <div className="fill tactical-vignette pointer-events-none" />

      {/* Hover tooltip — non-interactive entity preview */}
      {hover && (
        <div
          className="absolute pointer-events-none z-30 surface-floating px-2.5 py-1.5 min-w-[180px]"
          style={{
            left: hover.x,
            top: hover.y,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-[9px] tracking-[0.22em] uppercase"
              style={{
                color:
                  hover.tier === 'critical'
                    ? 'var(--color-rose-400)'
                    : hover.tier === 'high'
                    ? 'var(--color-amber-400)'
                    : hover.tier === 'medium'
                    ? 'var(--color-ice-400)'
                    : 'var(--color-emerald-400)',
              }}
            >
              {hover.tier}
            </span>
            <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
              {hover.kind.replace('_', ' ')}
            </span>
            <span className="ml-auto font-mono text-[10px] text-[var(--color-text-bright)]">
              {hover.risk}
            </span>
          </div>
          <div className="text-[11.5px] text-[var(--color-text-bright)] mt-0.5 truncate">
            {hover.label}
          </div>
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mt-0.5">
            {hover.id} · degree {hover.degree}
          </div>
        </div>
      )}

      {/* Shockwave layer */}
      <div className="fill pointer-events-none">
        <AnimatePresence>
          {shocks.map((s) => (
            <motion.div
              key={s.id}
              initial={{ scale: 0, opacity: 0.85 }}
              animate={{ scale: 18, opacity: 0 }}
              transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
              className="absolute rounded-full"
              style={{
                top: `${s.y}%`,
                left: `${s.x}%`,
                width: 16,
                height: 16,
                transform: 'translate(-50%, -50%)',
                border: `1.5px solid ${
                  s.tone === 'rose'
                    ? '#fb7185'
                    : s.tone === 'violet'
                    ? '#c084fc'
                    : s.tone === 'amber'
                    ? '#fbbf24'
                    : '#67e8f9'
                }`,
                boxShadow: `0 0 20px -2px ${
                  s.tone === 'rose'
                    ? 'rgba(244,63,94,0.55)'
                    : s.tone === 'violet'
                    ? 'rgba(168,85,247,0.55)'
                    : s.tone === 'amber'
                    ? 'rgba(245,158,11,0.5)'
                    : 'rgba(34,211,238,0.5)'
                }`,
              }}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
