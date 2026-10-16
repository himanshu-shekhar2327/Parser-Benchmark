"""Smoke test v2: separates model-load time from per-file parse time."""
import sys
import time
from adapters.docling_adapter import DoclingParser

path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/sample.pdf"

# 1) Model loading cost, measured on its own.
t0 = time.perf_counter()
parser = DoclingParser()
print(f"init (model load): {time.perf_counter() - t0:.1f}s")

# 2) Parse the same file 3 times. The first call may still do lazy setup,
#    so report all three instead of averaging blindly.
for i in range(3):
    r = parser.parse(path)
    per_page = r.latency_s / max(r.pages, 1)
    print(f"run {i+1}: {r.latency_s:.1f}s  ({per_page:.2f}s/page)  "
          f"pages={r.pages} tables={r.tables} error={r.error}")