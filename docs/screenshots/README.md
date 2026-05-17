# Screenshot capture checklist

The main `README.md` reserves visual slots at 9 strategic positions. This
file is the authoritative capture script — record screenshots that match
the framing notes below, save them with the exact filenames listed, then
run `scripts/wire_screenshots.sh` to auto-replace the README slot markers
with live `<img>` tags.

The platform is currently booted at:
- Backend:  `http://localhost:8000`  (`make demo-backend` — clean empty boot)
- Frontend: `http://localhost:5173`  (`make dev-frontend`)

## Browser / capture settings

For visual consistency across the gallery:

- **Viewport:** 1440 × 900 (standard MBP 14") or 1920 × 1080
- **Color scheme:** dark (the platform is dark-themed)
- **Browser:** Chrome / Edge / Firefox · clean profile, no extensions
- **Tool:** macOS `Cmd+Shift+4` + spacebar (window mode) OR Linux
  `gnome-screenshot -w` — capture the browser content area only, NOT
  the OS chrome
- **Format:** PNG (lossless). JPG for the hero only if file size matters
- **Naming:** lower-snake-case, exactly as listed below
- **Drop location:** `docs/screenshots/<filename>.png`

## The 9 slots, in README order

### 1. `hero-investigation.png` — flagship

**Section:** below the hero, above "Why this exists"
**What to capture:** the `/investigate` workstation page mid-stream
during an investigation against an ACTIVATED sample environment.
Show all four panels at once if possible:
1. Graph canvas (cytoscape) with a fraud-ring cluster expanded
2. Suspect rail (left or right)
3. Streaming timeline at the bottom
4. The custom-investigation input bar visible

Cinematic frame — this is the FIRST visual a judge sees. Wait for the
graph to settle, then capture.

**Suggested query:** `identify members of fraud ring FR-001`
**Aspect:** 16:9 landscape · width=`95%`

---

### 2. `graphrag-vs-vectorrag.png` — thesis centerpiece

**Section:** inside "The GraphRAG advantage, demonstrated"
**What to capture:** the `/benchmark` page in **Scenario** tab (the
3-lane side-by-side walkthrough). Capture at phase 3 or 4 when GraphRAG
is highlighted and the structural-edge count is visible.

If the scenario tab is too synthetic-feeling, alternative: open the
`/investigate` page, press `4` to switch to the **compare** right-tab,
and capture the 3-pipeline side-by-side comparison panel.

**Aspect:** 16:9 landscape · width=`95%`

---

### 3. `benchmark-evidence.png` — measured run

**Section:** inside "B. 3-pipeline measured run"
**What to capture:** the `/benchmark` page on the **Evidence** tab,
showing `RealBenchmarkPanel` with:
- Structural verdict bar (20/20 vs 0/20)
- Quantitative comparison table (token / latency / sources)
- Disclosure block visible

**Aspect:** 16:9 landscape · width=`90%`

---

### 4. `lifecycle-empty.png` — empty-state landing

**Section:** inside "Operational lifecycle" → "What lives at each state"
**What to capture:** the `/sources` page in `empty` activation state
(default after `make demo-backend`). Show all 5 readiness gates closed
in amber/rose with the `"no environment activated · click Launch Sample
Ecosystem"` reasons visible, AND the Launch button prominent.

**Aspect:** 16:9 landscape · width=`90%`

---

### 5. `lifecycle-activated.png` — sample activated

**Section:** directly after `lifecycle-empty.png`
**What to capture:** the same `/sources` page IMMEDIATELY after clicking
"Launch Sample Fraud Ecosystem" — readiness gates green, vertex counts
populated, `activation: sample` chip visible.

Pair with the empty one — these two should read as a before/after.

**Aspect:** 16:9 landscape · width=`90%`

---

### 6. `ingestion-promote.png` — ecosystem upload

**Section:** inside "Sources / Ingestion"
**What to capture:** the `/sources` page with the upload pane open and:
- 2-3 recently uploaded files visible in the "recent uploads" list
- Each with a green "schema · Person/Company/edge" chip
- One file showing the promote button active

You may need to upload `custom_persons.csv` / `custom_companies.csv` /
`custom_account_device_edges.csv` from `/tmp/sni_test_eco/` (or recreate
them locally) to populate the list.

**Aspect:** 16:9 landscape · width=`90%`

---

### 7. `investigation-ring.png` — ring discovery

**Section:** inside "GraphRAG retrieval internals"
**What to capture:** the `/investigate` workstation after running
`identify members of fraud ring FR-001`. Focus the capture on the
RIGHT panel — Report tab — showing:
- 5 suspects (1 FraudRing + 4 promoted ring members)
- Ring connections section with 8 `ACCOUNT_MEMBER_OF_RING` entries
- Structural signals chip

The graph canvas on the left should show the FR-001 hub with edges
fanning out to accounts.

**Aspect:** 16:9 landscape · width=`90%`

---

### 8. `degraded-mode.png` — offline trust

**Section:** inside "Evaluator resilience"
**What to capture:** the `/sources` page after killing TigerGraph
connectivity (or restarting backend with bad creds: `make demo-backend`
with `TIGERGRAPH_HOST=https://invalid.tg.io`). Show:
- TG-OFF pill in the TopBar
- Readiness gates in degraded state with the new operator-friendly
  reasons (`degraded · entity ranking + dossier available against local CSV`)
- Activation chip still showing the activated environment

**Aspect:** 16:9 landscape · width=`90%`

---

### 9. `architecture-diagram.png` — Mermaid fallback (optional)

**Section:** below the Mermaid architecture block
**What to capture:** export the Mermaid diagram from the rendered README
as a static PNG. Two options:
- Use https://mermaid.live, paste the diagram source, export as PNG
- OR render the README in VS Code / Obsidian and screenshot the diagram

This is a **fallback for markdown renderers that don't render Mermaid**.
Skip if you're confident the target audience renders Mermaid (GitHub
does).

**Aspect:** 4:3 or 16:9 · width=`85%`

---

## After capture

```bash
# Drop files in docs/screenshots/, then:
bash scripts/wire_screenshots.sh

# That will replace the slot markers in README.md with live <img> tags.
# Verify with:
grep -c "img src=\"docs/screenshots" README.md
# Should match the number of captured files.
```

If you skip a slot (e.g. you only want 3 screenshots, not 9), the wire-in
script leaves un-captured slots as markdown comments — they stay invisible
in rendered output. No broken images, ever.
