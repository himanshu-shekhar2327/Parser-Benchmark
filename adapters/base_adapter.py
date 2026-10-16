"""
Base contract for every parser adapter.

WHY THIS FILE EXISTS
Each parser (Docling, Azure, AWS, ...) has a different API and returns a
different data structure. If the benchmark talked to them directly, every
metric would need five code paths and comparisons would be unfair.

Instead, each parser gets a thin "adapter" that:
  1. accepts a file path
  2. returns the SAME ParseResult shape

This is the "template method" pattern: the base class owns the shared logic
(timing, error handling, format checks), and each adapter only implements
the vendor-specific part in _parse().
"""
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Reads the .env file in the project root into environment variables.
# This is how API keys reach the adapters without being hard-coded.
load_dotenv()


def count_markdown_tables(markdown: str) -> int:
    """Count Markdown table separator rows outside fenced code blocks."""
    table_count = 0
    fence_char = ""
    fence_length = 0

    for line in markdown.splitlines():
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            marker, trailing = fence.groups()
            if fence_char:
                if (marker[0] == fence_char and len(marker) >= fence_length
                        and not trailing.strip()):
                    fence_char = ""
                    fence_length = 0
                continue
            if marker[0] != "`" or "`" not in trailing:
                fence_char = marker[0]
                fence_length = len(marker)
            continue

        if fence_char:
            continue

        cells = line.strip().strip("|").split("|")
        if len(cells) >= 2 and all(
                re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells):
            table_count += 1

    return table_count


@dataclass
class ParseResult:
    """Standard output of every parser. All metrics are computed from this."""
    parser: str                 # which parser produced this result
    file: str                   # input file path
    markdown: str = ""          # extracted content, normalised to Markdown
    tables: int = 0             # number of tables detected
    pages: int = 0              # pages processed (also used to track free-tier usage)
    latency_s: float = 0.0      # wall-clock time for the parse call
    cost_usd: float = 0.0       # 0 on free tier; estimated at paid rates in analysis
    error: str | None = None    # None means success. Failures are DATA, not crashes:
    config: str = ""            # settings used, e.g. "ocr=True,tables=True"                           # the failure rate is itself a benchmark metric.


class BaseParser(ABC):
    name: str = ""                       # short id used in result tables
    supported: set[str] = set()          # file extensions this parser can open
    requires_env: list[str] = []         # env vars (API keys) needed to run

    def is_configured(self) -> bool:
        """True if all required keys are present. Local parsers need none."""
        return all(os.getenv(var) for var in self.requires_env)

    def supports(self, path: str) -> bool:
        """Check the file extension against this parser's supported formats."""
        return Path(path).suffix.lower() in self.supported

    def parse(self, path: str) -> ParseResult:
        """
        Public entry point. Never raises: every outcome becomes a ParseResult,
        so one bad file cannot stop a whole benchmark run.
        """
        # Skip cleanly instead of crashing when we can't run this parser.
        if not self.is_configured():
            return ParseResult(self.name, str(path), error="not_configured")
        if not self.supports(path):
            return ParseResult(self.name, str(path), error="unsupported_format")

        start = time.perf_counter()  # perf_counter is the right clock for timing
        try:
            result = self._parse(path)
        except Exception as e:
            result = ParseResult(self.name, str(path),
                                 error=f"{type(e).__name__}: {e}")
        result.latency_s = time.perf_counter() - start
        return result

    @abstractmethod
    def _parse(self, path: str) -> ParseResult:
        """Vendor-specific logic. Each adapter implements only this method."""
        ...