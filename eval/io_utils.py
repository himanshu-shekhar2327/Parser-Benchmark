"""Saves every parse result so quality can be inspected and metrics computed later."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

RESULTS = Path("results")


def save_result(r) -> None:
    # 1) The Markdown itself, for eyeballing: results/<parser>/<file>.md
    out_dir = RESULTS / r.parser
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{Path(r.file).name}.md").write_text(r.markdown, encoding="utf-8")

    # 2) One JSON line per run with metadata (no full text, to keep it small).
    record = asdict(r)
    md = record.pop("markdown")
    record["chars"] = len(md)
    # Same hash across repeated runs = deterministic output.
    record["md_sha1"] = hashlib.sha1(md.encode("utf-8")).hexdigest()
    with open(RESULTS / "runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")