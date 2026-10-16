# Parser-Benchmark

Benchmark of document parsers (Docling, LiteParse, LlamaParse, Azure Document
Intelligence, AWS Textract) across formats: PDF, DOCX, XLSX, PPTX, HTML, images.

## Status
- [x] Common adapter contract
- [x] Docling adapter + format sweep
- [ ] LiteParse, LlamaParse, Azure, AWS adapters
- [ ] Metrics, router, Streamlit app

## Setup
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env      # then add keys for the cloud parsers

## Run
    python make_samples.py      # fake invoices into data/raw/ (run once)
    python run_sweep.py docling
    python eval/check_samples.py