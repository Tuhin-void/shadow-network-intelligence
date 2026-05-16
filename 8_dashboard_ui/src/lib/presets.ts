import type {
  BenchmarkComparison,
  Edge,
  EdgeKind,
  Entity,
  EntityKind,
  EvidenceItem,
  HiddenRelationship,
  IntelReport,
  PresetSnapshot,
  Ring,
  RiskTier,
  StreamEvent,
  StreamEventKind,
  StructuralSignal,
  TraversalPath,
} from '@/types/intel';
import { riskToTier } from './utils';

/* -------------------------------------------------------------------------- */
/* Construction helpers                                                       */
/* -------------------------------------------------------------------------- */

let _seq = 0;
const nextSeq = () => ++_seq;

const ent = (
  id: string,
  label: string,
  kind: EntityKind,
  risk: number,
  importance = 5,
  extras: Partial<Entity> = {}
): Entity => ({
  id,
  label,
  kind,
  risk,
  tier: riskToTier(risk),
  importance,
  ...extras,
});

const edg = (
  source: string,
  target: string,
  kind: EdgeKind,
  weight = 3,
  confidence = 0.85,
  hidden = false,
  meta: Record<string, string | number | boolean> = {}
): Edge => ({
  id: `e_${source}_${target}_${kind}_${Math.random().toString(36).slice(2, 7)}`,
  source,
  target,
  kind,
  weight,
  confidence,
  hidden,
  meta,
});

const evt = (
  kind: StreamEventKind,
  title: string,
  opts: Partial<StreamEvent> = {}
): StreamEvent => ({
  id: `ev_${Math.random().toString(36).slice(2, 9)}`,
  kind,
  seq: nextSeq(),
  at: new Date(Date.now() + nextSeq() * 250).toISOString(),
  title,
  ...opts,
});

const evi = (
  claim: string,
  basis: EvidenceItem['basis'],
  refs: string[],
  confidence = 0.9
): EvidenceItem => ({
  id: `evi_${Math.random().toString(36).slice(2, 9)}`,
  claim,
  basis,
  refs,
  confidence,
  timestamp: new Date().toISOString(),
});

/* -------------------------------------------------------------------------- */
/* PRESET 1 — Shell Cascade                                                   */
/* -------------------------------------------------------------------------- */

