"""
Scores every parser's output on the seeded dataset against ground truth (v2).

Reads:   data/dataset/manifest.csv, data/dataset/ground_truth/*.json,
         results/<parser>/<image>.md
Writes:  results/dataset_scores.csv   (all parsers x images, for charts)

Columns in the report:
  header   supplier name, VAT no, invoice no, date found (VAT no digit-exact)
  tot-lbl  Subtotal/VAT/Total each followed by the right value (strict)
  tot-any  the three total values appear anywhere (found, maybe detached)
  lines    each item: description + unit price + amount present
  rows     strict: qty, unit price and amount on the SAME line as the description
  perfect  header 4/4 and tot-lbl 3/3 and all lines present
  usable   header 4/4 and tot-any 3/3 and all lines present (loose)
Reports use only images that every parser has, so the comparison is fair.
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


def nums(s):
    return [float(t.replace(",", "")) for t in NUM.findall(s)]


def has(vals, want):
    return any(abs(v - want) < 0.005 for v in vals)


def squash(s):          # like the agent's invoice-key rule: no spaces/dashes, upper
    return re.sub(r"[\s\-]", "", s).upper()


def collapse(s):
    return re.sub(r"\s+", " ", s).lower()


def flatten(s):         # drop table pipes and padding so labels sit next to values
    return re.sub(r"[\s|]+", " ", s)


def score(gt, md):
    t, c, flat = squash(md), collapse(md), flatten(md)
    header = sum([
        collapse(gt["supplier_name"]) in c,
        gt["supplier_tax_no"] in t,
        squash(gt["invoice_number"]) in t,
        squash(gt["invoice_date"]) in t,
    ])

    totals = 0
    for key, label in TOTAL_LABELS:
        for m in re.finditer(label, flat, flags=re.I):
            found = NUM.search(flat[m.end(): m.end() + 25])
            if found and abs(float(found.group().replace(",", "")) - gt[key]) < 0.005:
                totals += 1
                break

    all_vals, md_lines = nums(md), md.splitlines()
    tot_present = sum(has(all_vals, gt[k]) for k in ("subtotal", "vat", "total"))

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
    return {"header": header, "totals": totals, "tot_present": tot_present,
            "present": present, "row": row, "n_lines": n_lines,
            "perfect": int(header == 4 and totals == 3 and present == n_lines),
            "usable": int(header == 4 and tot_present == 3 and present == n_lines)}


manifest = list(csv.DictReader(open(DATA / "manifest.csv", encoding="utf-8")))
parsers = sorted(p.name for p in RESULTS.iterdir()
                 if p.is_dir() and any((p / f"{m['file']}.md").exists() for m in manifest))
gts, rows = {}, []
for m in manifest:
    gts.setdefault(m["invoice_id"], json.loads(
        (DATA / "ground_truth" / f"{m['invoice_id']}.json").read_text(encoding="utf-8")))
    for p in parsers:
        f = RESULTS / p / f"{m['file']}.md"
        if f.exists():
            rows.append({"parser": p, "file": m["file"], "template": m["template"],
                         "level": int(m["level"]),
                         **score(gts[m["invoice_id"]], f.read_text(encoding="utf-8"))})

with open(RESULTS / "dataset_scores.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# Fairness: compare only images that EVERY parser has an output for.
per_parser = {p: {r["file"] for r in rows if r["parser"] == p} for p in parsers}
common = set.intersection(*per_parser.values())
for p in parsers:
    print(f"{p}: {len(per_parser[p])}/{len(manifest)} images have output")
print(f"Reports below use the {len(common)} images present for every parser.")
rows = [r for r in rows if r["file"] in common]


def report(title, keyfn):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    print(f"\n{title}")
    print(f"{'parser':10}{'group':12}{'n':>3}{'header':>8}{'tot-lbl':>9}{'tot-any':>9}"
          f"{'lines':>7}{'rows':>6}{'perfect':>9}{'usable':>8}")
    for key in sorted(groups):
        g = groups[key]

        def share(field, per):
            return f"{100 * sum(r[field] for r in g) / sum(per(r) for r in g):.0f}%"

        def frac(field):
            return f"{100 * sum(r[field] for r in g) / len(g):.0f}%"

        print(f"{key[0]:10}{key[1]:12}{len(g):>3}"
              f"{share('header', lambda r: 4):>8}{share('totals', lambda r: 3):>9}"
              f"{share('tot_present', lambda r: 3):>9}"
              f"{share('present', lambda r: r['n_lines']):>7}"
              f"{share('row', lambda r: r['n_lines']):>6}"
              f"{frac('perfect'):>9}{frac('usable'):>8}")


report("By degradation level (templates combined)",
       lambda r: (r["parser"], f"L{r['level']}"))
report("By template and level",
       lambda r: (r["parser"], f"{r['template']}-L{r['level']}"))
print("\nAll per-image scores (before filtering) saved to results/dataset_scores.csv")