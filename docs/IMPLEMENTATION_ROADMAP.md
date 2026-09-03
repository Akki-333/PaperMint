# PaperMint — Implementation Roadmap

## 1. Status at a glance

| Phase | Milestone | Status | Focus |
|:---|:---|:---|:---|
| **1** | Parser engine hardening | **Complete** | Field extraction, validation guards, confidence scoring |
| **2** | Architecture and service decoupling | **Complete** | `PipelineService`, typed errors, enforced layering |
| **3** | Interactive review and correction | **Complete** | Inline editing, BibTeX copy, search, sort, review filter |
| **4** | Deduplication and provenance | **Planned** | Cross-file duplicate merging, source tagging, concurrency |
| **5** | Containerisation and deployment | **Deferred** | Excluded from the current scope by request |

Verification: `pytest` runs 345 tests; `ruff check .` and `ruff format --check .`
both pass.

---

## 2. Phase 1 — Parser engine hardening (complete)

**Goal.** Eliminate fabricated authors, "Untitled" cards and nonsense field
values.

**Delivered.**

- `parsers/text_normalizer.py`: ligature folding, de-hyphenation across line
  breaks, dash and quote unification, page-number and running-header removal.
  This is the single largest contributor to output quality, because most visibly
  broken fields were broken before parsing ever began.
- Validation on every extractor. A title candidate is rejected when it is a page
  locator, an author list, a DOI, a URL or a publisher; a page range is rejected
  when it is a span of two four-digit calendar years.
- Multi-author APA parsing. The previous regex captured `"C. D., Brown, E."` as
  one author's given name for any citation with three or more authors.
- Entry type inferred from extracted fields, so a book with a publisher and no
  volume is typed as a book rather than "Other".
- General-purpose named entity recognition removed from author extraction.

**Gate.** `tests/test_normalization.py`, plus the original parser suite,
unchanged and still green.

---

## 3. Phase 2 — Architecture and service decoupling (complete)

**Goal.** No presentation code sequences domain engines.

**Delivered.**

- `papermint/pipeline.py` with `PipelineService.process_document()` and
  `process_batch()`, a `PipelineStage` enum, progress callbacks and per-file
  error isolation.
- `papermint/errors.py`: the full `PaperMintError` hierarchy, each error
  carrying a reader-facing message and an optional remedy.
- `papermint/extractors/registry.py`, replacing the MIME-type `if/elif` chain
  that was duplicated inside both Streamlit pages.
- `papermint/cli.py`, a headless entry point running the same service.
- Logging configured once at start-up. Without it, every `logger.error` and
  `logger.exception` in the domain layer was silently discarded.

**Gate.** `tests/test_architecture.py` parses every module with `ast` and fails
on a Streamlit import in the domain layer, a page importing past the service, a
`print()` call, a bare `except`, a missing `from __future__ import annotations`
or an undocumented public definition. `tests/test_pipeline.py` runs the pipeline
and the CLI end to end with no Streamlit process.

---

## 4. Phase 3 — Interactive review and correction (complete)

**Goal.** Let a researcher correct a citation before exporting it.

**Delivered.**

- Inline editor in a popover on every card: title, authors, year, volume, pages,
  journal, publisher and DOI. Author strings round-trip in either
  `Family, Given` or `Given Family` order.
- Confidence rescored on save through `score_citation()`, so the badge stays
  honest, and the entry is marked as edited.
- One-click BibTeX view per card, using Streamlit's own copy affordance.
- Search across title, author, year, venue and DOI; six sort orders; a "Needs
  review" toggle; pagination beyond 25 entries.
- Edits persist in session state and flow through to every export.

**Gate.** `tests/test_ui.py` covers card markup, escaping, the missing-field
line, author round-tripping, and renders all five pages under `AppTest`.

### A defect fixed along the way

`st.file_uploader` returns a `BytesIO` whose cursor stays where the last read
left it. The previous code called `.read()`, so on every rerun, meaning every
keystroke in the search box, it received zero bytes and the page reported that
no text could be extracted. `read_upload()` uses `getvalue()`, and results are
cached against a content digest so interacting with a filter no longer
reprocesses the document at all.

---

## 5. Phase 4 — Deduplication and provenance (planned)

**Goal.** Make batch mode a real literature-review tool.

**Deliverables.**

- Fuzzy title and DOI matching to merge duplicates across files.
- Provenance retained on merged entries. `Citation.source_file` is already
  populated by the pipeline, so the data is in place.
- Concurrent extraction across batch files.
- A conflict view for entries that match but disagree on a field.

**Gate.** Ten papers with overlapping bibliographies produce one merged list
with every source document listed against each shared entry.

---

## 6. Phase 5 — Containerisation and deployment (deferred)

Excluded from the current scope by request. `docs/DEPLOYMENT_GUIDE.md` retains
the reference material for when it resumes.
