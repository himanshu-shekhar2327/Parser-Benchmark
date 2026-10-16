"""Does OCR add anything on a digital PDF? Compares ocr on vs off."""
from adapters.liteparse_adapter import LiteParseParser

path = "data/raw/sample.pdf"
for ocr in (True, False):
    p = LiteParseParser(ocr_enabled=ocr)
    print(f"\n== ocr_enabled={ocr}")
    for i in range(3):
        r = p.parse(path)
        print(f"  run {i+1}: {r.latency_s:.1f}s  chars={len(r.markdown)}  "
              f"tables={r.tables}  error={r.error}")
        