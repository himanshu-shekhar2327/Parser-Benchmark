"""
Row-integrity check (strict). A number is only useful on an invoice if it is
still attached to its row. For each expected line item we require ONE output
line that contains:
  - the item description
  - its quantity, unit price and amount (compared numerically)
  - and NOT the other item's description (otherwise association is ambiguous,
    e.g. a whole table flattened onto a single line)
Totals pass when each label is followed by its value on the same line.
Empty outputs (errors / unsupported) are shown as N/A, not as 0%.
"""

import re
from pathlib import Path

ITEMS = [("USB cable", 5, 120.0, 600.0), ("Desk lamp", 2, 350.0, 700.0)]
TOTALS = [("Subtotal", r"Subtotal", 1300.0),
          ("VAT",      r"VAT\s*15%", 195.0),
          ("Total",    r"\bTotal\b", 1495.0)]
NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def nums(s: str) -> list[float]:
    return [float(t.replace(",", "")) for t in NUM.findall(s)]


def has(vals: list[float], want: float) -> bool:
    return any(abs(v - want) < 0.005 for v in vals)


def check(md: str):
    lines = md.splitlines()
    item_ok, item_bad = 0, []
    for desc, qty, unit, amt in ITEMS:
        others = [d.lower() for d, *_ in ITEMS if d != desc]
        passed = any(
            desc.lower() in ln.lower()
            and not any(o in ln.lower() for o in others)
            and all(has(nums(ln), v) for v in (qty, unit, amt))
            for ln in lines
        )
        item_ok += passed
        if not passed:
            item_bad.append(desc)

    tot_ok, tot_bad = 0, []
    for name, label, value in TOTALS:
        passed = False
        for ln in lines:
            for m in re.finditer(label, ln, flags=re.I):
                tail = ln[m.end(): m.end() + 25]       # value must follow the label
                found = NUM.search(tail)
                if found and abs(float(found.group().replace(",", "")) - value) < 0.005:
                    passed = True
        tot_ok += passed
        if not passed:
            tot_bad.append(name)
    return item_ok, item_bad, tot_ok, tot_bad


print(f"{'parser':10}{'file':24}{'items':>7}{'totals':>8}   broken")
for p in sorted(Path("results").glob("*/invoice*.md")):
    md = p.read_text(encoding="utf-8")
    name = p.name[:-3]
    if not md.strip():
        print(f"{p.parent.name:10}{name:24}{'N/A':>7}{'N/A':>8}   (empty output)")
        continue
    io, ib, to, tb = check(md)
    print(f"{p.parent.name:10}{name:24}{io:>4}/{len(ITEMS)}{to:>6}/{len(TOTALS)}   "
          f"{', '.join(ib + tb) or '-'}")
    