function presetShellCascade(): PresetSnapshot {
  const entities: Entity[] = [
    ent('p_alaric', 'A. Voss', 'person', 92, 9, { flags: ['UBO', 'sanctioned-adjacent'] }),
    ent('p_lina', 'L. Marek', 'person', 71, 6, { flags: ['nominee-director'] }),
    ent('p_owen', 'O. Hess', 'person', 55, 5),
    ent('p_renata', 'R. Cole', 'person', 38, 4),
    ent('sc_obsidian', 'Obsidian Holdings BVI', 'shell_company', 86, 8),
    ent('sc_helix', 'Helix Trust GP', 'shell_company', 78, 7),
    ent('sc_kappa', 'Kappa Mgmt SRL', 'shell_company', 74, 6),
    ent('sc_orchid', 'Orchid Ltd KY', 'shell_company', 81, 7),
    ent('co_meridian', 'Meridian Logistics', 'company', 42, 5),
    ent('co_arclight', 'Arclight Trading', 'company', 67, 6),
    ent('acc_zr1', 'ZR-• 4781', 'account', 88, 7),
    ent('acc_zr2', 'ZR-• 8810', 'account', 79, 6),
    ent('acc_eu1', 'EU-• 3320', 'account', 64, 5),
    ent('acc_us1', 'US-• 2261', 'account', 58, 5),
    ent('addr_nicosia', '17 Demetriou, Nicosia', 'address', 60, 4),
    ent('addr_vaduz', '2 Aulestrasse, Vaduz', 'address', 62, 4),
    ent('dev_legalpad', 'iPad-LEGAL-04', 'device', 70, 4),
    ent('tx_w1', 'WIRE 2.4M EUR', 'transaction', 84, 6),
    ent('tx_w2', 'WIRE 1.1M USD', 'transaction', 76, 5),
    ent('tx_w3', 'WIRE 880K CHF', 'transaction', 72, 5),
    ent('tx_w4', 'WIRE 420K USD', 'transaction', 65, 4),
    ent('doc_trust', 'Trust Deed v3', 'document', 50, 3),
  ];

  const edges: Edge[] = [
    edg('p_alaric', 'sc_obsidian', 'controls', 9, 0.92),
    edg('sc_obsidian', 'sc_helix', 'owns', 8, 0.88),
    edg('sc_helix', 'sc_kappa', 'owns', 7, 0.84),
    edg('sc_kappa', 'sc_orchid', 'owns', 6, 0.78),
    edg('sc_orchid', 'co_arclight', 'owns', 8, 0.9),
    edg('p_lina', 'sc_helix', 'authorizes', 5, 0.81),
    edg('p_lina', 'sc_kappa', 'authorizes', 5, 0.81),
    edg('p_owen', 'co_meridian', 'controls', 6, 0.74),
    edg('p_renata', 'co_meridian', 'employs', 4, 0.72),
    edg('co_meridian', 'co_arclight', 'wires_to', 6, 0.86, false, { count: 14 }),
    edg('co_arclight', 'acc_zr1', 'owns', 7, 0.9),
    edg('co_arclight', 'acc_zr2', 'owns', 7, 0.9),
    edg('co_meridian', 'acc_eu1', 'owns', 6, 0.88),
    edg('co_meridian', 'acc_us1', 'owns', 6, 0.88),
    edg('acc_eu1', 'acc_zr1', 'transfers', 8, 0.92),
    edg('acc_us1', 'acc_zr2', 'transfers', 7, 0.9),
    edg('acc_zr1', 'tx_w1', 'transfers', 9, 0.94),
    edg('acc_zr2', 'tx_w2', 'transfers', 8, 0.92),
    edg('tx_w1', 'tx_w3', 'transfers', 7, 0.88),
    edg('tx_w3', 'tx_w4', 'transfers', 6, 0.84),
    edg('sc_obsidian', 'addr_nicosia', 'shares_address', 4, 0.66),
    edg('sc_helix', 'addr_nicosia', 'shares_address', 4, 0.66),
    edg('sc_kappa', 'addr_vaduz', 'shares_address', 4, 0.62),
    edg('sc_orchid', 'addr_vaduz', 'shares_address', 4, 0.62),
    edg('p_lina', 'dev_legalpad', 'authorizes', 4, 0.7),
    edg('p_alaric', 'dev_legalpad', 'shares_device', 5, 0.76, true, { discovered: 'topology' }),
    edg('p_alaric', 'co_arclight', 'hidden_link', 6, 0.71, true, {
      via: 'ownership chain → shared device',
    }),
    edg('p_alaric', 'p_owen', 'hidden_link', 5, 0.68, true, { via: 'co_arclight ↔ co_meridian' }),
    edg('sc_obsidian', 'doc_trust', 'authorizes', 3, 0.6),
    edg('doc_trust', 'p_lina', 'kyc_match', 3, 0.58),
  ];

  const rings: Ring[] = [
    {
      id: 'ring_shell_chain',
      name: 'Obsidian → Helix → Kappa → Orchid cascade',
      members: ['sc_obsidian', 'sc_helix', 'sc_kappa', 'sc_orchid', 'co_arclight'],
      cohesion: 0.86,
      signal: 'ownership_layering',
      risk: 'critical',
    },
  ];

  const hidden: HiddenRelationship[] = [
    {
      id: 'h_alaric_arclight',
      from: 'p_alaric',
      to: 'co_arclight',
      via: ['sc_obsidian', 'sc_helix', 'sc_kappa', 'sc_orchid'],
      reason: '4-hop ownership chain crossing three jurisdictions',
      confidence: 0.91,
    },
    {
      id: 'h_alaric_owen',
      from: 'p_alaric',
      to: 'p_owen',
      via: ['co_arclight', 'co_meridian'],
      reason: 'Wire pattern (14 transfers) between counterparties under common UBO',
      confidence: 0.74,
    },
    {
      id: 'h_lina_alaric_device',
      from: 'p_lina',
      to: 'p_alaric',
      via: ['dev_legalpad'],
      reason: 'Director nominee and UBO share session device — fingerprint match',
      confidence: 0.82,
    },
  ];

  const paths: TraversalPath[] = [
    {
      id: 'tp_ubo',
      label: 'UBO concealment cascade',
      nodes: ['p_alaric', 'sc_obsidian', 'sc_helix', 'sc_kappa', 'sc_orchid', 'co_arclight'],
      edges: [],
      hops: 5,
      why: 'Shortest path from natural person to operating company across 4 corporate veils.',
      intent: 'shortest_path',
    },
    {
      id: 'tp_flow',
      label: 'Funds flow Nicosia → Zürich',
      nodes: ['co_meridian', 'acc_eu1', 'acc_zr1', 'tx_w1', 'tx_w3', 'tx_w4'],
      edges: [],
      hops: 5,
      why: 'Layered wire chain depositing into nested trust accounts',
      intent: 'evidence_chain',
    },
    {
      id: 'tp_reverse',
      label: 'Reverse-edge from beneficiary',
      nodes: ['tx_w4', 'tx_w3', 'tx_w1', 'acc_zr1', 'co_arclight', 'sc_orchid'],
      edges: [],
      hops: 5,
      why: 'Reverse traversal from final beneficiary reveals identical chain',
      intent: 'reverse_edge',
    },
  ];

  const signals: StructuralSignal[] = [
    {
      id: 'sig_layer_depth',
      name: 'Ownership layering depth',
      description: 'Five corporate hops between UBO and operations',
      intensity: 0.92,
      contributors: ['sc_obsidian', 'sc_helix', 'sc_kappa', 'sc_orchid'],
    },
    {
      id: 'sig_addr_reuse',
      name: 'Registered address reuse',
      description: 'Two distinct shells share Nicosia & Vaduz registered addresses',
      intensity: 0.78,
      contributors: ['addr_nicosia', 'addr_vaduz', 'sc_obsidian', 'sc_helix', 'sc_kappa', 'sc_orchid'],
    },
    {
      id: 'sig_dev_overlap',
      name: 'Device fingerprint overlap',
      description: 'Nominee director and UBO authenticate from the same tablet',
      intensity: 0.86,
      contributors: ['dev_legalpad', 'p_alaric', 'p_lina'],
    },
  ];

  const stream: StreamEvent[] = [
    evt('session.start', 'Topology bootstrap • seed p_alaric', { refs: ['p_alaric'] }),
    evt('topology.expanded', 'Hop 1 — 3 entities discovered', { refs: ['sc_obsidian'] }),
    evt('entity.discovered', 'Obsidian Holdings BVI', {
      refs: ['sc_obsidian'],
      severity: 'critical',
      section: 'suspects',
    }),
    evt('edge.traversed', 'controls → Obsidian Holdings BVI', { refs: ['p_alaric', 'sc_obsidian'] }),
    evt('topology.expanded', 'Hop 2 — corporate layer surfaced', {
      refs: ['sc_helix', 'sc_kappa'],
    }),
    evt('entity.discovered', 'Helix Trust GP / Kappa Mgmt SRL', {
      refs: ['sc_helix', 'sc_kappa'],
      severity: 'high',
    }),
    evt('topology.expanded', 'Hop 3 — Orchid + Arclight surfaced', {
      refs: ['sc_orchid', 'co_arclight'],
    }),
    evt('ring.detected', '4-layer ownership cascade — cohesion 0.86', {
      refs: ['ring_shell_chain'],
      severity: 'critical',
      section: 'rings',
    }),
    evt('path.discovered', 'Shortest path UBO → operating company (5 hops)', {
      refs: ['tp_ubo'],
      section: 'ownershipFlow',
    }),
    evt('suspicion.escalated', 'p_alaric escalated → CRITICAL', {
      refs: ['p_alaric'],
      severity: 'critical',
    }),
    evt('hidden.relationship', 'Hidden link surfaced: p_alaric → co_arclight', {
      refs: ['h_alaric_arclight'],
      section: 'hiddenRelationships',
      severity: 'critical',
    }),
    evt('signal.surfaced', 'Address reuse signal — Nicosia & Vaduz', {
      refs: ['sig_addr_reuse'],
      section: 'structuralSignals',
    }),
    evt('edge.traversed', 'Wire chain Nicosia → Zürich identified', { refs: ['tp_flow'] }),
    evt('hidden.relationship', 'p_alaric ↔ p_lina via shared device', {
      refs: ['h_lina_alaric_device'],
      severity: 'high',
      section: 'hiddenRelationships',
    }),
    evt('evidence.collected', '7 structural evidence items chained', {
      refs: ['tp_ubo', 'tp_flow', 'ring_shell_chain'],
      section: 'evidence',
    }),
    evt('report.section', 'Narrative composed — 9 sections complete', {
      section: 'narrative',
    }),
    evt('session.complete', 'Investigation complete • 22 entities • 30 edges'),
  ];

  const report: IntelReport = {
    suspects: entities.filter((e) => e.risk >= 60 && e.kind === 'person'),
    hiddenRelationships: hidden,
    rings,
    ownershipFlow: paths.filter((p) => p.intent === 'shortest_path'),
    transactionFlows: paths.filter((p) => p.intent === 'evidence_chain'),
    sharedInfrastructure: [
      {
        id: 'si_addr_nicosia',
        from: 'sc_obsidian',
        to: 'sc_helix',
        via: ['addr_nicosia'],
        reason: 'Two shells co-registered at the same nominee address',
        confidence: 0.79,
      },
      {
        id: 'si_addr_vaduz',
        from: 'sc_kappa',
        to: 'sc_orchid',
        via: ['addr_vaduz'],
        reason: 'Vaduz address reused across the lower cascade',
        confidence: 0.76,
      },
      {
        id: 'si_dev',
        from: 'p_alaric',
        to: 'p_lina',
        via: ['dev_legalpad'],
        reason: 'Shared authentication device fingerprint',
        confidence: 0.82,
      },
    ],
    traversalPaths: paths,
    structuralSignals: signals,
    evidence: [
      evi('UBO controls operating company through 4 corporate veils', 'path', ['tp_ubo'], 0.91),
      evi('Ownership chain is structurally closed (cycle of trust)', 'ring', ['ring_shell_chain'], 0.86),
      evi('Funds reach UBO-controlled account in 5 wires', 'path', ['tp_flow'], 0.92),
      evi('Nominee director and UBO share authentication device', 'edge', ['h_lina_alaric_device'], 0.82),
      evi('Two addresses host four nominally unrelated shells', 'signal', ['sig_addr_reuse'], 0.78),
    ],
    narrative: {
      headline: 'Concealed UBO operating a 4-layer offshore cascade with €4.4M layered through Zürich.',
      body: 'Topology traversal seeded at p_alaric resolves through a deliberately opaque BVI → GP → SRL → KY chain into operating co. Arclight. Reverse-edge traversal from the terminal wire matches the same chain — strong structural closure. Device-fingerprint correlation collapses the nominee façade.',
      highlights: ['ownership layering 0.92', 'address reuse', 'device co-auth', 'closed reverse edge'],
    },
  };

  const benchmark: BenchmarkComparison = {
    question: 'Who ultimately controls Arclight Trading, and how do funds flow to them?',
    groundTruth:
      'A. Voss controls Arclight via a 4-layer offshore cascade. €4.4M flows from Meridian → EU/US accounts → Zürich-nested accounts under common UBO.',
    results: {
      pure_llm: {
        method: 'pure_llm',
        latencyMs: 8400,
        tokens: 9800,
        confidence: 0.32,
        hops: 0,
        relationshipsFound: 1,
        relationshipsMissed: 9,
        hiddenLinksFound: 0,
        ringsDetected: 0,
        answer:
          'Based on the names provided, Arclight Trading appears to be a subsidiary of Orchid Ltd. Beyond that, ownership cannot be determined without further context.',
        trace: ['LLM completion only'],
        blindSpots: [
          'No traversal of ownership cascade',
          'No detection of nominee structure',
          'Missed device-fingerprint correlation',
          'Missed shared-address signal',
          'Cannot identify UBO',
        ],
      },
      vector_rag: {
        method: 'vector_rag',
        latencyMs: 3100,
        tokens: 4600,
        confidence: 0.51,
        hops: 1,
        relationshipsFound: 3,
        relationshipsMissed: 7,
        hiddenLinksFound: 0,
        ringsDetected: 0,
        answer:
          'Arclight Trading is owned by Orchid Ltd KY (per filings). L. Marek appears as director on several shell entities. Wire activity is consistent with cross-border layering, but the ultimate beneficiary is not retrievable from document snippets.',
        trace: ['filing-doc-823', 'kyc-snippet-441', 'address-record-127'],
        blindSpots: [
          'Document chunks lack relational context',
          'No multi-hop reasoning across shells',
          'Missed reverse-edge from terminal wire',
          'Cannot fuse device fingerprint with UBO',
        ],
      },
      graph_rag: {
        method: 'graph_rag',
        latencyMs: 1850,
        tokens: 3200,
        confidence: 0.94,
        hops: 5,
        relationshipsFound: 10,
        relationshipsMissed: 0,
        hiddenLinksFound: 3,
        ringsDetected: 1,
        answer:
          'A. Voss controls Arclight via a 4-layer offshore cascade (Obsidian BVI → Helix GP → Kappa SRL → Orchid KY → Arclight). Funds flow from Meridian (controlled by O. Hess) through EU/US accounts into Zürich-nested accounts. Reverse traversal from the terminal €420K wire collapses to the same UBO. Nominee director L. Marek shares an authentication device with the UBO.',
        trace: [
          'shortest_path(p_alaric → co_arclight)',
          'ring_detected(ring_shell_chain)',
          'reverse_edge(tx_w4 → sc_orchid)',
          'device_fingerprint(dev_legalpad)',
          'address_reuse(addr_nicosia, addr_vaduz)',
        ],
        blindSpots: [],
      },
    },
  };

  return {
    id: 'shell_cascade',
    label: 'Shell Cascade',
    description:
      '4-layer offshore ownership cascade concealing UBO behind nominee directors and reused registered addresses.',
    tags: ['UBO', 'offshore', 'layering', 'AML'],
    tone: 'amber',
    graph: { entities, edges },
    rings,
    hidden,
    paths,
    signals,
    stream,
    report,
    seed: 'p_alaric',
    benchmark,
  };
}

/* -------------------------------------------------------------------------- */
/* PRESET 2 — Card Ring Topology                                              */
/* -------------------------------------------------------------------------- */

