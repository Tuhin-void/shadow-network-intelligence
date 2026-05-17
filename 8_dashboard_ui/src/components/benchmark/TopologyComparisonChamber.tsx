import { useMemo } from 'react';

/**
 * TopologyComparisonChamber — three schematic SVGs explaining the
 * architectural difference between the three retrieval paradigms.
 *
 * These are CONCEPTUAL diagrams — they illustrate *what each pipeline
 * returns* for a topology-heavy query. They are explicitly labeled as
 * schematic so they cannot be mistaken for real graph output.
 *
 *   PureLLM   → isolated, unconnected guesses (no retrieval at all)
 *   VectorRAG → small clusters of chunks; no inter-chunk structural edges
 *   GraphRAG  → fully connected topology with ring + flow + ownership
 *
 * Render: deterministic seeded layouts so it always looks the same.
 */
export function TopologyComparisonChamber() {
  const purellm = useMemo(() => generatePureLLM(13, 33), []);
  const vectorrag = useMemo(() => generateVectorRAG(33), []);
  const graphrag = useMemo(() => generateGraphRAG(33), []);

  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          what each pipeline reconstructs
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          schematic illustration
        </span>
        <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          same query · three architectures
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 divide-x divide-y divide-[var(--color-line-soft)]">
        <Panel
          title="PureLLM"
          tone="rose"
          headline="ungrounded guess"
          body="No retrieval. The model emits names from its priors with no edges between them. Hallucinates entity IDs that don't exist."
          render={purellm}
          legend="3-5 disconnected guesses"
        />
        <Panel
          title="VectorRAG"
          tone="amber"
          headline="fragmented chunks"
          body="Top-K chunked documents by semantic similarity. Each chunk is internally coherent but edges between chunks live only in the source graph — never in the text."
          render={vectorrag}
          legend="text-clustered, no inter-chunk edges"
        />
        <Panel
          title="GraphRAG"
          tone="emerald"
          headline="reconstructed topology"
          body="Multi-hop typed-edge traversal. Surfaces the ring, the ownership chain, the shared infrastructure — the structural answer is the join itself."
          render={graphrag}
          legend="ring + ownership + flow continuity"
        />
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function Panel({
  title,
  tone,
  headline,
  body,
  render,
  legend,
}: {
  title: string;
  tone: 'emerald' | 'rose' | 'amber';
  headline: string;
  body: string;
  render: SVGGraph;
  legend: string;
}) {
  const color =
    tone === 'emerald'
      ? 'var(--color-emerald-400)'
      : tone === 'rose'
      ? 'var(--color-rose-400)'
      : 'var(--color-amber-400)';
  return (
    <div className="px-3 py-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span
          className="font-mono text-[10px] tracking-[0.32em] uppercase"
          style={{ color }}
        >
          {title}
        </span>
        <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {legend}
        </span>
      </div>
      <div
        className="aspect-[5/3] w-full rounded-sm border overflow-hidden bg-[rgba(7,9,14,0.45)] relative"
        style={{ borderColor: `${color}33` }}
      >
        <SchematicSVG graph={render} color={color} />
      </div>
      <div>
        <div
          className="font-mono text-[9.5px] tracking-[0.22em] uppercase mb-1"
          style={{ color }}
        >
          ▸ {headline}
        </div>
        <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
          {body}
        </p>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* SVG schematic primitives                                                   */
/* -------------------------------------------------------------------------- */

type Node = { x: number; y: number; r?: number };
type Edge = { a: number; b: number; w?: number; dashed?: boolean };
type SVGGraph = { nodes: Node[]; edges: Edge[] };

function SchematicSVG({ graph, color }: { graph: SVGGraph; color: string }) {
  const W = 100;
  const H = 60;
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-full"
    >
      {graph.edges.map((e, i) => {
        const a = graph.nodes[e.a];
        const b = graph.nodes[e.b];
        if (!a || !b) return null;
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke={color}
            strokeWidth={e.w ?? 0.4}
            strokeOpacity={0.55}
            strokeDasharray={e.dashed ? '1.2,1.2' : undefined}
          />
        );
      })}
      {graph.nodes.map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r={(n.r ?? 1.2) + 0.8} fill={color} opacity={0.18} />
          <circle cx={n.x} cy={n.y} r={n.r ?? 1.2} fill={color} opacity={0.95} />
        </g>
      ))}
    </svg>
  );
}

