"""Format sweep v2: a discarded warm-up pass, then the timed pass."""

from pathlib import Path

from adapters.docling_adapter import DoclingParser
from eval.io_utils import save_result

parser = DoclingParser()
files = sorted(p for p in Path("data/raw").iterdir()
               if p.is_file() and p.name != ".gitkeep")

# Warm-up: OCR models are downloaded and loaded lazily on the FIRST image.
# Parse one image and throw the result away so it cannot pollute any timing.
for f in files:
    if f.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        parser.parse(str(f))
        break

print(f"\n{'file':24}{'status':28}{'pages':>6}{'tables':>7}{'sec':>7}{'chars':>8}")
for f in files:
    r = parser.parse(str(f))
    save_result(r)
    status = "OK" if r.error is None else r.error[:26]
    print(f"{f.name:24}{status:28}{r.pages:>6}{r.tables:>7}"
          f"{r.latency_s:>7.1f}{len(r.markdown):>8}")