function presetCardRing(): PresetSnapshot {
  const entities: Entity[] = [
    ent('p_kade', 'K. Aro', 'person', 88, 8),
    ent('p_nia', 'N. Idris', 'person', 81, 7),
    ent('p_sami', 'S. Olu', 'person', 74, 6),
    ent('p_jules', 'J. Park', 'person', 68, 5),
    ent('p_meta', 'M. Tan', 'person', 56, 4),
    ent('acc_a1', 'CARD-• 4421', 'account', 78, 6),
    ent('acc_a2', 'CARD-• 9009', 'account', 76, 6),
    ent('acc_a3', 'CARD-• 6612', 'account', 73, 5),
    ent('acc_a4', 'CARD-• 7741', 'account', 71, 5),
    ent('acc_a5', 'CARD-• 8025', 'account', 65, 4),
    ent('dev_d1', 'Pixel-7-PRO/SIM-α', 'device', 84, 6),
    ent('dev_d2', 'Pixel-6/SIM-β', 'device', 80, 5),
    ent('dev_d3', 'iPhone-15/SIM-γ', 'device', 72, 4),
    ent('addr_a1', '88 Royston Ln, MAN', 'address', 76, 5),
    ent('addr_a2', '14 Birch St, LDS', 'address', 68, 4),
    ent('ph_a1', '+44 7700 ••012', 'phone', 80, 5),
    ent('ph_a2', '+44 7700 ••340', 'phone', 74, 4),
    ent('co_merch', 'Royston Retail Ltd', 'company', 70, 5),
    ent('co_payproc', 'PayBridge Acquirer', 'company', 35, 4),
    ent('tx_a1', 'CHARGE £4,200', 'transaction', 72, 4),
    ent('tx_a2', 'CHARGE £3,950', 'transaction', 70, 4),
    ent('tx_a3', 'CHARGE £4,800', 'transaction', 73, 4),
  ];

  const edges: Edge[] = [
    edg('p_kade', 'acc_a1', 'controls', 8),
    edg('p_kade', 'acc_a2', 'controls', 7),
    edg('p_nia', 'acc_a3', 'controls', 7),
    edg('p_sami', 'acc_a4', 'controls', 6),
    edg('p_jules', 'acc_a5', 'controls', 6),
    edg('p_meta', 'acc_a5', 'authorizes', 5),
    edg('acc_a1', 'dev_d1', 'shares_device', 7),
    edg('acc_a2', 'dev_d1', 'shares_device', 7),
    edg('acc_a3', 'dev_d2', 'shares_device', 6),
    edg('acc_a4', 'dev_d2', 'shares_device', 6),
    edg('acc_a5', 'dev_d3', 'shares_device', 5),
    edg('p_kade', 'ph_a1', 'shares_phone', 6),
    edg('p_nia', 'ph_a1', 'shares_phone', 5, 0.78, true),
    edg('p_sami', 'ph_a2', 'shares_phone', 5),
    edg('p_jules', 'ph_a2', 'shares_phone', 5, 0.74, true),
    edg('acc_a1', 'addr_a1', 'shares_address', 6),
    edg('acc_a2', 'addr_a1', 'shares_address', 6),
    edg('acc_a3', 'addr_a1', 'shares_address', 5),
    edg('acc_a4', 'addr_a2', 'shares_address', 5),
    edg('acc_a5', 'addr_a2', 'shares_address', 5),
    edg('co_merch', 'addr_a1', 'shares_address', 7),
    edg('co_merch', 'co_payproc', 'wires_to', 6),
    edg('acc_a1', 'co_merch', 'transfers', 7),
    edg('acc_a2', 'co_merch', 'transfers', 6),
    edg('acc_a3', 'co_merch', 'transfers', 6),
    edg('acc_a4', 'co_merch', 'transfers', 5),
    edg('acc_a5', 'co_merch', 'transfers', 5),
    edg('co_merch', 'tx_a1', 'transfers', 6),
    edg('co_merch', 'tx_a2', 'transfers', 6),
    edg('co_merch', 'tx_a3', 'transfers', 6),
    edg('p_kade', 'co_merch', 'hidden_link', 6, 0.78, true, { via: 'address + acquirer' }),
  ];

  const rings: Ring[] = [
    {
      id: 'ring_card_circle',
      name: 'Royston Retail bust-out ring',
      members: ['p_kade', 'p_nia', 'p_sami', 'p_jules', 'co_merch'],
      cohesion: 0.81,
      signal: 'shared_infrastructure',
      risk: 'critical',
    },
  ];

  const hidden: HiddenRelationship[] = [
    {
      id: 'h_kade_merch',
      from: 'p_kade',
      to: 'co_merch',
      via: ['addr_a1', 'co_payproc'],
      reason: 'Ring leader linked to the merchant beneficiary via shared address & acquirer',
      confidence: 0.83,
    },
    {
      id: 'h_phones',
      from: 'p_kade',
      to: 'p_nia',
      via: ['ph_a1'],
      reason: 'Recycled phone number across two ring members',
      confidence: 0.78,
    },
  ];

  const paths: TraversalPath[] = [
    {
      id: 'tp_card_flow',
      label: 'Bust-out flow → merchant',
      nodes: ['p_kade', 'acc_a1', 'co_merch', 'tx_a1'],
      edges: [],
      hops: 3,
      why: 'Card → friendly merchant → settlement, classic bust-out pattern.',
      intent: 'evidence_chain',
    },
    {
      id: 'tp_card_short',
      label: 'Shortest path Kade → Merchant',
      nodes: ['p_kade', 'addr_a1', 'co_merch'],
      edges: [],
      hops: 2,
      why: 'Shared address collapses 5 nominal identities onto one merchant.',
      intent: 'shortest_path',
    },
  ];

  const signals: StructuralSignal[] = [
    {
      id: 'sig_dev_cluster',
      name: 'Device fingerprint cluster',
      description: '5 cards transact from 3 devices in tight rotation',
      intensity: 0.88,
      contributors: ['dev_d1', 'dev_d2', 'dev_d3'],
    },
    {
      id: 'sig_addr_collapse',
      name: 'Address collapse',
      description: 'All 5 cards bill to 2 addresses tied to the merchant',
      intensity: 0.85,
      contributors: ['addr_a1', 'addr_a2', 'co_merch'],
    },
  ];

  const stream: StreamEvent[] = [
    evt('session.start', 'Seed p_kade • bust-out heuristic loaded'),
    evt('topology.expanded', '5 cards within 2 hops'),
    evt('entity.discovered', 'Card cluster CARD-•4421 / •9009 / •6612 / •7741 / •8025', {
      refs: ['acc_a1', 'acc_a2', 'acc_a3', 'acc_a4', 'acc_a5'],
    }),
    evt('signal.surfaced', 'Device cluster intensity 0.88', { refs: ['sig_dev_cluster'] }),
    evt('signal.surfaced', 'Address collapse intensity 0.85', { refs: ['sig_addr_collapse'] }),
    evt('ring.detected', 'Bust-out ring around Royston Retail (cohesion 0.81)', {
      refs: ['ring_card_circle'],
      severity: 'critical',
    }),
    evt('hidden.relationship', 'p_kade ↔ Royston Retail via address+acquirer', {
      refs: ['h_kade_merch'],
      severity: 'critical',
    }),
    evt('hidden.relationship', 'p_kade ↔ p_nia via recycled phone', { refs: ['h_phones'] }),
    evt('path.discovered', 'Shortest path Kade → Merchant (2 hops)', { refs: ['tp_card_short'] }),
    evt('suspicion.escalated', 'p_kade escalated → CRITICAL', { severity: 'critical' }),
    evt('evidence.collected', '6 structural evidence items chained'),
    evt('session.complete', 'Investigation complete • 22 entities'),
  ];

  const report: IntelReport = {
    suspects: entities.filter((e) => e.risk >= 60 && e.kind === 'person'),
    hiddenRelationships: hidden,
    rings,
    ownershipFlow: paths.filter((p) => p.intent === 'shortest_path'),
    transactionFlows: paths.filter((p) => p.intent === 'evidence_chain'),
    sharedInfrastructure: [
      {
        id: 'si_dev_d1',
        from: 'acc_a1',
        to: 'acc_a2',
        via: ['dev_d1'],
        reason: 'Two cards share the same device fingerprint',
        confidence: 0.9,
      },
      {
        id: 'si_addr',
        from: 'co_merch',
        to: 'p_kade',
        via: ['addr_a1'],
        reason: 'Ring leader and beneficiary merchant co-located',
        confidence: 0.83,
      },
    ],
    traversalPaths: paths,
    structuralSignals: signals,
    evidence: [
      evi('Five cards rotate across three devices', 'signal', ['sig_dev_cluster'], 0.88),
      evi('All cards bill to two addresses tied to merchant', 'signal', ['sig_addr_collapse'], 0.85),
      evi('Ring leader linked to merchant via address+acquirer', 'edge', ['h_kade_merch'], 0.83),
    ],
    narrative: {
      headline: 'Five-card bust-out ring funneling £120K through a captive merchant.',
      body: 'Device fingerprint and address collapse compress 5 nominally distinct identities into one operational ring. The ring leader has no direct edge to the merchant — only a graph-native traversal exposes the indirect ownership through the acquirer and shared address.',
      highlights: ['device cluster', 'address collapse', 'captive merchant', 'recycled phones'],
    },
  };

  const benchmark: BenchmarkComparison = {
    question: 'Are these 5 cards an independent fraud spike, or a coordinated ring?',
    groundTruth:
      'Coordinated ring. 5 cards share 3 devices, 2 addresses, and route to a captive merchant whose acquirer flow returns funds to the ring leader.',
    results: {
      pure_llm: {
        method: 'pure_llm',
        latencyMs: 7800,
        tokens: 7400,
        confidence: 0.28,
        hops: 0,
        relationshipsFound: 0,
        relationshipsMissed: 7,
        hiddenLinksFound: 0,
        ringsDetected: 0,
        answer:
          'Without transactional context the 5 cards appear independent. They share some geographic proximity which may be coincidental.',
        trace: ['LLM completion only'],
        blindSpots: [
          'No device fingerprinting',
          'No graph clustering',
          'Cannot connect cards through merchant',
        ],
      },
      vector_rag: {
        method: 'vector_rag',
        latencyMs: 2800,
        tokens: 3900,
        confidence: 0.46,
        hops: 1,
        relationshipsFound: 2,
        relationshipsMissed: 5,
        hiddenLinksFound: 0,
        ringsDetected: 0,
        answer:
          'The cards may be connected — chunks mention overlapping addresses, but the relationship to the merchant is not retrievable.',
        trace: ['kyc-doc-91', 'address-122'],
        blindSpots: ['Cannot collapse identities through device fingerprints'],
      },
      graph_rag: {
        method: 'graph_rag',
        latencyMs: 1650,
        tokens: 2800,
        confidence: 0.93,
        hops: 3,
        relationshipsFound: 7,
        relationshipsMissed: 0,
        hiddenLinksFound: 2,
        ringsDetected: 1,
        answer:
          'Coordinated bust-out ring. Cards collapse to 3 devices, 2 addresses, and converge on Royston Retail. The merchant routes settlement back to the ring leader via PayBridge.',
        trace: [
          'cluster(devices)',
          'cluster(addresses)',
          'ring_detected(ring_card_circle)',
          'hidden_link(p_kade → co_merch)',
        ],
        blindSpots: [],
      },
    },
  };

  return {
    id: 'card_ring',
    label: 'Card Ring Topology',
    description:
      'Bust-out card fraud ring concealed under nominal identity diversity, compressed by device + address graph.',
    tags: ['card-fraud', 'bust-out', 'ring', 'merchant'],
    tone: 'rose',
    graph: { entities, edges },
    rings,
    hidden,
    paths,
    signals,
    stream,
    report,
    seed: 'p_kade',
    benchmark,
  };
}

