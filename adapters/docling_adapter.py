"""
Docling adapter (local, open source, no API key).

Design notes:
- The converter is built ONCE and warmed up in __init__, so parse() latency
  measures only parsing, never model loading (startup is reported separately).
- OCR and table-structure switches are constructor arguments so the benchmark
  can compare a default config with a faster one. The settings used are stored
  in every ParseResult.config for reproducibility.
- These options apply to PDF input. Images and Office files use Docling's own
  defaults for their formats (OCR on for images).
"""

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from .base_adapter import BaseParser, ParseResult, count_markdown_tables


class DoclingParser(BaseParser):
    name = "docling"
    supported = {".pdf", ".docx", ".pptx", ".xlsx", ".html",
                 ".png", ".jpg", ".jpeg", ".tiff"}
    requires_env = []  # local parser: nothing needed

    def __init__(self, do_ocr: bool = True, do_table_structure: bool = True):
        opts = PdfPipelineOptions()
        opts.do_ocr = do_ocr                          # OCR for scanned pages
        opts.do_table_structure = do_table_structure  # table-structure model

        self.config = f"ocr={do_ocr},tables={do_table_structure}"
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
        # Load models now so startup cost is not hidden inside the first parse.
        if hasattr(self.converter, "initialize_pipeline"):
            self.converter.initialize_pipeline(InputFormat.PDF)

    def _parse(self, path: str) -> ParseResult:
        doc = self.converter.convert(path).document
        markdown = doc.export_to_markdown()      # normalise to the shared format
        return ParseResult(
            parser=self.name,
            file=str(path),
            markdown=markdown,
            tables=count_markdown_tables(markdown),  # same counter as every parser
            pages=len(doc.pages),                    # may be 0 for unpaginated formats
            config=self.config,
        )