# Lahore High Court Judgements Search Engine

A legal information retrieval system for searching Lahore High Court judgments using **Boolean retrieval**, **phrase queries**, **wildcard matching**, and **TF-IDF ranking**.

This project supports both:
- a **Command-Line Interface (CLI)** for quick testing and evaluation, and
- a **Flask-based Web UI** for interactive search and document browsing.

---

## Features

- End-to-end IR pipeline: **PDF → text extraction → preprocessing → positional index → ranked retrieval**
- Boolean query operators: `AND`, `OR`, `NOT`
- Phrase search: e.g. `"writ petition"`
- Wildcard search: e.g. `judge*`
- TF-IDF ranking with optional **cosine similarity**
- Query spell suggestions and optional auto-correction
- Result snippets and full document view (text and PDF)
- Basic scraper utilities for collecting judgment PDFs

---

## Project Structure

```text
.
├── app.py                            # Main launcher (CLI/UI mode)
├── cli.py                            # Interactive command-line search
├── ui_app.py                         # Flask web application
├── query.py                          # Query parser + boolean/phrase/wildcard handling
├── tfidf.py                          # TF-IDF ranker and cosine scoring
├── clean.py                          # Tokenization, stopword removal, normalization
├── extract.py                        # PDF text extraction (PyMuPDF + pdfplumber fallback)
├── build.py                          # Builds corpus and positional index artifacts
├── lhc_scraper.py                    # Main scraper/downloader utility (argparse based)
├── crawl_and_download_judgments.py   # Minimal crawler placeholder
├── test_phrase.py                    # Unit tests for phrase query logic
├── requirements.txt                  # Python dependencies
└── data/
    ├── pdfs/                         # Source judgment PDFs
    ├── extracted/                    # Extracted .txt files
    └── index/                        # Built IR artifacts (corpus, preprocess, index, vocab)
```

---

## Retrieval Architecture

1. **Data Collection**
   - PDFs are collected into `data/pdfs` (or a fallback source folder).

2. **Text Extraction**
   - `extract.py` reads PDFs and writes plain text files to `data/extracted`.

3. **Preprocessing**
   - `clean.py` lowercases, removes punctuation, tokenizes, and removes English stopwords.

4. **Index Construction**
   - `build.py` creates:
     - `data/index/corpus.jsonl`
     - `data/index/preprocess.json`
     - `data/index/positional_index.json.gz`
     - `data/index/vocab.txt`

5. **Query Processing and Ranking**
   - `query.py` evaluates Boolean/phrase/wildcard logic.
   - `tfidf.py` scores candidate documents via TF-IDF (with optional cosine normalization).

---

## Installation

### 1) Clone repository

```bash
git clone https://github.com/Hamza-AI-07/Lahore-High-Court-Judgements-Search-Engine.git
cd Lahore-High-Court-Judgements-Search-Engine
```

### 2) Create and activate virtual environment (recommended)

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

---

## Quick Start

If your repository already contains `data/pdfs`, `data/extracted`, and `data/index`, you can run search immediately.

### Run CLI

```bash
python app.py --mode cli
```

### Run Web UI

```bash
python app.py --mode ui --port 5000
```

Open: `http://127.0.0.1:5000`

---

## Build the Index from Raw PDFs

Use this when you add/update PDFs or rebuild artifacts from scratch.

```bash
python extract.py
python build.py
```

Then launch CLI or UI.

---

## Query Syntax

### Boolean
- `bail AND murder`
- `civil OR criminal`
- `murder NOT bail`

### Phrase
- `"constitution petition"`
- `"writ petition"`

### Wildcard
- `judge*`
- `petit*`

### Combined examples
- `"writ petition" AND jurisdiction`
- `(bail OR acquittal) AND murder`

> Note: Parentheses are tokenized in the parser, but the current evaluation logic is primarily left-to-right with operator handling. Keep queries simple for most reliable behavior.

---

## Scraping / Data Collection Utilities

### Main scraper (`lhc_scraper.py`)

Example:

```bash
python lhc_scraper.py --mode list --target 1000 --out lhc_1000_documents.csv --pdf-dir data/pdfs
```

Common options:
- `--mode {list,idscan,page}`
- `--target`
- `--out`
- `--pdf-dir`
- `--skip-download`
- `--verify-links`
- timeout and filtering flags (see script arguments)

### Placeholder crawler

`crawl_and_download_judgments.py` contains a template for custom URL-based downloading and is not fully implemented.

---

## Testing

Run phrase-query unit tests:

```bash
python -m unittest test_phrase.py
```

---

## Known Limitations

- `crawl_and_download_judgments.py` is a scaffold, not a complete crawler.
- Query evaluation supports core Boolean operators, phrase, and wildcard; complex nested Boolean expressions may need parser refinement.
- Ranking uses TF-IDF and optional cosine normalization (no learning-to-rank).

---

## Future Improvements

- Better Boolean parser with explicit precedence and robust parenthesis support
- Metadata-aware filtering (judge/date/bench)
- Faster index serialization and incremental updates
- Containerized deployment (Docker)
- API layer for external integrations

---

## Tech Stack

- Python
- Flask
- NLTK
- PyMuPDF (`fitz`)
- pdfplumber
- NumPy / scikit-learn (project dependencies)

---

## Author

**Hamza AI**  
MPhil Artificial Intelligence, PUCIT

---

## License

No license file is currently included in this repository. Add a `LICENSE` file if you want to define open-source usage terms.