/* -------------------------------------------------------------------------- */
/* Lighter presets (3-8) — same structural completeness, denser per-section.  */
/* -------------------------------------------------------------------------- */

function buildPreset(
  id: string,
  label: string,
  description: string,
  tags: string[],
  tone: PresetSnapshot['tone'],
  seedLabel: string,
  factory: () => {
    entities: Entity[];
    edges: Edge[];
    rings: Ring[];
    hidden: HiddenRelationship[];
    paths: TraversalPath[];
    signals: StructuralSignal[];
    stream: StreamEvent[];
    narrative: { headline: string; body: string; highlights: string[] };
    benchmark: BenchmarkComparison;
    seed: string;
  }
): PresetSnapshot {
  const f = factory();
  const persons = f.entities.filter((e) => e.kind === 'person');
  const suspects = persons.filter((p) => p.risk >= 60);
  const report: IntelReport = {
    suspects,
    hiddenRelationships: f.hidden,
    rings: f.rings,
    ownershipFlow: f.paths.filter((p) => p.intent === 'shortest_path'),
    transactionFlows: f.paths.filter((p) => p.intent === 'evidence_chain'),
    sharedInfrastructure: f.hidden.filter((h) => h.via.length === 1),
    traversalPaths: f.paths,
    structuralSignals: f.signals,
    evidence: [
      ...f.paths.map((p) =>
        evi(`Path: ${p.label}`, 'path', [p.id], 0.78 + Math.random() * 0.18)
      ),
      ...f.signals.map((s) =>
        evi(`Signal: ${s.name}`, 'signal', [s.id], s.intensity)
      ),
      ...f.rings.map((r) => evi(`Ring: ${r.name}`, 'ring', [r.id], r.cohesion)),
    ],
    narrative: f.narrative,
  };
  return {
    id,
    label,
    description: `${description} Seed entity: ${seedLabel}.`,
    tags,
    tone,
    graph: { entities: f.entities, edges: f.edges },
    rings: f.rings,
    hidden: f.hidden,
    paths: f.paths,
    signals: f.signals,
    stream: f.stream,
    report,
    seed: f.seed,
    benchmark: f.benchmark,
  };
}

function presetSanctions(): PresetSnapshot {
  return buildPreset(
    'sanctions_evasion',
    'Sanctions Evasion',
    'OFAC-listed UBO concealed behind 3 proxies and a logistics front.',
    ['sanctions', 'OFAC', 'proxies'],
    'rose',
    'D. Volkov',
    () => {
      const entities: Entity[] = [
        ent('p_volkov', 'D. Volkov', 'person', 95, 9, { flags: ['OFAC-SDN'] }),
        ent('p_aria', 'A. Ferro', 'person', 78, 6, { flags: ['proxy'] }),
        ent('p_marco', 'M. Beltran', 'person', 72, 5, { flags: ['proxy'] }),
        ent('p_yelena', 'Y. Ines', 'person', 66, 5),
        ent('sc_irongate', 'Irongate Holdings', 'shell_company', 84, 7),
        ent('sc_blacksail', 'Blacksail Maritime', 'shell_company', 79, 6),
        ent('co_polaris', 'Polaris Freight', 'company', 60, 5),
        ent('acc_dxb1', 'DXB-• 9912', 'account', 80, 6),
        ent('acc_dxb2', 'DXB-• 4422', 'account', 76, 5),
        ent('acc_cy1', 'CY-• 7710', 'account', 72, 5),
        ent('addr_dxb', 'Cluster X, JLT, Dubai', 'address', 64, 4),
        ent('addr_cy', 'Limassol office tower', 'address', 60, 4),
        ent('dev_phone', 'Encrypted handset σ', 'device', 78, 5),
        ent('tx_oil', 'OIL CARGO 18M USD', 'transaction', 88, 7),
        ent('tx_settle', 'SETTLE 3.4M USD', 'transaction', 74, 5),
      ];
      const edges: Edge[] = [
        edg('p_volkov', 'sc_irongate', 'controls', 9, 0.94),
        edg('p_aria', 'sc_irongate', 'authorizes', 5, 0.8),
        edg('sc_irongate', 'sc_blacksail', 'owns', 8, 0.88),
        edg('sc_blacksail', 'co_polaris', 'owns', 7, 0.84),
        edg('p_marco', 'co_polaris', 'employs', 5, 0.74),
        edg('p_yelena', 'co_polaris', 'controls', 4, 0.7),
        edg('co_polaris', 'acc_dxb1', 'owns', 7),
        edg('sc_blacksail', 'acc_dxb2', 'owns', 6),
        edg('sc_irongate', 'acc_cy1', 'owns', 6),
        edg('acc_dxb1', 'tx_oil', 'transfers', 9, 0.94),
        edg('tx_oil', 'acc_cy1', 'transfers', 8, 0.9),
        edg('acc_cy1', 'tx_settle', 'transfers', 7, 0.86),
        edg('sc_irongate', 'addr_cy', 'shares_address', 4, 0.7),
        edg('sc_blacksail', 'addr_dxb', 'shares_address', 4, 0.7),
        edg('p_aria', 'dev_phone', 'authorizes', 4, 0.72),
        edg('p_volkov', 'dev_phone', 'shares_device', 5, 0.74, true),
        edg('p_volkov', 'co_polaris', 'hidden_link', 6, 0.86, true, { via: 'corporate cascade' }),
      ];
      const rings: Ring[] = [
        {
          id: 'ring_proxy_layer',
          name: 'Proxy layer hiding OFAC UBO',
          members: ['p_volkov', 'p_aria', 'sc_irongate', 'sc_blacksail', 'co_polaris'],
          cohesion: 0.82,
          signal: 'ownership_layering',
          risk: 'critical',
        },
      ];
      const hidden: HiddenRelationship[] = [
        {
          id: 'h_volkov_polaris',
          from: 'p_volkov',
          to: 'co_polaris',
          via: ['sc_irongate', 'sc_blacksail'],
          reason: '3-hop ownership exposes UBO through Polaris',
          confidence: 0.91,
        },
        {
          id: 'h_dev_aria_volkov',
          from: 'p_volkov',
          to: 'p_aria',
          via: ['dev_phone'],
          reason: 'Encrypted handset reused by sanctioned UBO and proxy',
          confidence: 0.79,
        },
      ];
      const paths: TraversalPath[] = [
        {
          id: 'tp_sanc_ubo',
          label: 'OFAC UBO → operating front',
          nodes: ['p_volkov', 'sc_irongate', 'sc_blacksail', 'co_polaris'],
          edges: [],
          hops: 3,
          why: 'Shortest path through proxy directors to operating freight company.',
          intent: 'shortest_path',
        },
        {
          id: 'tp_oil_flow',
          label: 'Oil cargo proceeds → CY settlement',
          nodes: ['acc_dxb1', 'tx_oil', 'acc_cy1', 'tx_settle'],
          edges: [],
          hops: 3,
          why: 'Cargo proceeds settled into CY-account under UBO control',
          intent: 'evidence_chain',
        },
        {
          id: 'tp_sanc_reverse',
          label: 'Reverse-edge from settlement',
          nodes: ['tx_settle', 'acc_cy1', 'sc_irongate', 'p_volkov'],
          edges: [],
          hops: 3,
          why: 'Reverse traversal of settlement lands on sanctioned UBO',
          intent: 'reverse_edge',
        },
      ];
      const signals: StructuralSignal[] = [
        {
          id: 'sig_proxy_density',
          name: 'Proxy director density',
          description: '2 proxies hold all visible signatory rights',
          intensity: 0.84,
          contributors: ['p_aria', 'p_marco'],
        },
        {
          id: 'sig_jur_hops',
          name: 'Jurisdictional layering',
          description: 'DXB → CY → SDN UBO across two opaque jurisdictions',
          intensity: 0.78,
          contributors: ['addr_dxb', 'addr_cy'],
        },
      ];
      const stream: StreamEvent[] = [
        evt('session.start', 'Seed p_volkov • sanctions screen loaded', { refs: ['p_volkov'] }),
        evt('topology.expanded', 'Proxy layer surfaced (2 entities)'),
        evt('ring.detected', 'Proxy layer hides OFAC UBO', { refs: ['ring_proxy_layer'], severity: 'critical' }),
        evt('hidden.relationship', 'Volkov → Polaris via 3-hop cascade', {
          refs: ['h_volkov_polaris'],
          severity: 'critical',
        }),
        evt('path.discovered', 'Oil cargo settlement chain identified', { refs: ['tp_oil_flow'] }),
        evt('signal.surfaced', 'Proxy director density 0.84', { refs: ['sig_proxy_density'] }),
        evt('suspicion.escalated', 'co_polaris flagged for OFAC nexus', { severity: 'critical' }),
        evt('evidence.collected', '5 evidence items chained'),
        evt('session.complete', 'Investigation complete'),
      ];
      const benchmark: BenchmarkComparison = {
        question: 'Does Polaris Freight have OFAC exposure?',
        groundTruth:
          'Yes. Polaris is owned through a 3-hop cascade by D. Volkov, an OFAC-SDN. Oil cargo proceeds settle into a CY account under the same UBO.',
        results: {
          pure_llm: {
            method: 'pure_llm',
            latencyMs: 7600,
            tokens: 7200,
            confidence: 0.25,
            hops: 0,
            relationshipsFound: 0,
            relationshipsMissed: 6,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Polaris Freight is not publicly listed under any sanctions list.',
            trace: ['LLM completion only'],
            blindSpots: ['Cannot traverse beyond named entity', 'Misses cascade'],
          },
          vector_rag: {
            method: 'vector_rag',
            latencyMs: 3000,
            tokens: 4100,
            confidence: 0.4,
            hops: 1,
            relationshipsFound: 1,
            relationshipsMissed: 5,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer:
              'Polaris is owned by Blacksail Maritime according to filings. No direct sanctions match.',
            trace: ['filing-882', 'sanc-list-snippet-71'],
            blindSpots: ['No multi-hop traversal'],
          },
          graph_rag: {
            method: 'graph_rag',
            latencyMs: 1700,
            tokens: 2900,
            confidence: 0.95,
            hops: 3,
            relationshipsFound: 6,
            relationshipsMissed: 0,
            hiddenLinksFound: 2,
            ringsDetected: 1,
            answer:
              'Polaris Freight is owned through a 3-hop cascade by D. Volkov (OFAC-SDN). Oil cargo proceeds settle into a CY account under the same UBO. Proxy directors A. Ferro and M. Beltran obscure signatory rights.',
            trace: ['shortest_path(p_volkov → co_polaris)', 'sanctions_join', 'reverse_edge(tx_settle → p_volkov)'],
            blindSpots: [],
          },
        },
      };
      return {
        entities,
        edges,
        rings,
        hidden,
        paths,
        signals,
        stream,
        narrative: {
          headline: 'OFAC-SDN UBO operating maritime freight via 3-hop proxy cascade.',
          body: 'Graph-native traversal exposes a sanctioned UBO behind two proxies and three corporate hops. Reverse traversal from settlement transaction lands on the same UBO — structural closure.',
          highlights: ['OFAC nexus', 'proxy density 0.84', 'reverse edge closure'],
        },
        benchmark,
        seed: 'p_volkov',
      };
    }
  );
}

