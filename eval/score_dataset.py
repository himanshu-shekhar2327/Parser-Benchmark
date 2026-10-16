"""
Scores every parser's output on the seeded dataset against ground truth.

Reads:   data/dataset/manifest.csv, data/dataset/ground_truth/*.json,
         results/<parser>/<image>.md  (outputs written by run_sweep.py)
Writes:  results/dataset_scores.csv   (one row per parser x image, for charts)

Design rules:
- Money is compared as numbers, so "1,450.00" and "1450.00" both match.
- The VAT number must match digit for digit (a wrong digit = wrong supplier).
- 'row' is strict: it measures how much table STRUCTURE the parser kept.
- With few images per cell, differences of one image are noise: look at 'n'.
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

DATA = Path("data/dataset")
RESULTS = Path("results")
NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
TOTAL_LABELS = [("subtotal", r"Subtotal"), ("vat", r"VAT\s*15%"), ("total", r"\bTotal\b")]


def nums(s):                      # all numbers in a string, commas removed
    return [float(t.replace(",", "")) for t in NUM.findall(s)]


def has(vals, want):              # is `want` among `vals`? (cent tolerance)
    return any(abs(v - want) < 0.005 for v in vals)


def squash(s):                    # like the agent's inv_key: no spaces/dashes, upper
    return re.sub(r"[\s\-]", "", s).upper()


def collapse(s):                  # single spaces, lowercase
    return re.sub(r"\s+", " ", s).lower()


def score(gt, md):
    t, c = squash(md), collapse(md)
    header = sum([
        collapse(gt["supplier_name"]) in c,
        gt["supplier_tax_no"] in t,
        squash(gt["invoice_number"]) in t,
        squash(gt["invoice_date"]) in t,
    ])

    totals = 0
    for key, label in TOTAL_LABELS:
        for m in re.finditer(label, md, flags=re.I):
            found = NUM.search(md[m.end(): m.end() + 25])   # value must follow label
            if found and abs(float(found.group().replace(",", "")) - gt[key]) < 0.005:
                totals += 1
                break

    all_vals, md_lines = nums(md), md.splitlines()
    present = row = 0
    for ln in gt["lines"]:
        d = ln["description"].lower()
        others = [x["description"].lower() for x in gt["lines"] if x is not ln]
        if d in c and has(all_vals, ln["unit_price"]) and has(all_vals, ln["line_amount"]):
            present += 1
        if any(d in l.lower() and not any(o in l.lower() for o in others)
               and all(has(nums(l), v) for v in
                       (ln["quantity"], ln["unit_price"], ln["line_amount"]))
               for l in md_lines):
            row += 1

    n_lines = len(gt["lines"])
    return {"header": header, "totals": totals, "present": present, "row": row,
            "n_lines": n_lines,
            "perfect": int(header == 4 and totals == 3 and present == n_lines)}


rows = []
manifest = list(csv.DictReader(open(DATA / "manifest.csv", encoding="utf-8")))
parsers = sorted(p.name for p in RESULTS.iterdir()
                 if p.is_dir() and any((p / f"{m['file']}.md").exists() for m in manifest))
gts = {}
for m in manifest:
    gts.setdefault(m["invoice_id"], json.loads(
        (DATA / "ground_truth" / f"{m['invoice_id']}.json").read_text(encoding="utf-8")))
    for p in parsers:
        f = RESULTS / p / f"{m['file']}.md"
        if f.exists():                                   # skip images not yet run
            s = score(gts[m["invoice_id"]], f.read_text(encoding="utf-8"))
            rows.append({"parser": p, "file": m["file"], "template": m["template"],
                         "level": int(m["level"]), **s})

with open(RESULTS / "dataset_scores.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)


def report(title, keyfn):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    print(f"\n{title}")
    print(f"{'parser':10}{'group':14}{'n':>3}{'header':>8}{'totals':>8}"
          f"{'lines':>7}{'rows':>6}{'perfect':>9}")
    for key in sorted(groups):
        g = groups[key]
        pct = lambda a, b: f"{100 * sum(r[a] for r in g) / sum(r[b] for r in g):.0f}%"
        perfect = f"{100 * sum(r['perfect'] for r in g) / len(g):.0f}%"
        print(f"{key[0]:10}{key[1]:14}{len(g):>3}"
              f"{100 * sum(r['header'] for r in g) / (4 * len(g)):>7.0f}%"
              f"{100 * sum(r['totals'] for r in g) / (3 * len(g)):>7.0f}%"
              f"{pct('present', 'n_lines'):>7}{pct('row', 'n_lines'):>6}{perfect:>9}")


report("By degradation level (templates combined)",
       lambda r: (r["parser"], f"L{r['level']}"))
report("By template and level",
       lambda r: (r["parser"], f"{r['template']}-L{r['level']}"))
print("\nPer-image scores saved to results/dataset_scores.csv")