# PaperMint — Engineering Standards

Every rule below is enforced by a test. Where a rule has no test, it is a
preference and is marked as one.

Run the gates with:

```
ruff check .
ruff format --check .
pytest
```

---

## 1. Language and typing

- Target runtime **Python 3.10+**.
- Every module begins with `from __future__ import annotations`.
  Enforced by `test_every_module_uses_postponed_annotations`.
- Modern typing throughout: `Citation | None`, `list[Author]`, `dict[str, str]`.
  `typing.List`, `Optional` and `Union` are rejected by the `UP` rule set.
- Every function signature and class attribute is annotated.
- Every module and every public definition carries a docstring with `Args:` and
  `Returns:` sections. Enforced by
  `test_every_module_and_public_definition_is_documented`.

### Pydantic v2

- `model_dump()` and `model_dump_json()`, never `dict()` or `json()`.
- `model_copy(update={...})` for derived instances, as the citation editor does.
- Constraints declared on the field: `Field(default=0.0, ge=0.0, le=1.0)`.
- Computed values are `@property`, not stored fields, so they cannot drift from
  the data they derive from.

---

## 2. Layering

```
FORBIDDEN
  papermint/parsers/*        -> import streamlit
  papermint/extractors/*     -> import streamlit
  papermint/exporters/*      -> import streamlit
  papermint/enrichment/*     -> import streamlit
  papermint/{models,config,errors,pipeline}.py -> import streamlit
  papermint/*                -> import papermint.ui.*
  papermint/ui/pages/*       -> import papermint.parsers.* or papermint.extractors.*

ALLOWED
  Streamlit only in papermint/ui/ and app.py
  Pages talk to papermint.pipeline and nothing deeper
```

Enforced by `test_the_domain_layer_never_imports_streamlit`,
`test_the_domain_layer_never_imports_the_ui` and
`test_pages_do_not_reach_past_the_pipeline_service`.

**Why it matters in practice.** `papermint/cli.py` runs the identical engine
with no Streamlit process. If the rule lapses, that stops working, and so does
every headless test.

**Corollary.** When the interface needs a fact from the domain layer, the fact
is re-exported through the service facade rather than reached for directly. This
is why `accepted_formats()` exists on `papermint.pipeline`.

---

## 3. Errors

Never a bare `except`, never a silent `pass`. Enforced by
`test_no_module_uses_a_bare_except`.

```
PaperMintError                       message + optional remedy
+-- ExtractionError
|   +-- UnsupportedFileTypeError
|   +-- CorruptedDocumentError
|   +-- EmptyDocumentError
|   +-- OcrUnavailableError
+-- ParsingError
|   +-- StyleDetectionError
+-- SummarizationError
+-- EnrichmentError
|   +-- CrossRefNetworkError
|   +-- DoiNotFoundError
+-- ExportError
```

Every error carries a message written for a reader and, where there is a useful
next step, a `remedy` the interface renders beneath it. `kind` is a stable slug
the batch view uses to group failures.

### The pattern

```python
# Domain layer: convert, do not swallow.
try:
    doc = pymupdf.open("pdf", file_bytes)
except Exception as exc:
    logger.exception("Failed to open PDF stream")
    raise CorruptedDocumentError(
        "This PDF could not be opened. It may be corrupted or password protected.",
        remedy="Try re-saving the PDF, then upload it again.",
    ) from exc

# Presentation layer: three tiers, narrowest first.
try:
    result = PipelineService().process_document(document, options)
except PaperMintError as err:
    notice(
        "This document could not be processed",
        str(err),
        tone="critical",
        details=[err.remedy] if err.remedy else None,
    )
except Exception:
    logger.exception("Unexpected failure while processing %s", document.filename)
    notice("Something went wrong", "...", tone="critical")
```

### Where a broad catch is correct

Three places, each with a comment saying why: around one citation entry, so a
single malformed reference cannot discard a whole document; around one file in a
batch; and around a progress callback, so a presentation-layer bug cannot abort
a run in progress.

---

## 4. Logging

- No `print()` anywhere in `papermint/`. Enforced by `test_no_module_uses_print`.
- Module-level `logger = logging.getLogger(__name__)`.
- Lazy `%s` interpolation, never an f-string, so a suppressed message costs
  nothing to format. Enforced by the `G` rule set.
- `logger.exception(...)` inside an exception handler; it records the traceback,
  so the exception object must not also be interpolated into the message.
- Levels: `DEBUG` for heuristic branches, `INFO` for a processed document,
  `WARNING` for a skipped entry or a missing optional model, `ERROR` for a
  failure the reader will see.
- Configured exactly once, in `app.py` and in `papermint/cli.py`. Library
  modules never call `basicConfig`.

---

## 5. Parsing discipline

The rule that governs the parser: **propose, then validate**.

Every extractor generates candidates in descending order of reliability and
tests each one before accepting it. A rejected candidate leaves the field empty,
which the interface renders honestly as missing.

Concretely, a title candidate is rejected when it is a page locator, an author
list, a DOI, a URL, a publisher, or shorter than two real words. A page range is
rejected when it is a span of two four-digit calendar years.

General-purpose named entity recognition is not used for author extraction. It
reports place names and common nouns as people, and a fabricated author is worse
than a missing one.

---

## 6. Optional dependencies

spaCy is an extra, not a requirement. `_get_nlp()` imports it lazily, returns
`None` when it or its model is absent, and the summariser falls back to a
deterministic regex segmenter.

Downloading a model at request time is forbidden. The previous implementation
called `spacy.cli.download()` inside the request path, which stalls a
user-facing page for minutes with no feedback.

A CI job installs without the extra specifically to keep the fallback exercised.

---

## 7. Presentation rules

- Interpolated values are escaped with `esc()`. Titles come from arbitrary
  uploaded documents.
- Content markup goes through `render()`, which uses `st.html()` and therefore
  bypasses the Markdown parser entirely.
- Colour, spacing and type come from `papermint/ui/theme.py`. A literal hex
  value in a component is a defect.
- Expensive work is cached in session state against a content digest. Streamlit
  reruns the whole script on every interaction.
- Uploaded bytes are read with `getvalue()`, never `read()`.

---

## 8. Tests

| File | Covers |
|:---|:---|
| `test_models.py` | Schema validation, computed properties, cite keys |
| `test_parsers.py` | Detection, splitting, style scoring, field extraction |
| `test_normalization.py` | Unicode repair, de-hyphenation, parser guards |
| `test_pipeline.py` | Orchestration, batch isolation, registry, the CLI |
| `test_exporters.py` | Serialisation for every format |
| `test_enrichment.py` | CrossRef client against mocked responses |
| `test_ui.py` | Markup, escaping, components, all five pages under `AppTest` |
| `test_architecture.py` | Every rule in this document |

No test makes a network call. CrossRef is mocked; PDFs are synthesised in memory
with PyMuPDF.

---

## 9. Version control

> Commit and push only when the project owner explicitly asks. No automated,
> periodic or background commits during a refactoring session.