function presetCryptoMixer(): PresetSnapshot {
  return buildPreset(
    'crypto_mixer',
    'Crypto Mixer Web',
    'Wallet cluster fragmenting funds through 4 mixers — collapsed by topology.',
    ['crypto', 'mixers', 'wallets'],
    'violet',
    'wallet_seed',
    () => {
      const entities: Entity[] = [
        ent('w_seed', 'WALLET 0xA9..b2', 'wallet', 90, 8),
        ent('w_m1', 'MIXER-α 0x88..1f', 'wallet', 76, 6),
        ent('w_m2', 'MIXER-β 0xC1..7e', 'wallet', 76, 6),
        ent('w_m3', 'MIXER-γ 0x52..a0', 'wallet', 76, 6),
        ent('w_m4', 'MIXER-δ 0x77..91', 'wallet', 76, 6),
        ent('w_split1', 'WALLET 0x12..ab', 'wallet', 64, 5),
        ent('w_split2', 'WALLET 0x34..cd', 'wallet', 64, 5),
        ent('w_split3', 'WALLET 0x56..ef', 'wallet', 64, 5),
        ent('w_split4', 'WALLET 0x78..gh', 'wallet', 64, 5),
        ent('w_recombine', 'WALLET 0xFE..23', 'wallet', 88, 7),
        ent('w_offramp', 'WALLET 0xDD..00', 'wallet', 86, 7),
        ent('p_skye', 'S. Wren', 'person', 84, 7, { flags: ['exchange-KYC'] }),
        ent('co_exchange', 'NorthGate Exchange', 'company', 30, 4),
        ent('tx_offramp', 'OFFRAMP 4.2M USDT', 'transaction', 84, 6),
      ];
      const edges: Edge[] = [
        edg('w_seed', 'w_m1', 'transfers', 8),
        edg('w_seed', 'w_m2', 'transfers', 8),
        edg('w_seed', 'w_m3', 'transfers', 8),
        edg('w_seed', 'w_m4', 'transfers', 8),
        edg('w_m1', 'w_split1', 'transfers', 5),
        edg('w_m2', 'w_split2', 'transfers', 5),
        edg('w_m3', 'w_split3', 'transfers', 5),
        edg('w_m4', 'w_split4', 'transfers', 5),
        edg('w_split1', 'w_recombine', 'transfers', 6),
        edg('w_split2', 'w_recombine', 'transfers', 6),
        edg('w_split3', 'w_recombine', 'transfers', 6),
        edg('w_split4', 'w_recombine', 'transfers', 6),
        edg('w_recombine', 'w_offramp', 'transfers', 9),
        edg('w_offramp', 'co_exchange', 'transfers', 8),
        edg('co_exchange', 'tx_offramp', 'transfers', 8),
        edg('p_skye', 'co_exchange', 'kyc_match', 6, 0.92),
        edg('w_seed', 'w_offramp', 'hidden_link', 7, 0.84, true, { via: '4 mixers recombined' }),
        edg('p_skye', 'w_seed', 'hidden_link', 6, 0.78, true, { via: 'KYC ↔ wallet cluster' }),
      ];
      const rings: Ring[] = [
        {
          id: 'ring_split_recombine',
          name: 'Split-and-recombine mixer cluster',
          members: ['w_m1', 'w_m2', 'w_m3', 'w_m4', 'w_recombine'],
          cohesion: 0.78,
          signal: 'fan_out',
          risk: 'high',
        },
      ];
      const hidden: HiddenRelationship[] = [
        {
          id: 'h_seed_offramp',
          from: 'w_seed',
          to: 'w_offramp',
          via: ['w_m1', 'w_m2', 'w_m3', 'w_m4', 'w_recombine'],
          reason: 'Funds recombine after 4-way split through mixers',
          confidence: 0.84,
        },
        {
          id: 'h_skye_seed',
          from: 'p_skye',
          to: 'w_seed',
          via: ['co_exchange'],
          reason: 'KYC at off-ramp resolves cluster onto person',
          confidence: 0.78,
        },
      ];
      const paths: TraversalPath[] = [
        {
          id: 'tp_mixer',
          label: 'Mixer split → recombine → off-ramp',
          nodes: ['w_seed', 'w_m1', 'w_split1', 'w_recombine', 'w_offramp', 'co_exchange'],
          edges: [],
          hops: 5,
          why: 'Demonstrates that split + recombine pattern is structurally trivial in graph space',
          intent: 'evidence_chain',
        },
        {
          id: 'tp_offramp_reverse',
          label: 'Reverse-edge from KYC off-ramp',
          nodes: ['tx_offramp', 'co_exchange', 'p_skye', 'w_seed'],
          edges: [],
          hops: 3,
          why: 'Reverse-edge from settled fiat lands on the source wallet',
          intent: 'reverse_edge',
        },
      ];
      const signals: StructuralSignal[] = [
        {
          id: 'sig_fanout',
          name: 'Fan-out signature',
          description: '1 source → 4 mixers in 1 block window',
          intensity: 0.92,
          contributors: ['w_seed', 'w_m1', 'w_m2', 'w_m3', 'w_m4'],
        },
        {
          id: 'sig_recombine',
          name: 'Recombination tightness',
          description: '4 paths recombine in a single wallet within 6 minutes',
          intensity: 0.86,
          contributors: ['w_recombine'],
        },
      ];
      const stream: StreamEvent[] = [
        evt('session.start', 'Seed wallet 0xA9..b2'),
        evt('topology.expanded', 'Mixer cluster surfaced (4 wallets)'),
        evt('signal.surfaced', 'Fan-out signature 0.92', { refs: ['sig_fanout'] }),
        evt('signal.surfaced', 'Recombination tightness 0.86', { refs: ['sig_recombine'] }),
        evt('ring.detected', 'Split-and-recombine cluster identified', {
          refs: ['ring_split_recombine'],
          severity: 'high',
        }),
        evt('hidden.relationship', 'Seed ↔ Off-ramp via mixers', {
          refs: ['h_seed_offramp'],
          severity: 'high',
        }),
        evt('hidden.relationship', 'S. Wren tied to cluster via KYC off-ramp', {
          refs: ['h_skye_seed'],
          severity: 'high',
        }),
        evt('path.discovered', 'Reverse-edge from off-ramp lands on seed wallet', {
          refs: ['tp_offramp_reverse'],
        }),
        evt('suspicion.escalated', 'S. Wren tagged HIGH', { severity: 'high' }),
        evt('session.complete', 'Investigation complete'),
      ];
      const benchmark: BenchmarkComparison = {
        question: 'Does the off-ramp wallet belong to the same actor as the seed wallet?',
        groundTruth: 'Yes — 4 mixers recombine and surface S. Wren via exchange KYC.',
        results: {
          pure_llm: {
            method: 'pure_llm',
            latencyMs: 7200,
            tokens: 6800,
            confidence: 0.22,
            hops: 0,
            relationshipsFound: 0,
            relationshipsMissed: 5,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Mixer obfuscation prevents attribution.',
            trace: ['LLM completion only'],
            blindSpots: ['No graph clustering'],
          },
          vector_rag: {
            method: 'vector_rag',
            latencyMs: 2900,
            tokens: 4200,
            confidence: 0.38,
            hops: 1,
            relationshipsFound: 1,
            relationshipsMissed: 4,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Off-ramp wallet appears in exchange filings but cluster is unclear.',
            trace: ['exch-snippet-203'],
            blindSpots: ['No mixer-aware traversal'],
          },
          graph_rag: {
            method: 'graph_rag',
            latencyMs: 1500,
            tokens: 2600,
            confidence: 0.93,
            hops: 5,
            relationshipsFound: 5,
            relationshipsMissed: 0,
            hiddenLinksFound: 2,
            ringsDetected: 1,
            answer:
              'Yes. The split-and-recombine pattern is structurally trivial: 1 source → 4 mixers → 4 splits → 1 recombination → off-ramp. KYC at the off-ramp resolves the cluster to S. Wren.',
            trace: ['fanout_detect', 'recombine_detect', 'reverse_edge(tx_offramp → w_seed)', 'kyc_join'],
            blindSpots: [],
          },
        },
      };
      return {
        entities,
        edges,
        rings,
        hidden,
        paths,
        signals,
        stream,
        narrative: {
          headline: 'Mixer obfuscation collapses under split + recombine topology.',
          body: 'The fan-out + recombination pattern is visually obvious to graph-native reasoning, even though every chunk-level method sees only an opaque mixer step.',
          highlights: ['fan-out 0.92', 'recombine 0.86', 'KYC pivot'],
        },
        benchmark,
        seed: 'w_seed',
      };
    }
  );
}

