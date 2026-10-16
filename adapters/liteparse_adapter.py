"""
LiteParse adapter (local, open source, Rust core, no API key).

How it works, as I understand the docs:
  PDF     -> parsed directly: text layer + the position of every text item
  Images  -> converted to PDF, then OCR'd with Tesseract
  Office  -> converted to PDF through LibreOffice first (LibreOffice must be
             installed, otherwise parse() returns an error naming it)
Unlike Docling there are no AI layout or table models here, so I expect it to
be faster but possibly weaker on complex tables. That is a hypothesis to test.
"""

from liteparse import LiteParse

from .base_adapter import BaseParser, ParseResult, count_markdown_tables


class LiteParseParser(BaseParser):
    name = "liteparse"
    # HTML is not in LiteParse's documented format list, so it is excluded.
    supported = {".pdf", ".docx", ".pptx", ".xlsx",
                 ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp", ".gif"}
    requires_env = []  # local parser: nothing needed

    def __init__(self, ocr_enabled: bool = True, dpi: int = 300):
        # Settings are explicit and stored in every result, so the blog can say
        # exactly what ran. DPI controls how finely images are rendered for OCR;
        # it is a variable worth testing on poor scans.
        self.config = f"ocr={ocr_enabled},dpi={dpi},format=markdown"
        self.parser = LiteParse(
            output_format="markdown",   # same output type as Docling
            ocr_enabled=ocr_enabled,
            dpi=dpi,
        )

    def _parse(self, path: str) -> ParseResult:
        result = self.parser.parse(path)
        markdown = result.text           # rendered Markdown lives on .text
        return ParseResult(
            parser=self.name,
            file=str(path),
            markdown=markdown,
            tables=count_markdown_tables(markdown),  # same counter as Docling
            pages=len(result.pages),
            config=self.config,
        )