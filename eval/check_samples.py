"""
Expected-fact check for the generated sample invoices (works for ANY parser).

For each results/<parser>/invoice*.md it asks: did the output contain the
identifiers, names and money amounts we know are in the source file?
Text facts need an exact match, because one wrong digit in an invoice number
or amount breaks the real pipeline's duplicate and arithmetic checks.
Money is compared numerically, so 600, 600.0 and 600.00 all count as equal.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

TEXT = ["INV-0001", "4000000001", "05/10/2026", "USB cable", "Desk lamp"]
MONEY = [120, 600, 350, 700, 1300, 195, 1495]
EXTRA_TEXT = {                      # file-specific traps
    "invoice.xlsx": ["HIDDEN-SHEET-MARKER"],   # does it read hidden sheets?
    "invoice.pptx": ["NOTES-MARKER"],          # does it read speaker notes?
}


def numbers_in(text: str) -> set[float]:
    vals = set()
    for tok in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text):
        vals.add(float(tok.replace(",", "")))
    return vals


print(f"{'parser':10}{'file':24}{'text':>7}{'money':>7}   missing")
for md_path in sorted(Path("results").glob("*/invoice*.md")):
    parser = md_path.parent.name
    src_name = md_path.name[:-3]                    # strip trailing ".md"
    text = md_path.read_text(encoding="utf-8")
    want_text = TEXT + EXTRA_TEXT.get(src_name, [])
    got_text = [t for t in want_text if t.lower() in text.lower()]
    nums = numbers_in(text)
    got_money = [m for m in MONEY if any(abs(n - m) < 0.005 for n in nums)]
    missing = [t for t in want_text if t not in got_text] + \
              [str(m) for m in MONEY if m not in got_money]
    print(f"{parser:10}{src_name:24}"
          f"{len(got_text)}/{len(want_text):>2}  {len(got_money)}/{len(MONEY):>2}   "
          f"{', '.join(missing) or '-'}")

# Determinism: the same file parsed twice should give an identical hash.
print("\nDeterminism (same md_sha1 across runs?):")
hashes = defaultdict(set)
log = Path("results/runs.jsonl")
if log.exists():
    for line in log.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        hashes[(rec["parser"], Path(rec["file"]).name)].add(rec["md_sha1"])
for (p, f), hs in sorted(hashes.items()):
    print(f"  {p:10}{f:24}{'stable' if len(hs) == 1 else 'DIFFERS'}")