function presetMule(): PresetSnapshot {
  return buildPreset(
    'mule_network',
    'Mule Network',
    'Money-mule network rotating across 12 devices and 3 wifi APs.',
    ['mules', 'devices', 'rotation'],
    'amber',
    'p_handler',
    () => {
      const entities: Entity[] = [
        ent('p_handler', 'H. Reyes', 'person', 88, 8),
        ...Array.from({ length: 6 }, (_, i) =>
          ent(`p_mule_${i}`, `Mule ${i + 1}`, 'person', 50 + (i % 3) * 6, 4)
        ),
        ent('dev_pool_1', 'Pool device set A (4)', 'device', 78, 5),
        ent('dev_pool_2', 'Pool device set B (5)', 'device', 76, 5),
        ent('dev_pool_3', 'Pool device set C (3)', 'device', 74, 4),
        ent('addr_studio', '12 Bay Studio Flat', 'address', 70, 4),
        ent('acc_pool', 'POOL ACC •••• 11', 'account', 82, 6),
        ent('tx_pool', 'AGGREGATE £180K', 'transaction', 80, 5),
      ];
      const edges: Edge[] = [
        ...entities
          .filter((e) => e.id.startsWith('p_mule'))
          .flatMap((m, i) => [
            edg(m.id, ['dev_pool_1', 'dev_pool_2', 'dev_pool_3'][i % 3], 'shares_device', 5),
            edg(m.id, 'acc_pool', 'authorizes', 4),
            edg(m.id, 'addr_studio', 'shares_address', 4),
          ]),
        edg('p_handler', 'dev_pool_1', 'controls', 6, 0.86),
        edg('p_handler', 'acc_pool', 'controls', 7, 0.86),
        edg('acc_pool', 'tx_pool', 'transfers', 8),
        edg('p_handler', 'addr_studio', 'shares_address', 5, 0.82, true),
      ];
      const rings: Ring[] = [
        {
          id: 'ring_mules',
          name: 'Bay Studio mule rotation',
          members: ['p_handler', 'p_mule_0', 'p_mule_1', 'p_mule_2', 'p_mule_3', 'p_mule_4', 'p_mule_5', 'addr_studio'],
          cohesion: 0.84,
          signal: 'shared_infrastructure',
          risk: 'high',
        },
      ];
      const hidden: HiddenRelationship[] = [
        {
          id: 'h_handler_pool',
          from: 'p_handler',
          to: 'acc_pool',
          via: ['dev_pool_1'],
          reason: 'Handler authenticates onto pool from the same device set as mules',
          confidence: 0.84,
        },
        {
          id: 'h_studio',
          from: 'p_handler',
          to: 'p_mule_0',
          via: ['addr_studio'],
          reason: 'Shared accommodation address',
          confidence: 0.7,
        },
      ];
      const paths: TraversalPath[] = [
        {
          id: 'tp_mule_short',
          label: 'Handler → pool account (2 hops)',
          nodes: ['p_handler', 'dev_pool_1', 'acc_pool'],
          edges: [],
          hops: 2,
          why: 'Shared device exposes handler as controller of the pool',
          intent: 'shortest_path',
        },
        {
          id: 'tp_mule_flow',
          label: 'Aggregation flow',
          nodes: ['p_mule_0', 'acc_pool', 'tx_pool'],
          edges: [],
          hops: 2,
          why: 'Mules aggregate £180K into a single pool',
          intent: 'evidence_chain',
        },
      ];
      const signals: StructuralSignal[] = [
        {
          id: 'sig_dev_rotation',
          name: 'Device rotation',
          description: '6 mules cycle 12 devices in 9 days',
          intensity: 0.88,
          contributors: ['dev_pool_1', 'dev_pool_2', 'dev_pool_3'],
        },
        {
          id: 'sig_aggr',
          name: 'Aggregation density',
          description: 'All mule flows converge on one pool account',
          intensity: 0.92,
          contributors: ['acc_pool'],
        },
      ];
      const stream: StreamEvent[] = [
        evt('session.start', 'Seed p_handler'),
        evt('topology.expanded', '6 mules + 3 device sets'),
        evt('signal.surfaced', 'Device rotation 0.88', { refs: ['sig_dev_rotation'] }),
        evt('signal.surfaced', 'Aggregation 0.92', { refs: ['sig_aggr'] }),
        evt('ring.detected', 'Bay Studio rotation ring', {
          refs: ['ring_mules'],
          severity: 'high',
        }),
        evt('hidden.relationship', 'Handler → pool account via device set', {
          refs: ['h_handler_pool'],
          severity: 'high',
        }),
        evt('path.discovered', 'Aggregation chain identified', { refs: ['tp_mule_flow'] }),
        evt('session.complete', 'Investigation complete'),
      ];
      const benchmark: BenchmarkComparison = {
        question: 'Who controls the pool account, and are these 6 mules coordinated?',
        groundTruth:
          'H. Reyes controls the pool account. The 6 mules are coordinated and rotate 12 devices from a shared address.',
        results: {
          pure_llm: {
            method: 'pure_llm',
            latencyMs: 7400,
            tokens: 6900,
            confidence: 0.3,
            hops: 0,
            relationshipsFound: 0,
            relationshipsMissed: 6,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: '6 individuals appear unconnected.',
            trace: ['LLM completion only'],
            blindSpots: ['No device clustering'],
          },
          vector_rag: {
            method: 'vector_rag',
            latencyMs: 2800,
            tokens: 3900,
            confidence: 0.45,
            hops: 1,
            relationshipsFound: 2,
            relationshipsMissed: 4,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Some address overlap, individuals may be roommates.',
            trace: ['kyc-doc-22'],
            blindSpots: ['No graph rotation analysis'],
          },
          graph_rag: {
            method: 'graph_rag',
            latencyMs: 1600,
            tokens: 2700,
            confidence: 0.93,
            hops: 2,
            relationshipsFound: 6,
            relationshipsMissed: 0,
            hiddenLinksFound: 2,
            ringsDetected: 1,
            answer:
              'Coordinated mule network. H. Reyes controls the pool. 12-device rotation across 6 mules collapses to one address, one account, £180K aggregate.',
            trace: ['device_cluster', 'address_cluster', 'ring_detected(ring_mules)'],
            blindSpots: [],
          },
        },
      };
      return {
        entities,
        edges,
        rings,
        hidden,
        paths,
        signals,
        stream,
        narrative: {
          headline: 'Mule rotation network collapses under device + address clustering.',
          body: 'Across 9 days, 6 mules cycle 12 devices from a single accommodation address. Graph clustering surfaces the handler immediately.',
          highlights: ['device rotation', 'aggregation 0.92', 'handler exposed'],
        },
        benchmark,
        seed: 'p_handler',
      };
    }
  );
}

