#!/usr/bin/env bash
# Wire captured screenshots into README.md.
#
# Workflow:
#   1. README.md contains slot markers of the form:
#        <!-- SCREENSHOT_SLOT: <filename> · <caption> · width=<W> · framing notes: ... -->
#   2. Capture screenshots per docs/screenshots/README.md and drop them at
#      docs/screenshots/<filename>.
#   3. Run this script. It replaces each marker whose file exists with:
#        <p align="center">
#          <img src="docs/screenshots/<filename>" width="<W>" alt="<caption>">
#          <br><sub><em><caption></em></sub>
#        </p>
#   4. Slots whose file does NOT exist are left untouched (still invisible
#      HTML comments) — no broken image links ever appear in the rendered
#      README.
#
# Idempotent: re-running picks up newly added screenshots and leaves
# already-wired ones alone.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="$ROOT/README.md"
SS_DIR="$ROOT/docs/screenshots"
TMP="$(mktemp)"

if [[ ! -f "$README" ]]; then
  echo "ERROR: README.md not found at $README" >&2
  exit 1
fi

wired=0
skipped=0

python3 - "$README" "$SS_DIR" "$TMP" <<'PY'
import re, sys, os
readme_path, ss_dir, tmp_path = sys.argv[1], sys.argv[2], sys.argv[3]

text = open(readme_path, encoding="utf-8").read()

# Match:  <!-- SCREENSHOT_SLOT: filename.png · caption · width=NN% · ... -->
slot_re = re.compile(
    r"<!--\s*SCREENSHOT_SLOT:\s*"
    r"(?P<file>[A-Za-z0-9_\-]+\.png)\s*·\s*"
    r"(?P<caption>[^·]+?)\s*·\s*"
    r"width=(?P<width>[\dA-Za-z%]+)\s*·\s*"
    r"[^>]*-->"
)

wired = 0
skipped = 0
def replace(m):
    global wired, skipped
    fname = m.group("file").strip()
    caption = m.group("caption").strip()
    width = m.group("width").strip()
    abs_path = os.path.join(ss_dir, fname)
    if not os.path.isfile(abs_path):
        skipped += 1
        return m.group(0)  # leave the comment in place
    wired += 1
    rel = f"docs/screenshots/{fname}"
    # HTML-centered, captioned. No raw markdown image syntax — works
    # uniformly on GitHub, GitLab, and most markdown renderers.
    return (
        f'<p align="center">\n'
        f'  <img src="{rel}" width="{width}" alt="{caption}">\n'
        f'  <br><sub><em>{caption}</em></sub>\n'
        f'</p>'
    )

new_text = slot_re.sub(replace, text)
open(tmp_path, "w", encoding="utf-8").write(new_text)
print(f"WIRED={wired}", file=sys.stderr)
print(f"SKIPPED={skipped}", file=sys.stderr)
PY

# Only write back if something actually changed (keeps mtime stable for no-ops).
if ! cmp -s "$README" "$TMP"; then
  cp "$TMP" "$README"
  echo "README.md updated."
else
  echo "No changes (no new screenshots present)."
fi

# Count present vs total slots for the operator. `grep -c` always prints
# a number even when zero — use grep's exit code via `|| true` so we don't
# clobber the count with a fallback "0".
total_slots=$(grep -c "<!-- SCREENSHOT_SLOT:" "$README" || true)
wired_imgs=$(grep -c '<img src="docs/screenshots/' "$README" || true)
echo
echo "Slot summary:"
echo "  - ${wired_imgs:-0} image(s) wired in"
echo "  - ${total_slots:-0} slot marker(s) still pending"
echo
echo "Capture the remaining screenshots per docs/screenshots/README.md,"
echo "drop them into docs/screenshots/, and re-run this script."

rm -f "$TMP"
