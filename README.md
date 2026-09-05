# PaperMint

**Turn unstructured academic documents into structured, exportable bibliographic records.**

PDF, PNG, JPEG, Word and PowerPoint go in. BibTeX, RIS, CSV, Excel, Word and PDF
come out, with a document summary and optional CrossRef enrichment.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-34D399.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-34D399.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-345%20passing-34D399.svg)](tests/)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-34D399.svg)](https://streamlit.io)

---

## The problem

Researchers spend hours retyping references. They copy out of PDFs, wrestle with
BibTeX, and check every field by hand.

PaperMint reads the document, isolates its bibliography, parses each entry into
structured fields, and exports the lot. What separates it from a regex script is
that **it tells you how much of each entry it could actually read**, and it never
fills a gap with a guess.

---

## The governing principle: honesty over completeness

A field that cannot be read confidently is left empty and reported as missing. It
is never filled with a plausible-looking fragment. A document with no bibliography
produces zero citations and says so.

This is not a slogan. It shapes every parser:

- A title candidate is **rejected** when it is a page locator, an author list, a
  DOI, a URL, a publisher, or shorter than two real words.
- A page range is **rejected** when it is a span of two four-digit calendar years,
  which is how `1700-2000` in a book title used to become page numbers.
- General-purpose named entity recognition is **not used** for author extraction.
  It reports place names and common nouns as people, and a fabricated author is
  worse than a missing one.

Every extractor proposes candidates in descending order of reliability and
validates each one before accepting it. A rejected candidate leaves the field
empty, which the interface renders honestly as *missing*.

---

## What it does

| | |
|:---|:---|
| **Reads five formats** | PDF, PNG and JPEG through OCR, Word, PowerPoint |
| **Repairs the text first** | Folds ligatures, rejoins words split across a line break, unifies six dash characters, strips page numbers and running headers |
| **Finds every bibliography** | Not just the last References heading: a file with a list per chapter, separate primary and secondary sources, or a further-reading list after the references yields all of them. An appendix or index between two lists stays in the body |
| **Reads and writes four styles** | APA, MLA, IEEE and Chicago are recognised on the way in, with a confidence score, and rendered on the way out as a finished reference list |
| **Validates every field** | A candidate that is really a page range, an author list or a publisher is rejected rather than shown as a title |
| **Scores what it found** | Every entry reports field coverage; anything below 50% is flagged for review |
| **Lets you fix it** | Inline editor on every card; the score updates to match what you entered |
| **Invents nothing** | A document with no bibliography produces no citations, and says so |
| **Exports six formats** | BibTeX, RIS, CSV, Excel, Word, PDF |
| **Explains the styles** | Each style's principle, element order and punctuation, with MLA's nine core elements set out in full |
| **Keeps your place** | Moving between pages never discards your document, your filters or your corrections |
| **Runs headless** | The same engine works from a terminal with no Streamlit |

---

## Quick start

### Prerequisites

- Python 3.10 or newer
- Tesseract OCR, only if you want to read scanned images

### Install

```bash
git clone https://github.com/Akki-333/PaperMint.git
cd PaperMint

python -m venv .venv
.\.venv\Scripts\activate        # Windows
source .venv/bin/activate       # macOS and Linux

pip install -e .
```

Tesseract, for image OCR:

- **Windows** — [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS** — `brew install tesseract`
- **Linux** — `sudo apt-get install tesseract-ocr`

Better sentence segmentation in summaries is optional. Without it, a
deterministic segmenter is used instead:

```bash
pip install -e ".[nlp]"
python -m spacy download en_core_web_sm
```

### Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Command line

The engine imports nothing from Streamlit, so it also runs headless:

```bash
papermint paper.pdf                                  # BibTeX to stdout
papermint *.pdf --format ris --out references.ris    # merged RIS file
papermint catalogue.pdf --force-parse                # treat it all as a bibliography
papermint paper.pdf --json                           # full structured result
```

Exit codes: `0` clean, `1` at least one file failed, `2` nothing readable.

---

## Using the app

**Document analyzer.** Upload one file. You get a notice explaining what kind of
document it is and how the bibliography was found, four headline numbers, and
three tabs: References, Summary and Source text. Search, sort and filter the
references, correct any of them inline, then export.

**Batch processing.** Upload many. Each file is processed independently, so a
corrupt PDF is reported against itself instead of aborting the run. Export one
merged bibliography.

**Style studio.** Takes the references you just extracted, or one you paste,
and sets them as a finished reference list in APA, MLA, IEEE or Chicago, with
the same entry shown four ways for comparison. Beside it is an account of what
that style is for and how an entry is built. Nothing is invented: an element
your source never supplied is left out and named.

Nothing on any page is discarded when you navigate away. Your document, your
search, your sort order and your corrections are all still there when you come
back.

---

## How a document is read

`PipelineStage` defines the sequence, and the interface's stepper is driven from
that same enum, so the displayed steps cannot drift from the executed ones.

```
EXTRACT ──▶ CHARACTERIZE ──▶ PARSE ──▶ SUMMARIZE ──▶ result
```

### 1 — EXTRACT

`resolve_extractor()` picks a decoder by MIME type, falling back to the filename
extension. The decoder returns text, a real page count and any non-fatal
warnings. Failures raise `CorruptedDocumentError`, `UnsupportedFileTypeError` or
`OcrUnavailableError` rather than returning an empty string.

The text is then normalised, and the repairs matter more than any parsing
heuristic:

| Problem in raw PDF text | Repair |
|:---|:---|
| Typographic ligatures | Unicode NFKC folding |
| Soft hyphens, zero-width characters | Removed |
| Words split across a line break | Rejoined, lowercase to lowercase only |
| Six different dash characters | Mapped to the ASCII hyphen |
| Curly quotes | Mapped to straight quotes |
| Bare page numbers on their own line | Dropped |
| Repeated running headers and footers | Dropped by repetition frequency |

### 2 — CHARACTERIZE

`characterize_document()` returns a `DetectionOutcome` carrying the bibliography
block, the remaining body text, the detection method, the document kind, a
confidence score and human-readable reasoning the interface displays.

Strategies run in descending order of reliability:

1. **Force-parse** from the reader — the whole document is the bibliography.
2. **The first line declares it** a bibliography.
3. **References headings** on lines of their own. Every heading opens a candidate
   block, bounded below by the next heading of any kind, including an appendix,
   index or glossary heading, and trimmed at any sustained run of narrative
   prose. The block under the **last** heading is kept on the strength of the
   heading alone, so a table of contents entry still cannot win; every earlier
   block must be dense enough to read as references before it joins them.
4. **A backwards density scan** from the end of the document, tolerating up to
   four consecutive continuation lines, stopping at the first sustained run of
   prose. The selected block must itself pass the density check.
5. **Nothing found** — the document is non-academic, and no citations are
   produced.

### 3 — PARSE

`split_citations()` tries numbered prefixes, blank lines, hanging indent and
author boundaries, **validating each candidate split before accepting it** and
merging continuation fragments. A split that yields mostly non-citation fragments
is rejected in favour of the next strategy, which is what stops prose being
shredded into fake entries. Author boundaries recognise surname particles
(`van der Berg`, `de la Cruz`, `von Neumann`), hyphens, apostrophes and all-caps
forms.

`detect_style()` scores APA, MLA, IEEE and Chicago signals. `parse_citation()`
extracts eight fields — title, authors, year, journal, volume, issue, pages, DOI,
plus publisher and URL — proposing and validating each. Every entry is then
scored for field coverage.

### 4 — SUMMARIZE

Reference lines are stripped, then sentences are scored by normalised
content-word frequency with a positional boost for openings and conclusions.
spaCy is used when present and a deterministic regex segmenter when it is not. A
document that is itself a reference list gets a factual description rather than
its own citations read back to it.

---

## The eight workflows

Every document takes one of these branches, and the branch taken is always shown
to the reader with its reasoning.

| # | Document | What happens | Verified by |
|:--|:---|:---|:---|
| **1** | **Research paper** — narrative body, then a references section | References heading splits body from bibliography; style detected; eight fields parsed per entry; summary runs on the body only | `test_pipeline_parses_a_research_paper` |
| **2** | **Annotated bibliography** — each citation followed by commentary | Recognised from the first line or via force-parse; the citation header is isolated from the annotation before any field is extracted; all-caps titles matched while publisher forms are still rejected | `test_pipeline_honours_force_parse` |
| **3** | **Reference list with no heading** | Density scan walks backwards from the end to the block boundary, so the closing paragraphs of the body are not parsed as citations; method reported as "Detected by citation density" | `tests/test_parsers.py` |
| **4** | **General document** — no bibliography at all | Detection returns non-academic; the parse stage is skipped; the References tab and export panel are hidden; a notice explains that no references were found and none were invented | `test_pipeline_invents_no_citations_for_prose` |
| **5** | **Batch processing** | Each file runs the full pipeline; a failure is caught, recorded against that file with its error kind, and the run continues; results cached against a digest of the whole set | `test_batch_isolates_a_failing_file`, `test_batch_reports_progress` |
| **6** | **Several bibliographies in one file** | Every heading opens a candidate block; the last is kept on the heading alone, earlier ones must be dense enough to read as references, and an appendix or index between them stays in the body | `test_every_reference_block_is_collected_not_only_the_last`, `test_an_appendix_between_two_lists_stays_in_the_body` |
| **7** | **Formatting for submission** | The analyzer's citations are rendered as a finished list in the chosen style, alphabetised or numbered as that style requires; an element the source never supplied is omitted and named rather than invented | `tests/test_formatters.py` |
| **8** | **Review and correction** | Entries below 50% are flagged and filterable; every card has an inline editor for all eight fields; on save the citation is rescored by `score_citation()`, marked edited, and written back at its original position so it survives sorting, filtering and pagination; every export reads the corrected list | `test_edited_authors_round_trip_in_either_order`, `test_confidence_can_be_rescored_after_an_edit` |

---

## Architecture

Four layers. The arrows only ever point downward.

```
PRESENTATION    papermint/ui/  and  app.py        Streamlit lives ONLY here
      │  DocumentInput, PipelineOptions
      ▼
ORCHESTRATION   papermint/pipeline.py             PipelineService
      │
      ▼
DOMAIN          extractors/  parsers/             pure Python, headless
                formatters/  exporters/
                enrichment/
      │
      ▼
DATA MODEL      models.py  errors.py  config.py
```

### The rules, and the test that enforces each one

`tests/test_architecture.py` parses every module with `ast` and contributes 237
of the 428 tests. Break a rule and the build names the file and the line.

| Rule | Enforced by |
|:---|:---|
| No Streamlit import below the presentation layer | `test_the_domain_layer_never_imports_streamlit` |
| Nothing outside `ui/` imports `papermint.ui.*` | `test_the_domain_layer_never_imports_the_ui` |
| Pages import `papermint.pipeline` and nothing deeper | `test_pages_do_not_reach_past_the_pipeline_service` |
| No `print()` anywhere in `papermint/` | `test_no_module_uses_print` |
| No bare `except`, no silent `pass` | `test_no_module_uses_a_bare_except` |
| Every module opens with `from __future__ import annotations` | `test_every_module_uses_postponed_annotations` |
| Every module and public definition is documented with `Args:` / `Returns:` | `test_every_module_and_public_definition_is_documented` |

When the interface needs a fact from the domain layer, it is re-exported through
the service facade — which is why `accepted_formats()` and
`accepted_extensions()` live on `papermint.pipeline`. `papermint/cli.py` is the
standing proof of the layering: it runs the identical `PipelineService` with no
Streamlit process anywhere.

### Errors

```
PaperMintError                  message + optional remedy + stable kind
├── ExtractionError
│   ├── UnsupportedFileTypeError
│   ├── CorruptedDocumentError
│   ├── EmptyDocumentError
│   └── OcrUnavailableError
├── ParsingError
│   └── StyleDetectionError
├── SummarizationError
├── EnrichmentError
│   ├── CrossRefNetworkError
│   └── DoiNotFoundError
└── ExportError
```

The domain layer converts, never swallows. The presentation layer catches
`PaperMintError` first, then `Exception` with a logged traceback and a generic
notice. A broad catch is correct in exactly three places, each with a comment
saying why: around one citation entry, around one file in a batch, and around a
progress callback — so a single malformed reference can never discard a whole
document.

---

## Project structure

```
PaperMint/
├── app.py                          # Entry point: config, logging, routing
├── pyproject.toml
├── papermint/
│   ├── config.py                   # Constants and thresholds
│   ├── models.py                   # Pydantic models and enums
│   ├── errors.py                   # PaperMintError hierarchy
│   ├── pipeline.py                 # PipelineService, the orchestration layer
│   ├── cli.py                      # Headless entry point
│   ├── extractors/
│   │   ├── base.py                 # BaseExtractor, ExtractedDocument
│   │   ├── registry.py             # MIME and extension resolution
│   │   └── pdf_ / image_ / docx_ / pptx_extractor.py
│   ├── parsers/
│   │   ├── text_normalizer.py      # Ligatures, hyphenation, page furniture
│   │   ├── bibliography_detector.py
│   │   ├── citation_splitter.py
│   │   ├── citation_parser.py
│   │   ├── style_detector.py
│   │   └── summarizer.py
│   ├── formatters/
│   │   └── reference_formatter.py  # APA, MLA, IEEE, Chicago rendering and guides
│   ├── enrichment/crossref.py
│   ├── exporters/                  # bibtex, ris, csv, docx, pdf
│   └── ui/                         # Streamlit lives only here
│       ├── theme.py                # Design tokens
│       ├── icons.py                # Inline SVG set
│       ├── html.py                 # Escaping and safe rendering
│       ├── styles.py               # Stylesheet built from tokens
│       ├── navigation.py           # Routes
│       ├── state.py                # Widget state that survives a page switch
│       ├── components/             # primitives, citation_card, export_panel, progress, file_uploader
│       └── pages/                  # home, extract, batch, style_studio, about
└── tests/                          # 428 tests, no network calls
    ├── test_architecture.py        # Enforces the layering rules (237)
    ├── test_ui.py                  # Components, state and every page (40)
    ├── test_normalization.py       # Text repair and parser guards (40)
    ├── test_parsers.py             # Detection and multi-block collection (40)
    ├── test_pipeline.py            # Orchestration, batch, registry, CLI (25)
    ├── test_formatters.py          # Style rendering and its honesty rules (23)
    └── test_models · test_exporters · test_enrichment
```

---

## Data model

`Citation` carries eight core fields plus `raw_text`, `style`, `entry_type`,
`confidence`, `source_file` and `edited`. Display logic lives in properties:
`display_title`, `short_author_string`, `author_string`, `venue`, `locator`,
`doi_url`, `cite_key`, `confidence_band`, `needs_review`, `missing_fields`,
`is_parsed`. `display_title` never returns "Untitled" — it falls back to the
entry's own opening text, rendered in italic sans to mark it as unparsed.

Results: `ExtractionResult` for one document, `BatchFileResult` and `BatchResult`
for a run. `DocumentStats` holds word, character, line, sentence and page counts.

### Thresholds — all in `config.py`, never hard-coded elsewhere

| Constant | Value | Meaning |
|:---|---:|:---|
| `CONFIDENCE_HIGH` | 0.60 | Band becomes Complete |
| `CONFIDENCE_MEDIUM` | 0.30 | Band becomes Partial |
| `CONFIDENCE_REVIEW` | 0.50 | Below this, flagged for review |
| `BIBLIOGRAPHY_DENSITY_THRESHOLD` | 0.20 | Density scan trigger |
| `SPLIT_VALIDATION_RATIO` | 0.40 | Share of segments that must look like citations |
| `REFERENCE_ONLY_COVERAGE` | 0.80 | Above this, the document is a reference list |
| `CITATIONS_PER_PAGE` | 25 | Pagination |

---

## Design system

Every colour, type step, space step, radius and duration lives in
`papermint/ui/theme.py` and is emitted as a CSS custom property. A literal hex
value anywhere else under `ui/` is a defect. `.streamlit/config.toml` carries the
same surface and text values so Streamlit's own chrome sits on the same palette.

**Palette.** Mint `#34D399` on canvas `#0F172A`, with surfaces `#161F33`,
`#1D293D` and `#0B1120` layered above it.

**Type.** Inter for interface chrome, Source Serif 4 for bibliographic content,
JetBrains Mono for identifiers and index numerals. The serif is what makes a
citation card read as scholarship rather than a form field.

### The citation card

```
┌─┬──────────────────────────────────────────────────────────────────────┐
│ │ 01                                   [APA]   [● Complete 100%]        │
│ │ Machine learning in citation parsing         ← serif, 18px            │
│ │ Smith, J. A. & Doe, R. B. · 2020             ← 14px, muted            │
│ │ Journal of Bibliometrics · vol. 15, no. 2, pp. 103-115 · Article     │
│ │ 10.1016/j.jbi.2020.01.002                    ← mono, link            │
└─┴──────────────────────────────────────────────────────────────────────┘
  ▲ 2px rule, coloured by confidence band
```

Confidence is shown at three levels of detail:

| Level | Where | Shows |
|:---|:---|:---|
| Glance | 2px rule on the card's left edge | Band colour |
| Scan | Badge in the card header | Band label and percentage |
| Inspect | Line under the metadata | Exactly which fields are missing |

Bands: **Complete** at 60%+, **Partial** from 30%, **Sparse** below. An entry
under 50% is also flagged for review.

### Deliberately absent

- **No gradient text.** Applying one to every heading flattens hierarchy.
- **No emoji as icons.** They render differently per platform and cannot inherit
  text colour. `icons.py` supplies a stroked SVG set on `currentColor`.
- **No hover lift on static cards.** Motion on a non-interactive element is
  decoration pretending to be an affordance.

### Rendering rules

- Everything interpolated into markup passes through `esc()`. Titles come from
  arbitrary uploaded documents.
- Content markup goes through `render()`, which wraps `st.html()` and bypasses
  the Markdown parser entirely — the four-space code-block leak is structurally
  impossible, not merely avoided.
- Interactive cards are keyed `st.container`s, so real widgets sit inside the
  card chrome.

---

## Engineering standards

- **Python 3.10+.** Modern typing throughout (`Citation | None`, `list[Author]`);
  `typing.List`, `Optional` and `Union` are rejected by ruff's `UP` rules.
- **Pydantic v2.** `model_dump()` / `model_dump_json()`, `model_copy(update=...)`
  for derived instances, constraints declared on the field, computed values as
  `@property`.
- **Logging.** Module-level `logger = logging.getLogger(__name__)`, lazy `%s`
  interpolation never f-strings, `logger.exception()` inside handlers.
  `basicConfig` is called once in `app.py` and once in `cli.py`, never in a
  library module.
- **Optional dependencies.** spaCy is an extra. Downloading a model at request
  time is forbidden — the previous build called `spacy.cli.download()` inside the
  request path and stalled a user-facing page for minutes.
- **Streamlit specifics.** `UploadedFile` bytes are read with `getvalue()`, never
  `read()`. Expensive work is cached in session state against a content digest.
  Widgets written in a loop get a stable key, not a positional index.

Run the gates:

```bash
pytest                 # 428 tests, no network calls
ruff check .
ruff format --check .
```

---

## Testing

428 tests. None makes a network call. CrossRef is mocked and PDFs are synthesised
in memory with PyMuPDF.

| Suite | Tests | Covers |
|:---|---:|:---|
| `test_architecture.py` | 237 | Every layering and coding rule, by parsing each module with `ast` |
| `test_ui.py` | 40 | Markup, escaping, components, sticky state, the processing flow, all five pages via `AppTest` |
| `test_normalization.py` | 40 | Text repair, parser guards, surname particles |
| `test_parsers.py` | 40 | Detection, multi-block collection, splitting, style, fields |
| `test_pipeline.py` | 25 | Orchestration, batch isolation, registry, CLI |
| `test_formatters.py` | 23 | Style rendering, list ordering, the honesty rules |
| `test_models.py` | 11 | Schema, properties, cite keys |
| `test_exporters.py` | 7 | Every format serialises |
| `test_enrichment.py` | 5 | CrossRef against mocks |

---

## Roadmap

| Phase | Milestone | Status |
|:--|:---|:---|
| 1 | Parser engine hardening — field extraction, validation guards, confidence scoring | **Complete** |
| 2 | Architecture and service decoupling — `PipelineService`, typed errors, enforced layering | **Complete** |
| 3 | Interactive review and correction — inline editing, BibTeX copy, search, sort, review filter | **Complete** |
| 3.5 | Multi-block detection, style rendering, and state that survives a page switch | **Complete** |
| 4 | Deduplication and provenance — cross-file duplicate merging, source tagging, concurrency | Planned |
| 5 | Containerisation and deployment | Deferred by request |

`Citation.source_file` is already populated by the pipeline, so the provenance
data for phase 4 is in place. Batch processing is currently sequential.

---

## What changed in 2.1.0

Interface and coverage work, driven by using 2.0.0 on a real education
catalogue.

**Added** - `formatters/reference_formatter.py` and the **Style studio** page:
a `Citation` rendered as APA 7, MLA 9, IEEE or Chicago 17, with an account of
what each style is for, its ordered elements and the punctuation that closes
each, and the same entry shown four ways. `PipelineService.parse_reference()`
parses one pasted reference. `ui/state.py` keeps widget values across a page
switch. About gained a full "Citation styles, explained" section.

**Changed** - the citation card is now an aligned label-and-value grid with a
coverage meter, so every field says what it is. The processing indicator is an
animated flow that names what each stage is doing. Bibliography detection
collects *every* qualifying reference block rather than the text after the last
heading, bounded by appendix, index and glossary headings. Both workspace pages
show their cached result when the upload control comes back empty after a page
switch.

**Removed** - the DOI lookup page, replaced by the style studio; the "Segments
set aside" panel, though the quarantine behind it still runs and still keeps
non-bibliographic segments out of every export; `_has_bibliographic_density()`,
dead since 2.0.0.

**Unchanged, and deliberately so** - nothing is invented. The new formatter
omits any element the source did not supply and names it, and it never recases
a title, because deciding which words are proper nouns is exactly the judgement
a machine gets wrong.

---

## What changed in 2.0.0

A rebuild of the architecture, the parsing engine and the interface. The public
signatures of `detect_bibliography_section`, `split_citations`, `parse_citation`,
`detect_style`, `summarize` and every exporter were kept, so the original 48
tests still pass untouched. The suite grew from 48 to 345.

**Added** — `pipeline.py` (`PipelineService`, `PipelineStage`, `process_batch()`
with per-file isolation), `errors.py` (the full typed hierarchy), the extractor
registry, `cli.py`, `text_normalizer.py`, the `theme.py` / `icons.py` /
`html.py` design layer, the inline citation editor with rescoring, per-card
BibTeX view, five-field search, six sort orders and a review filter.

**Changed** — both Streamlit pages now call the service instead of sequencing
domain engines themselves; results cache against a content digest; the density
scan walks back to a block boundary; the references heading match takes the last
occurrence; every split is validated before acceptance; spaCy became optional.

**Fixed** — uploads returning zero bytes on every rerun; the stepper stacking
four progress bars; three-or-more-author APA citations losing their authors; a
date span in a title becoming a page range; unescaped document text corrupting
cards; inflated sentence counts; page counts always zero; domain logging going
nowhere; the About page rendering its diagram as a code block; CrossRef network
failure being indistinguishable from a missing DOI.

**Removed** — `pytextrank`, `bibtexparser` and `httpx` (none were imported);
`spacy.cli.download()` from the request path; named entity recognition from
author extraction; gradient text, emoji icons and hover-lift animation.

---

## Built with

[Streamlit](https://streamlit.io) ·
[Pydantic](https://docs.pydantic.dev) ·
[PyMuPDF](https://pymupdf.readthedocs.io) ·
[python-docx](https://python-docx.readthedocs.io) ·
[python-pptx](https://python-pptx.readthedocs.io) ·
[Tesseract](https://github.com/tesseract-ocr/tesseract) ·
[ReportLab](https://www.reportlab.com) ·
[spaCy](https://spacy.io) (optional)

---

## Contributing

1. Fork and branch: `git checkout -b feature/your-feature`
2. Make the change, and add the test that would have caught its absence
3. `pytest && ruff check . && ruff format --check .`
4. Open a pull request

---

## License

MIT. See [LICENSE](LICENSE).

Made by [Akki](https://github.com/Akki-333)
