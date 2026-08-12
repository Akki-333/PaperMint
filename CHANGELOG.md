# Changelog

All notable changes to PaperMint are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-12

### Added
- **Multi-format document support**: PDF, Image (PNG/JPG with OCR), Word (DOCX), PowerPoint (PPTX)
- **Bibliography section detection**: Automatically finds "References" / "Bibliography" headers in documents
- **Citation splitting**: Multi-heuristic pipeline (numbered, blank-line, hanging indent, author boundary)
- **Citation style auto-detection**: Identifies APA, MLA, IEEE, and Chicago with confidence scores
- **Smart citation parsing**: Regex + spaCy NLP extraction of authors, title, year, journal, volume, pages, DOI
- **Confidence scoring**: Each citation gets a 0-100% extraction confidence score
- **CrossRef DOI lookup**: Fetch complete citation metadata from CrossRef API by DOI
- **Batch file processing**: Upload and process multiple documents at once
- **TextRank summarization**: Extractive document summarization using PyTextRank via spaCy
- **Export formats**: BibTeX (.bib), RIS (.ris), CSV, Excel (.xlsx), Word (.docx), PDF
- **Multi-page Streamlit UI**: Extract, Batch Processing, DOI Lookup, and About pages
- **Dark theme**: Mint-green accent on deep slate background via `.streamlit/config.toml`
- **Pydantic data models**: Type-safe Citation, Author, and ExtractionResult models
- **Test suite**: pytest tests for models, parsers, exporters, and enrichment
- **CI pipeline**: GitHub Actions workflow for linting and testing
- **Modern Python packaging**: `pyproject.toml` with PEP 621 compliance

### Removed
- Single-file `app.py` monolith architecture (replaced with `papermint/` package)
- Hardcoded regex-only extraction (3 patterns → multi-strategy pipeline)
- "First 2 sentences" summarization (replaced with TextRank)
- Dead dependencies (`requests`, `python-dotenv`, `numpy`)
- Misspelled `steamlit/` config directory (replaced with `.streamlit/`)
- `requirements.txt` and `requirements.in` (replaced with `pyproject.toml`)

### Fixed
- Streamlit theme config was never applied due to `steamlit/` folder typo
- `extract_title_from_nlp()` created spaCy doc but never used it
- `extract_year_from_nlp()` `[-4:]` slicing broke on non-year DATE entities
- DOCX/PPTX claimed in README but not accepted in file uploader
- `pytesseract` missing from dependencies
- README had placeholder `yourusername` and `your-email@example.com`
- Missing LICENSE file despite README claiming MIT License
- `st.write(f"*Title:*")` used single asterisks (italic, not bold)