function presetProcurement(): PresetSnapshot {
  return buildPreset(
    'procurement_fraud',
    'Procurement Collusion',
    'Three vendors collude to manipulate procurement awards under a single beneficiary.',
    ['procurement', 'collusion'],
    'emerald',
    'p_proc',
    () => {
      const entities: Entity[] = [
        ent('p_proc', 'Procurement Officer P. Rae', 'person', 78, 7),
        ent('p_vendor_a', 'Vendor Principal A', 'person', 64, 5),
        ent('p_vendor_b', 'Vendor Principal B', 'person', 62, 5),
        ent('p_vendor_c', 'Vendor Principal C', 'person', 60, 5),
        ent('co_vendor_a', 'Aurora Supplies', 'company', 66, 5),
        ent('co_vendor_b', 'BlueLine LLC', 'company', 64, 5),
        ent('co_vendor_c', 'Coastal Mfg', 'company', 60, 5),
        ent('co_benef', 'Bayside Consulting', 'company', 76, 6),
        ent('acc_kickback', 'Kickback acct •••• 41', 'account', 82, 6),
        ent('addr_office', 'Suite 200, Tower B', 'address', 56, 4),
        ent('tx_award_1', 'AWARD $4.2M', 'transaction', 70, 5),
        ent('tx_award_2', 'AWARD $3.7M', 'transaction', 68, 5),
        ent('tx_award_3', 'AWARD $5.1M', 'transaction', 72, 5),
        ent('tx_kickback', 'KICKBACK $620K', 'transaction', 84, 6),
      ];
      const edges: Edge[] = [
        edg('p_vendor_a', 'co_vendor_a', 'owns', 7),
        edg('p_vendor_b', 'co_vendor_b', 'owns', 7),
        edg('p_vendor_c', 'co_vendor_c', 'owns', 7),
        edg('co_vendor_a', 'tx_award_1', 'transfers', 6),
        edg('co_vendor_b', 'tx_award_2', 'transfers', 6),
        edg('co_vendor_c', 'tx_award_3', 'transfers', 6),
        edg('co_vendor_a', 'co_benef', 'wires_to', 5),
        edg('co_vendor_b', 'co_benef', 'wires_to', 5),
        edg('co_vendor_c', 'co_benef', 'wires_to', 5),
        edg('co_benef', 'acc_kickback', 'owns', 7),
        edg('acc_kickback', 'tx_kickback', 'transfers', 8),
        edg('tx_kickback', 'p_proc', 'transfers', 7, 0.86, true),
        edg('co_vendor_a', 'addr_office', 'shares_address', 4),
        edg('co_vendor_b', 'addr_office', 'shares_address', 4),
        edg('co_vendor_c', 'addr_office', 'shares_address', 4),
        edg('p_proc', 'co_benef', 'hidden_link', 6, 0.84, true, { via: 'kickback flow' }),
      ];
      const rings: Ring[] = [
        {
          id: 'ring_collusion',
          name: 'Bid-rigging trio',
          members: ['co_vendor_a', 'co_vendor_b', 'co_vendor_c', 'co_benef'],
          cohesion: 0.82,
          signal: 'shared_infrastructure',
          risk: 'high',
        },
      ];
      const hidden: HiddenRelationship[] = [
        {
          id: 'h_proc_benef',
          from: 'p_proc',
          to: 'co_benef',
          via: ['acc_kickback'],
          reason: 'Procurement officer receives kickback from beneficiary',
          confidence: 0.84,
        },
        {
          id: 'h_vendors_share',
          from: 'co_vendor_a',
          to: 'co_vendor_b',
          via: ['addr_office'],
          reason: 'Vendors co-located at the same suite',
          confidence: 0.74,
        },
      ];
      const paths: TraversalPath[] = [
        {
          id: 'tp_proc_short',
          label: 'Officer → kickback',
          nodes: ['p_proc', 'acc_kickback', 'co_benef'],
          edges: [],
          hops: 2,
          why: 'Shortest path from officer to beneficiary',
          intent: 'shortest_path',
        },
        {
          id: 'tp_proc_flow',
          label: 'Award rotation → kickback',
          nodes: ['co_vendor_a', 'co_benef', 'acc_kickback', 'tx_kickback', 'p_proc'],
          edges: [],
          hops: 4,
          why: 'Award funds rotate through beneficiary to kickback recipient',
          intent: 'evidence_chain',
        },
      ];
      const signals: StructuralSignal[] = [
        {
          id: 'sig_award_rotation',
          name: 'Award rotation cadence',
          description: 'Awards rotate predictably between three vendors',
          intensity: 0.79,
          contributors: ['co_vendor_a', 'co_vendor_b', 'co_vendor_c'],
        },
        {
          id: 'sig_shared_suite',
          name: 'Shared business suite',
          description: 'All three vendors share a single suite address',
          intensity: 0.86,
          contributors: ['addr_office'],
        },
      ];
      const stream: StreamEvent[] = [
        evt('session.start', 'Seed p_proc'),
        evt('topology.expanded', '3 vendors + beneficiary surfaced'),
        evt('signal.surfaced', 'Award rotation cadence detected', { refs: ['sig_award_rotation'] }),
        evt('signal.surfaced', 'Shared suite signal', { refs: ['sig_shared_suite'] }),
        evt('ring.detected', 'Bid-rigging trio', { refs: ['ring_collusion'], severity: 'high' }),
        evt('hidden.relationship', 'Officer ↔ beneficiary via kickback', {
          refs: ['h_proc_benef'],
          severity: 'high',
        }),
        evt('path.discovered', 'Award → kickback chain', { refs: ['tp_proc_flow'] }),
        evt('session.complete', 'Investigation complete'),
      ];
      const benchmark: BenchmarkComparison = {
        question: 'Are these vendor awards independent, or coordinated bid-rigging?',
        groundTruth:
          'Coordinated. Three vendors share an office, rotate awards, and route a $620K kickback to the procurement officer via Bayside Consulting.',
        results: {
          pure_llm: {
            method: 'pure_llm',
            latencyMs: 7900,
            tokens: 7100,
            confidence: 0.34,
            hops: 0,
            relationshipsFound: 1,
            relationshipsMissed: 5,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Vendors appear independent; awards are within procurement norms.',
            trace: ['LLM completion only'],
            blindSpots: ['No rotation analysis'],
          },
          vector_rag: {
            method: 'vector_rag',
            latencyMs: 3100,
            tokens: 4400,
            confidence: 0.48,
            hops: 1,
            relationshipsFound: 2,
            relationshipsMissed: 4,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer:
              'Filings show overlapping office space — possible coincidence. Kickback path is not retrievable.',
            trace: ['filing-441'],
            blindSpots: ['Cannot follow funds through beneficiary'],
          },
          graph_rag: {
            method: 'graph_rag',
            latencyMs: 1750,
            tokens: 2800,
            confidence: 0.94,
            hops: 4,
            relationshipsFound: 6,
            relationshipsMissed: 0,
            hiddenLinksFound: 2,
            ringsDetected: 1,
            answer:
              'Coordinated. Three vendors share Suite 200, rotate $13M of awards, and consolidate kickbacks through Bayside Consulting to procurement officer P. Rae.',
            trace: ['cluster(office)', 'cadence(awards)', 'reverse_edge(tx_kickback → p_proc)'],
            blindSpots: [],
          },
        },
      };
      return {
        entities,
        edges,
        rings,
        hidden,
        paths,
        signals,
        stream,
        narrative: {
          headline: 'Bid-rigging trio funneling kickbacks to procurement officer.',
          body: 'Award cadence and a shared suite expose the trio. Kickback chain closes the loop to the officer.',
          highlights: ['rotation cadence', 'shared suite', 'kickback closure'],
        },
        benchmark,
        seed: 'p_proc',
      };
    }
  );
}

function presetInsider(): PresetSnapshot {
  return buildPreset(
    'insider_leak',
    'Insider Leak',
    'Tipper-tippee chain across a research lab and two trading desks.',
    ['insider', 'leak', 'tipping'],
    'ice',
    'p_tipper',
    () => {
      const entities: Entity[] = [
        ent('p_tipper', 'Dr. E. Hahn', 'person', 84, 7, { flags: ['research-PI'] }),
        ent('p_tip2', 'M. Lowe', 'person', 72, 5),
        ent('p_tip3', 'V. Pope', 'person', 68, 5),
        ent('p_trader', 'Trader R. Quill', 'person', 86, 8),
        ent('p_friend', 'F. Day', 'person', 60, 4),
        ent('co_lab', 'Aurora Bio Lab', 'company', 30, 4),
        ent('co_desk', 'Vector Trading Desk', 'company', 40, 5),
        ent('dev_msg', 'Encrypted chat thread γ', 'device', 78, 5),
        ent('addr_pool', 'Squash club, NYC', 'address', 50, 3),
        ent('acc_trade', 'TRADING acct • 7791', 'account', 78, 6),
        ent('tx_buy', 'BUY OPT 220K', 'transaction', 84, 6),
        ent('tx_sell', 'SELL OPT 1.4M', 'transaction', 86, 6),
      ];
      const edges: Edge[] = [
        edg('p_tipper', 'co_lab', 'employs', 6),
        edg('p_tipper', 'dev_msg', 'controls', 5),
        edg('p_tip2', 'dev_msg', 'authorizes', 4),
        edg('p_tip3', 'dev_msg', 'authorizes', 4),
        edg('p_tipper', 'addr_pool', 'shares_address', 3),
        edg('p_trader', 'addr_pool', 'shares_address', 3),
        edg('p_trader', 'co_desk', 'employs', 6),
        edg('p_trader', 'acc_trade', 'controls', 8),
        edg('acc_trade', 'tx_buy', 'transfers', 8),
        edg('tx_buy', 'tx_sell', 'transfers', 7),
        edg('p_friend', 'p_trader', 'authorizes', 3),
        edg('p_tipper', 'p_trader', 'hidden_link', 6, 0.78, true, { via: 'squash club + chat' }),
      ];
      const rings: Ring[] = [
        {
          id: 'ring_tip',
          name: 'Tipper-tippee chain',
          members: ['p_tipper', 'p_tip2', 'p_tip3', 'p_trader'],
          cohesion: 0.74,
          signal: 'closed_cycle',
          risk: 'high',
        },
      ];
      const hidden: HiddenRelationship[] = [
        {
          id: 'h_tipper_trader',
          from: 'p_tipper',
          to: 'p_trader',
          via: ['addr_pool', 'dev_msg'],
          reason: 'Physical co-presence + encrypted chat correlates within trade window',
          confidence: 0.81,
        },
      ];
      const paths: TraversalPath[] = [
        {
          id: 'tp_tip_chain',
          label: 'Tipper → Trader (3 hops)',
          nodes: ['p_tipper', 'addr_pool', 'p_trader', 'acc_trade', 'tx_buy'],
          edges: [],
          hops: 4,
          why: 'Information chain from PI to trade execution',
          intent: 'evidence_chain',
        },
        {
          id: 'tp_tip_short',
          label: 'Shortest tipper → trader',
          nodes: ['p_tipper', 'dev_msg', 'p_trader'],
          edges: [],
          hops: 2,
          why: 'Encrypted chat collapses the chain to 2 hops',
          intent: 'shortest_path',
        },
      ];
      const signals: StructuralSignal[] = [
        {
          id: 'sig_time_window',
          name: 'Trade timing alignment',
          description: 'Trade entered 36 minutes after chat activity',
          intensity: 0.88,
          contributors: ['dev_msg', 'tx_buy'],
        },
        {
          id: 'sig_outsized',
          name: 'Outsized option position',
          description: 'Option size 11x trader average',
          intensity: 0.84,
          contributors: ['acc_trade', 'tx_buy'],
        },
      ];
      const stream: StreamEvent[] = [
        evt('session.start', 'Seed p_tipper'),
        evt('topology.expanded', 'Chat thread + trade desk surfaced'),
        evt('signal.surfaced', 'Trade timing alignment 0.88', { refs: ['sig_time_window'] }),
        evt('signal.surfaced', 'Outsized option position', { refs: ['sig_outsized'] }),
        evt('ring.detected', 'Tipper-tippee chain (cohesion 0.74)', {
          refs: ['ring_tip'],
          severity: 'high',
        }),
        evt('hidden.relationship', 'Tipper ↔ Trader via club + chat', {
          refs: ['h_tipper_trader'],
          severity: 'high',
        }),
        evt('path.discovered', 'Information chain to trade execution', { refs: ['tp_tip_chain'] }),
        evt('session.complete', 'Investigation complete'),
      ];
      const benchmark: BenchmarkComparison = {
        question: 'Was the option trade by R. Quill informed by material non-public information?',
        groundTruth:
          'Yes. PI Hahn passed information via encrypted chat 36 min before Quill placed an 11x-average option position.',
        results: {
          pure_llm: {
            method: 'pure_llm',
            latencyMs: 7000,
            tokens: 6500,
            confidence: 0.3,
            hops: 0,
            relationshipsFound: 0,
            relationshipsMissed: 5,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'No evidence of insider involvement is available.',
            trace: ['LLM completion only'],
            blindSpots: ['No comms graph'],
          },
          vector_rag: {
            method: 'vector_rag',
            latencyMs: 2700,
            tokens: 3700,
            confidence: 0.41,
            hops: 1,
            relationshipsFound: 1,
            relationshipsMissed: 4,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Trader and PI may share a club membership per filings.',
            trace: ['mem-snippet-9'],
            blindSpots: ['Cannot fuse comms with trade timing'],
          },
          graph_rag: {
            method: 'graph_rag',
            latencyMs: 1450,
            tokens: 2300,
            confidence: 0.91,
            hops: 4,
            relationshipsFound: 5,
            relationshipsMissed: 0,
            hiddenLinksFound: 1,
            ringsDetected: 1,
            answer:
              'Yes. PI Hahn and trader Quill share squash club presence + encrypted chat. Chat activity ends 36 min before an 11x-average option trade.',
            trace: ['shortest_path(p_tipper → p_trader)', 'time_alignment(dev_msg, tx_buy)'],
            blindSpots: [],
          },
        },
      };
      return {
        entities,
        edges,
        rings,
        hidden,
        paths,
        signals,
        stream,
        narrative: {
          headline: 'Tipper-tippee chain closes when comms + trade timing fuse.',
          body: 'No single signal exposes the breach. Graph-native fusion of communications, location and trade timing closes the loop.',
          highlights: ['timing 0.88', 'outsized 11x', 'closed cycle'],
        },
        benchmark,
        seed: 'p_tipper',
      };
    }
  );
}