/* -------------------------------------------------------------------------- */
/* Layout generators — deterministic, seeded                                  */
/* -------------------------------------------------------------------------- */

function rand(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}

/** PureLLM: scattered isolated nodes, no edges. */
function generatePureLLM(count: number, seed: number): SVGGraph {
  const rnd = rand(seed);
  const nodes: Node[] = [];
  for (let i = 0; i < count; i++) {
    nodes.push({
      x: 10 + rnd() * 80,
      y: 8 + rnd() * 44,
      r: 1.2 + rnd() * 0.6,
    });
  }
  return { nodes, edges: [] };
}

/** VectorRAG: 4 small clusters with intra-cluster edges only. */
function generateVectorRAG(seed: number): SVGGraph {
  const rnd = rand(seed);
  const clusters = [
    { cx: 22, cy: 18, n: 4 },
    { cx: 70, cy: 16, n: 4 },
    { cx: 25, cy: 42, n: 5 },
    { cx: 72, cy: 44, n: 4 },
  ];
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  clusters.forEach((c) => {
    const startIdx = nodes.length;
    for (let i = 0; i < c.n; i++) {
      nodes.push({
        x: c.cx + (rnd() - 0.5) * 12,
        y: c.cy + (rnd() - 0.5) * 9,
        r: 1.1 + rnd() * 0.4,
      });
    }
    // Intra-cluster edges only
    for (let i = 0; i < c.n; i++) {
      for (let j = i + 1; j < c.n; j++) {
        if (rnd() > 0.5) {
          edges.push({ a: startIdx + i, b: startIdx + j, w: 0.3 });
        }
      }
    }
  });
  return { nodes, edges };
}

/** GraphRAG: connected topology — central FraudRing hub + 3 Person spokes,
 *  each with Company children (OWNS), Accounts (HAS_ACCOUNT), Transactions
 *  (TRANSFERRED_TO), and a shared Address forming a 3-hop join. */
function generateGraphRAG(seed: number): SVGGraph {
  const rnd = rand(seed);
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // 0: FraudRing centre
  nodes.push({ x: 50, y: 30, r: 2.4 });

  // 1-3: Person ring members
  const persons = [
    { x: 26, y: 18 },
    { x: 26, y: 42 },
    { x: 74, y: 30 },
  ];
  persons.forEach((p) => nodes.push({ ...p, r: 1.8 }));

  // ring-membership edges (Person → FraudRing)
  edges.push({ a: 1, b: 0, w: 0.7 });
  edges.push({ a: 2, b: 0, w: 0.7 });
  edges.push({ a: 3, b: 0, w: 0.7 });

  // Companies owned by each person
  const personCompanyCount = [2, 2, 2];
  persons.forEach((p, idx) => {
    const personIdx = idx + 1;
    for (let c = 0; c < personCompanyCount[idx]; c++) {
      const angle = ((c + 1) / (personCompanyCount[idx] + 1)) * Math.PI - Math.PI / 2;
      const cx = p.x + Math.cos(angle) * 10;
      const cy = p.y + Math.sin(angle) * 8;
      nodes.push({ x: cx, y: cy, r: 1.2 });
      edges.push({ a: personIdx, b: nodes.length - 1, w: 0.4 });
    }
  });

  // A shared address connecting two of the persons (hidden join!)
  nodes.push({ x: 50, y: 52, r: 1.5 });
  const addressIdx = nodes.length - 1;
  edges.push({ a: 1, b: addressIdx, w: 0.45, dashed: true });
  edges.push({ a: 2, b: addressIdx, w: 0.45, dashed: true });

  // A few transaction flow edges between accounts
  const accountIndices: number[] = [];
  for (let i = 0; i < 3; i++) {
    const px = 12 + rnd() * 76;
    const py = 6 + rnd() * 48;
    nodes.push({ x: px, y: py, r: 0.9 });
    accountIndices.push(nodes.length - 1);
  }
  edges.push({ a: accountIndices[0], b: accountIndices[1], w: 0.3 });
  edges.push({ a: accountIndices[1], b: accountIndices[2], w: 0.3 });
  edges.push({ a: accountIndices[0], b: 1, w: 0.3 });
  edges.push({ a: accountIndices[2], b: 3, w: 0.3 });

  return { nodes, edges };
}
