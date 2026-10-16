"""
Format sweep:
  python run_sweep.py docling                          (folder data/raw)
  python run_sweep.py liteparse data/dataset/images
  python run_sweep.py docling data/dataset/images --resume
--resume skips files that already have an output in results/<parser>/, so an
interrupted run can be finished without redoing everything.
"""

import sys
from pathlib import Path

from eval.io_utils import save_result


def build(name: str):
    # Lazy imports: a missing library for one parser never breaks another.
    if name == "docling":
        from adapters.docling_adapter import DoclingParser
        return DoclingParser()
    if name == "liteparse":
        from adapters.liteparse_adapter import LiteParseParser
        return LiteParseParser()
    raise SystemExit(f"unknown parser '{name}' (try: docling, liteparse)")


args = [a for a in sys.argv[1:] if not a.startswith("--")]
resume = "--resume" in sys.argv
parser = build(args[0] if args else "docling")
folder = Path(args[1]) if len(args) > 1 else Path("data/raw")
files = sorted(p for p in folder.iterdir() if p.is_file() and p.name != ".gitkeep")

if resume:
    out_dir = Path("results") / parser.name
    files = [f for f in files if not (out_dir / f"{f.name}.md").exists()]
    print(f"resume: {len(files)} files left to do")

# Warm-up on one image so OCR model loading never pollutes a timing.
for f in files:
    if f.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        parser.parse(str(f))
        break

print(f"\n== {parser.name}  config: {getattr(parser, 'config', '-')}")
print(f"{'file':24}{'status':30}{'pages':>6}{'tables':>7}{'sec':>7}{'chars':>8}")
for f in files:
    print(f"-> {f.name}", flush=True)      # if the run hangs, this shows where
    r = parser.parse(str(f))
    save_result(r)
    status = "OK" if r.error is None else r.error[:28]
    print(f"{f.name:24}{status:30}{r.pages:>6}{r.tables:>7}"
          f"{r.latency_s:>7.1f}{len(r.markdown):>8}")