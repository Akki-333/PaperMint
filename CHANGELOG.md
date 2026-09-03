# Changelog

All notable changes to PaperMint are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-03

A rebuild of the architecture, the parsing engine and the interface. The public
signatures of `detect_bibliography_section`, `split_citations`, `parse_citation`,
`detect_style`, `summarize` and every exporter are unchanged, so the original
48 tests still pass untouched.

### Added

#### Architecture
- **`papermint/pipeline.py`** — `PipelineService` orchestrating extract,
  characterise, parse and summarise, with a `PipelineStage` enum, per-stage
  progress callbacks, `PipelineOptions`, and `process_batch()` with per-file
  error isolation.
- **`papermint/errors.py`** — the full `PaperMintError` hierarchy. Each error
  carries a reader-facing message, an optional `remedy`, and a stable `kind`.
- **`papermint/extractors/registry.py`** — resolves an extractor by MIME type
  with an extension fallback, replacing the `if/elif` chain duplicated in both
  Streamlit pages.
- **`papermint/cli.py`** — headless entry point running the identical service.
  Installed as the `papermint` console script.
- **`papermint/ui/navigation.py`** — routes built once so any page can link to
  any other.

#### Parsing
- **`papermint/parsers/text_normalizer.py`** — ligature folding, de-hyphenation
  across line breaks, dash and quote unification, page-number and
  running-header removal, and sentence counting that is not fooled by author
  initials or DOIs.
- `characterize_document()` returning a `DetectionOutcome` with the document
  kind, the detection method, the body text, a confidence score, and
  human-readable reasoning the interface displays.
- `score_citation()` exposed publicly so confidence can be recomputed after a
  manual correction.
- Page counts, per-page text and non-fatal warnings on every extractor.

#### Models
- `DocumentKind`, `DetectionMethod`, `ConfidenceBand`, `DocumentStats`,
  `BatchResult`, `BatchFileResult`.
- Display properties on `Citation`: `display_title`, `short_author_string`,
  `venue`, `locator`, `doi_url`, `confidence_band`, `needs_review`,
  `missing_fields`, `is_parsed`.

#### Interface
- **`papermint/ui/theme.py`** — every colour, type step, space step, radius and
  duration as one token set, emitted as CSS custom properties.
- **`papermint/ui/icons.py`** — 21 inline SVG icons on `currentColor`,
  replacing emoji throughout.
- **`papermint/ui/html.py`** — `esc()`, `render()` over `st.html()`, `clamp()`,
  `dot_join()`.
- **`papermint/ui/components/primitives.py`** — page headers, section headers,
  statistic tiles, chips, notices, empty states, definition lists, tile grids.
- Inline citation editor for all eight fields, with confidence rescored on save.
- Per-card BibTeX view, search across five fields, six sort orders, a "Needs
  review" filter, and pagination beyond 25 entries.
- Export preview for the text formats, and filenames derived from the source
  document.

#### Testing
- `tests/test_architecture.py` (223 checks) enforcing the layering and coding
  rules by parsing every module with `ast`.
- `tests/test_pipeline.py` (18) covering orchestration, batch isolation, the
  registry and the CLI.
- `tests/test_normalization.py` (26) covering text repair and the parser guards.
- `tests/test_ui.py` (30) covering markup, escaping, components, and rendering
  all five pages through `streamlit.testing.v1.AppTest`.
- Total: 345 tests, up from 48. No test makes a network call.

### Changed

- **Both Streamlit pages now call `PipelineService`.** `extract.py` replaced six
  inline domain calls plus a MIME dispatch with one service call; `batch.py`
  likewise.
- **Results are cached in session state** against a digest of the file and the
  options, so typing in the search box no longer reprocesses the document.
- **The density scan walks backwards to a block boundary** instead of returning
  the trailing half of the document, so the closing paragraphs of a paper are no
  longer parsed as citations.
- **The references heading match takes the last occurrence**, so a table of
  contents entry cannot win over the real section.
- **Every split is validated before acceptance**, and continuation fragments are
  merged, so prose is no longer shredded into fake entries.
- **Author surnames** now match particles, hyphens, apostrophes and all-caps
  forms.
- **spaCy is optional.** The summariser falls back to a deterministic regex
  segmenter, and a CI job runs without the model to keep that path exercised.
- **`ruff` configuration is explicit.** Fifteen rule families selected in
  `pyproject.toml` rather than inherited from the installed version's defaults.
- CI split into lint, test across three Python versions, and a separate job with
  the NLP extra installed.
- `.streamlit/config.toml` realigned to the design tokens.

### Fixed

- **Uploads returned zero bytes on every rerun.** `UploadedFile` is a `BytesIO`
  whose cursor persists, so `.read()` worked once. Every later interaction read
  nothing and the page reported that no text could be extracted. Now
  `getvalue()`.
- **The pipeline stepper stacked four progress bars.** Its render function was
  called once per stage, appending a new widget each time. It now draws into a
  single placeholder.
- **Three-or-more-author APA citations lost their authors.** The regex captured
  `"C. D., Brown, E."` as one author's given name.
- **A date span in a title was read as a page range.** `1700-2000` became
  `pp. 1700-2000`.
- **Unescaped document text corrupted cards.** A title containing an angle
  bracket ate the rest of the card.
- **The export panel's wrapper never wrapped anything.** An opening `<div>` in
  one `st.markdown` call and its closing tag in another are separate DOM nodes.
- **Sentence counts were inflated** by counting every period, including author
  initials and DOIs.
- **Page counts were always zero** although `extract_text_by_page` existed.
- **Domain-layer logging went nowhere.** No handler was ever configured.
- **The About page rendered its Mermaid diagram as a grey code block**, because
  every line carried four spaces of indentation.
- **CrossRef network failures were indistinguishable from a missing DOI.**
- **`--force-parse` reported the wrong document kind** for annotated
  bibliographies.

### Removed

- `pytextrank`, `bibtexparser` and `httpx` from dependencies. None were imported
  anywhere in the codebase.
- `spacy.cli.download()` from the request path, which stalled a user-facing page
  for minutes with no feedback.
- Named entity recognition from author extraction, which reported place names
  and common nouns as people.
- Gradient text, emoji iconography and hover-lift animation from the interface.
- Silent `return ""` on extractor failure, replaced by typed exceptions.

---

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