function presetAdtech(): PresetSnapshot {
  return buildPreset(
    'dark_adtech',
    'Dark Ad-tech',
    'Bot fraud network sharing IP ranges, fingerprints and a fake DSP.',
    ['adtech', 'bots', 'fingerprints'],
    'violet',
    'co_dsp',
    () => {
      const entities: Entity[] = [
        ent('co_dsp', 'Fake DSP — VirtuAds', 'company', 86, 8),
        ent('co_pub_1', 'Publisher Aurora.io', 'company', 70, 5),
        ent('co_pub_2', 'Publisher Mercury.net', 'company', 68, 5),
        ent('co_pub_3', 'Publisher Helios.tv', 'company', 66, 5),
        ent('addr_dc', 'AS24940 datacenter range', 'address', 80, 6),
        ent('dev_bots_1', 'Bot device cluster α (412 fp)', 'device', 88, 7),
        ent('dev_bots_2', 'Bot device cluster β (208 fp)', 'device', 84, 6),
        ent('dev_bots_3', 'Bot device cluster γ (96 fp)', 'device', 78, 5),
        ent('p_op', 'Operator Y. Sims', 'person', 80, 6),
        ent('acc_settle', 'AD revenue acct ••• 22', 'account', 78, 6),
        ent('tx_pay', 'PAYOUT $3.1M / wk', 'transaction', 84, 6),
      ];
      const edges: Edge[] = [
        edg('p_op', 'co_dsp', 'controls', 8),
        edg('co_pub_1', 'co_dsp', 'wires_to', 6),
        edg('co_pub_2', 'co_dsp', 'wires_to', 6),
        edg('co_pub_3', 'co_dsp', 'wires_to', 6),
        edg('co_dsp', 'addr_dc', 'shares_address', 5),
        edg('co_pub_1', 'addr_dc', 'shares_address', 4),
        edg('co_pub_2', 'addr_dc', 'shares_address', 4),
        edg('co_pub_3', 'addr_dc', 'shares_address', 4),
        edg('dev_bots_1', 'co_pub_1', 'shares_device', 6),
        edg('dev_bots_2', 'co_pub_2', 'shares_device', 6),
        edg('dev_bots_3', 'co_pub_3', 'shares_device', 5),
        edg('co_dsp', 'acc_settle', 'owns', 7),
        edg('acc_settle', 'tx_pay', 'transfers', 8),
        edg('p_op', 'addr_dc', 'shares_address', 4, 0.74, true),
      ];
      const rings: Ring[] = [
        {
          id: 'ring_adfraud',
          name: 'DSP-publisher ring',
          members: ['co_dsp', 'co_pub_1', 'co_pub_2', 'co_pub_3', 'addr_dc'],
          cohesion: 0.86,
          signal: 'shared_infrastructure',
          risk: 'critical',
        },
      ];
      const hidden: HiddenRelationship[] = [
        {
          id: 'h_op_dsp',
          from: 'p_op',
          to: 'co_dsp',
          via: ['addr_dc'],
          reason: 'Operator IP overlaps with DSP datacenter range',
          confidence: 0.79,
        },
        {
          id: 'h_dsp_pubs',
          from: 'co_dsp',
          to: 'co_pub_1',
          via: ['dev_bots_1'],
          reason: 'Bot cluster signs into both DSP and publisher',
          confidence: 0.88,
        },
      ];
      const paths: TraversalPath[] = [
        {
          id: 'tp_ad_short',
          label: 'Operator → settlement',
          nodes: ['p_op', 'co_dsp', 'acc_settle'],
          edges: [],
          hops: 2,
          why: 'Operator controls DSP — settlement directly attributable',
          intent: 'shortest_path',
        },
        {
          id: 'tp_ad_flow',
          label: 'Publisher → DSP → settle',
          nodes: ['co_pub_1', 'co_dsp', 'acc_settle', 'tx_pay'],
          edges: [],
          hops: 3,
          why: 'Publisher payouts cycle back to operator-controlled account',
          intent: 'evidence_chain',
        },
      ];
      const signals: StructuralSignal[] = [
        {
          id: 'sig_ip_overlap',
          name: 'IP range overlap',
          description: 'All entities resolve into AS24940 /22 range',
          intensity: 0.86,
          contributors: ['addr_dc'],
        },
        {
          id: 'sig_fp_cluster',
          name: 'Fingerprint cluster',
          description: '716 fingerprints rotated across 3 publishers',
          intensity: 0.91,
          contributors: ['dev_bots_1', 'dev_bots_2', 'dev_bots_3'],
        },
      ];
      const stream: StreamEvent[] = [
        evt('session.start', 'Seed co_dsp'),
        evt('topology.expanded', '3 publishers + 3 bot clusters surfaced'),
        evt('signal.surfaced', 'IP range overlap 0.86', { refs: ['sig_ip_overlap'] }),
        evt('signal.surfaced', 'Fingerprint cluster 0.91', { refs: ['sig_fp_cluster'] }),
        evt('ring.detected', 'DSP-publisher ring', { refs: ['ring_adfraud'], severity: 'critical' }),
        evt('hidden.relationship', 'Operator ↔ DSP via datacenter range', {
          refs: ['h_op_dsp'],
          severity: 'high',
        }),
        evt('path.discovered', 'Publisher payouts cycle back to operator', { refs: ['tp_ad_flow'] }),
        evt('suspicion.escalated', 'p_op escalated → CRITICAL', { severity: 'critical' }),
        evt('session.complete', 'Investigation complete'),
      ];
      const benchmark: BenchmarkComparison = {
        question: 'Are these publishers independent, or part of a coordinated bot-fraud ring?',
        groundTruth:
          'Coordinated. All 3 publishers, the DSP, and the operator resolve into one AS range. 716 bot fingerprints rotate across them. Settlement returns to operator-controlled account.',
        results: {
          pure_llm: {
            method: 'pure_llm',
            latencyMs: 7100,
            tokens: 6800,
            confidence: 0.31,
            hops: 0,
            relationshipsFound: 0,
            relationshipsMissed: 5,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Publishers appear unrelated; revenue is within industry norms.',
            trace: ['LLM completion only'],
            blindSpots: ['No fingerprint clustering'],
          },
          vector_rag: {
            method: 'vector_rag',
            latencyMs: 2800,
            tokens: 4000,
            confidence: 0.42,
            hops: 1,
            relationshipsFound: 1,
            relationshipsMissed: 4,
            hiddenLinksFound: 0,
            ringsDetected: 0,
            answer: 'Some shared hosting provider mentioned in filings.',
            trace: ['hosting-doc-7'],
            blindSpots: ['Cannot resolve fingerprint cluster'],
          },
          graph_rag: {
            method: 'graph_rag',
            latencyMs: 1600,
            tokens: 2700,
            confidence: 0.95,
            hops: 3,
            relationshipsFound: 5,
            relationshipsMissed: 0,
            hiddenLinksFound: 2,
            ringsDetected: 1,
            answer:
              'Coordinated bot-fraud ring. 716 fingerprints rotate across 3 publishers; DSP and publishers resolve into AS24940. Settlement returns to operator-controlled account.',
            trace: ['ip_cluster', 'fingerprint_cluster', 'ring_detected(ring_adfraud)'],
            blindSpots: [],
          },
        },
      };
      return {
        entities,
        edges,
        rings,
        hidden,
        paths,
        signals,
        stream,
        narrative: {
          headline: 'DSP-publisher ad fraud ring exposed by IP + fingerprint topology.',
          body: '716 fingerprints rotate across 3 publishers sharing a single AS range with the DSP. Operator surfaces immediately via datacenter overlap.',
          highlights: ['IP overlap 0.86', 'fp cluster 0.91', 'operator surfaced'],
        },
        benchmark,
        seed: 'co_dsp',
      };
    }
  );
}

/* -------------------------------------------------------------------------- */
/* Registry                                                                   */
/* -------------------------------------------------------------------------- */

const _registry: PresetSnapshot[] = [
  presetShellCascade(),
  presetCardRing(),
  presetSanctions(),
  presetCryptoMixer(),
  presetMule(),
  presetProcurement(),
  presetInsider(),
  presetAdtech(),
];

export function listPresets(): PresetSnapshot[] {
  return _registry;
}

export function getPreset(id: string): PresetSnapshot | undefined {
  return _registry.find((p) => p.id === id);
}

export function defaultPreset(): PresetSnapshot {
  return _registry[0];
}
