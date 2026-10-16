"""
Generic format sweep:  python run_sweep.py docling
                       python run_sweep.py liteparse
Same loop, same logging, same checker for every parser. That sameness is what
makes the comparison fair.
"""

import sys
from pathlib import Path

from eval.io_utils import save_result


def build(name: str):
    # Imports are lazy so a missing library for one parser never breaks another.
    if name == "docling":
        from adapters.docling_adapter import DoclingParser
        return DoclingParser()
    if name == "liteparse":
        from adapters.liteparse_adapter import LiteParseParser
        return LiteParseParser()
    raise SystemExit(f"unknown parser '{name}' (try: docling, liteparse)")


parser = build(sys.argv[1] if len(sys.argv) > 1 else "docling")
folder = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/raw")
files = sorted(p for p in folder.iterdir() if p.is_file() and p.name != ".gitkeep")

# Warm-up on one image so OCR model loading never pollutes a timing.
for f in files:
    if f.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        parser.parse(str(f))
        break

print(f"\n== {parser.name}  config: {getattr(parser, 'config', '-')}")
print(f"{'file':24}{'status':30}{'pages':>6}{'tables':>7}{'sec':>7}{'chars':>8}")
for f in files:
    r = parser.parse(str(f))
    save_result(r)
    status = "OK" if r.error is None else r.error[:28]
    print(f"{f.name:24}{status:30}{r.pages:>6}{r.tables:>7}"
          f"{r.latency_s:>7.1f}{len(r.markdown):>8}")