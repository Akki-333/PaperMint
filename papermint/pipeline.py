"""Application orchestration layer.

:class:`PipelineService` owns the end-to-end document workflow so that no
presentation code ever has to sequence the domain engines itself. It imports
nothing from Streamlit and is therefore usable from a command line tool, a web
service, a notebook or a test runner.

The pipeline is a fixed sequence of stages:

    extract -> normalise -> characterise -> segment -> parse -> summarise

Each stage reports progress through an optional callback, and every failure is
raised as a :class:`~papermint.errors.PaperMintError` subclass carrying a
message written for a reader rather than for a log file.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

from papermint.config import DEFAULT_SUMMARY_SENTENCES
from papermint.errors import EmptyDocumentError, PaperMintError, ParsingError
from papermint.extractors.registry import (
    resolve_extractor,
    supported_extensions,
    supported_format_names,
)
from papermint.models import (
    BatchFileResult,
    BatchResult,
    Citation,
    CitationStyle,
    DetectionMethod,
    DocumentKind,
    DocumentStats,
    ExtractionResult,
)
from papermint.parsers.bibliography_detector import DetectionOutcome, characterize_document
from papermint.parsers.citation_parser import is_bibliographic_entry, parse_citation
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style
from papermint.parsers.summarizer import summarize, summarize_reference_list
from papermint.parsers.text_normalizer import (
    normalize_document,
    sentence_count,
    word_count,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage reporting
# ---------------------------------------------------------------------------


class PipelineStage(str, Enum):
    """The ordered stages of document processing."""

    EXTRACT = "extract"
    CHARACTERIZE = "characterize"
    PARSE = "parse"
    SUMMARIZE = "summarize"
    DONE = "done"

    @property
    def label(self) -> str:
        """Return the reader-facing name of the stage."""
        return {
            PipelineStage.EXTRACT: "Reading document",
            PipelineStage.CHARACTERIZE: "Locating bibliography",
            PipelineStage.PARSE: "Parsing citations",
            PipelineStage.SUMMARIZE: "Summarising",
            PipelineStage.DONE: "Complete",
        }[self]

    @property
    def detail(self) -> str:
        """Return a one-line account of what this stage is doing.

        The processing indicator shows this beneath the running step, so a
        reader watching a long document is told what the work actually is
        rather than being shown an unexplained spinner. It lives here, beside
        the stage it describes, so the two cannot drift apart.
        """
        return {
            PipelineStage.EXTRACT: (
                "Decoding the file, then repairing the text: folding ligatures, "
                "rejoining words split across a line, dropping running headers."
            ),
            PipelineStage.CHARACTERIZE: (
                "Classifying the document and collecting every reference block "
                "in it, by heading and by citation density."
            ),
            PipelineStage.PARSE: (
                "Segmenting each block into entries and reading eight fields "
                "from every one, validating each candidate before accepting it."
            ),
            PipelineStage.SUMMARIZE: (
                "Scoring the narrative body by content-word frequency and "
                "position, with the references left out."
            ),
            PipelineStage.DONE: "Finished.",
        }[self]

    @property
    def order(self) -> int:
        """Return the zero-based position of the stage in the sequence."""
        return list(PipelineStage).index(self)


#: Signature of the optional per-stage progress callback.
ProgressCallback = Callable[["PipelineStage"], None]

#: Signature of the optional per-file batch progress callback.
BatchCallback = Callable[[int, int, str], None]


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentInput:
    """One document handed to the pipeline.

    Attributes:
        filename: The original file name, used for display and format hints.
        data: The raw bytes of the file.
        mime_type: The MIME type reported by the client, when known.
    """

    filename: str
    data: bytes
    mime_type: str = ""


@dataclass(frozen=True, slots=True)
class PipelineOptions:
    """Tunable behaviour for a single pipeline run.

    Attributes:
        force_parse: Treat the whole document as a bibliography.
        force_prose: Treat the document as having no bibliography at all, so no
            citations are produced. The counterpart to ``force_parse``, for when
            detection wrongly finds a reference list inside narrative text.
        summary_sentences: How many sentences the summary should contain.
        build_summary: Whether to run the summariser at all.
        strip_furniture: Whether to remove page numbers and running headers.
    """

    force_parse: bool = False
    force_prose: bool = False
    summary_sentences: int = DEFAULT_SUMMARY_SENTENCES
    build_summary: bool = True
    strip_furniture: bool = True


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PipelineService:
    """Runs the document workflow and returns fully populated results.

    Attributes:
        options: Default options applied when a call does not supply its own.
    """

    options: PipelineOptions = field(default_factory=PipelineOptions)

    # -- Internals ----------------------------------------------------------

    @staticmethod
    def _report(callback: ProgressCallback | None, stage: PipelineStage) -> None:
        """Invoke a progress callback, ignoring presentation-layer failures.

        Args:
            callback: The optional callback supplied by the caller.
            stage: The stage that has just started.
        """
        if callback is None:
            return
        try:
            callback(stage)
        except Exception:  # pragma: no cover - never let the UI break a run
            logger.debug("Progress callback raised; continuing.", exc_info=True)

    @staticmethod
    def _build_stats(text: str, page_count: int) -> DocumentStats:
        """Measure a document for the statistics strip in the interface.

        Args:
            text: The normalised document text.
            page_count: The real page count, or 0 when unknown.

        Returns:
            The populated statistics model.
        """
        return DocumentStats(
            word_count=word_count(text),
            character_count=len(text),
            line_count=text.count("\n") + 1 if text else 0,
            sentence_count=sentence_count(text),
            page_count=page_count,
        )

    def _parse_entries(
        self, bibliography_text: str, source_filename: str
    ) -> tuple[list[Citation], list[Citation], CitationStyle, float]:
        """Segment and parse a bibliography block.

        Segmentation is structural, so a document whose appendix is numbered or
        whose body wraps oddly yields segments that are prose rather than
        references. Each parsed entry is therefore checked for positive
        evidence of being a citation, and those without it are separated out
        rather than presented as citations or written into an export.

        Args:
            bibliography_text: The isolated bibliography.
            source_filename: Recorded on each citation for batch provenance.

        Returns:
            A ``(citations, discarded, style, style_confidence)`` tuple.

        Raises:
            ParsingError: If segmentation raises an unexpected failure.
        """
        try:
            segments = split_citations(bibliography_text)
        except Exception as exc:
            logger.exception("Citation segmentation failed")
            raise ParsingError(f"The bibliography could not be split into entries: {exc}") from exc

        if not segments:
            return [], [], CitationStyle.UNKNOWN, 0.0

        style, style_confidence = detect_style(segments)

        citations: list[Citation] = []
        discarded: list[Citation] = []
        for segment in segments:
            try:
                citation = parse_citation(segment, style)
            except Exception as exc:
                # One malformed entry must never discard the whole document.
                logger.warning("Skipping an unparsable entry (%s): %.80s", exc, segment)
                continue
            if not citation.raw_text.strip():
                continue
            citation.source_file = source_filename
            if is_bibliographic_entry(citation):
                citations.append(citation)
            else:
                discarded.append(citation)

        if discarded:
            logger.info(
                "Kept %d of %d segments; %d carried no bibliographic evidence",
                len(citations),
                len(segments),
                len(discarded),
            )
        return citations, discarded, style, style_confidence

    # -- Public API ---------------------------------------------------------

    def process_document(
        self,
        document: DocumentInput,
        options: PipelineOptions | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> ExtractionResult:
        """Run the full pipeline over a single document.

        Args:
            document: The file to process.
            options: Per-call overrides; falls back to the service defaults.
            on_progress: Optional callback invoked as each stage begins.

        Returns:
            A fully populated :class:`ExtractionResult`.

        Raises:
            UnsupportedFileTypeError: If no extractor handles the file.
            CorruptedDocumentError: If the file cannot be decoded.
            EmptyDocumentError: If the file decodes but contains no text.
            OcrUnavailableError: If an image needs OCR that is unavailable.
            ParsingError: If bibliography segmentation fails unexpectedly.
        """
        opts = options or self.options
        started = time.perf_counter()
        warnings: list[str] = []

        # -- Stage 1: extract -----------------------------------------------
        self._report(on_progress, PipelineStage.EXTRACT)
        extractor = resolve_extractor(document.mime_type, document.filename)
        extracted = extractor.extract_document(document.data)
        warnings.extend(extracted.warnings)

        text = normalize_document(extracted.text, strip_furniture=opts.strip_furniture)
        if not text.strip():
            raise EmptyDocumentError(
                f"No text could be read from {document.filename}.",
                remedy=(
                    "If this is a scanned document, upload the pages as images so "
                    "that optical character recognition can run."
                ),
            )

        stats = self._build_stats(text, extracted.page_count)

        # -- Stage 2: characterise ------------------------------------------
        self._report(on_progress, PipelineStage.CHARACTERIZE)
        outcome = characterize_document(text, force_parse=opts.force_parse)
        if opts.force_prose:
            # The reader overruled the classifier. Produce no citations rather
            # than parsing a block the reader has said is not a bibliography.
            outcome = DetectionOutcome(
                bibliography_text="",
                body_text=text.strip(),
                method=DetectionMethod.NONE,
                kind=DocumentKind.NON_ACADEMIC,
                confidence=0.0,
                notes=[
                    (
                        "You asked for this document to be read as prose, so no "
                        "citations were parsed from it."
                    )
                ],
            )
        warnings.extend(outcome.notes)

        # -- Stage 3: parse --------------------------------------------------
        self._report(on_progress, PipelineStage.PARSE)
        citations: list[Citation] = []
        discarded: list[Citation] = []
        style = CitationStyle.UNKNOWN
        style_confidence = 0.0

        if outcome.found:
            citations, discarded, style, style_confidence = self._parse_entries(
                outcome.bibliography_text, document.filename
            )
            if not citations and discarded:
                warnings.append(
                    f"A block of {len(discarded)} segments was located, but none of them "
                    "carried an author, a year, a venue or an identifier, so none was "
                    "treated as a citation. This document does not appear to contain a "
                    "bibliography."
                )
            elif not citations:
                warnings.append(
                    "A bibliography block was located but no entry could be parsed from it."
                )
            elif discarded:
                # Reported in the processing notes rather than displayed as a
                # list of rejected text. A reader wants their references, not a
                # rubbish bin; the count is enough to explain a short list.
                warnings.append(
                    f"{len(citations)} of {len(citations) + len(discarded)} segments carried "
                    "an author, a year, a venue or an identifier and were read as "
                    "references. The rest were appendix prose or section headings sharing "
                    "the reference list's numbering, and were left out."
                )

        # -- Stage 4: summarise ---------------------------------------------
        self._report(on_progress, PipelineStage.SUMMARIZE)
        summary = ""
        if opts.build_summary:
            if outcome.kind in {
                DocumentKind.BIBLIOGRAPHY,
                DocumentKind.ANNOTATED_BIBLIOGRAPHY,
            }:
                summary = summarize_reference_list(len(citations), outcome.kind.label)
            else:
                body = outcome.body_text or text
                summary = summarize(body, opts.summary_sentences)

        self._report(on_progress, PipelineStage.DONE)

        result = ExtractionResult(
            citations=citations,
            discarded=discarded,
            raw_text=text,
            bibliography_text=outcome.bibliography_text,
            source_filename=document.filename,
            detected_style=style,
            style_confidence=style_confidence,
            summary=summary,
            page_count=extracted.page_count,
            warnings=warnings,
            document_kind=outcome.kind,
            detection_method=outcome.method,
            stats=stats,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        logger.info(
            "Processed %s: %d citations, kind=%s, method=%s, %dms",
            document.filename,
            result.citation_count,
            result.document_kind.value,
            result.detection_method.value,
            result.duration_ms,
        )
        return result

    def parse_reference(self, text: str) -> Citation:
        """Parse one reference string a reader typed or pasted.

        The presentation layer may not import the parsers directly, so this is
        the service's front door for the single-entry case: the reference formatter
        hands over a line copied out of a paper and gets back the same
        :class:`~papermint.models.Citation` a document scan would produce.

        Args:
            text: One reference, as written.

        Returns:
            The parsed citation, with unreadable fields left empty.

        Raises:
            ParsingError: If the text is blank.
        """
        if not text or not text.strip():
            raise ParsingError(
                "There is nothing to parse.",
                remedy="Paste a single reference, such as one line from a Works Cited page.",
            )

        segment = text.strip()
        style, _confidence = detect_style([segment])
        return parse_citation(segment, style)

    def process_batch(
        self,
        documents: Sequence[DocumentInput] | Iterable[DocumentInput],
        options: PipelineOptions | None = None,
        on_file: BatchCallback | None = None,
    ) -> BatchResult:
        """Run the pipeline over several documents, isolating per-file errors.

        A failure in one document is recorded against that document and the
        run continues, so a single corrupt file cannot discard the results of
        an entire literature review.

        Args:
            documents: The files to process, in order.
            options: Per-call overrides applied to every document.
            on_file: Optional callback receiving ``(index, total, filename)``
                before each file is processed.

        Returns:
            An aggregated :class:`BatchResult`.
        """
        opts = options or self.options
        items = list(documents)
        started = time.perf_counter()
        results: list[BatchFileResult] = []

        for index, document in enumerate(items):
            if on_file is not None:
                try:
                    on_file(index, len(items), document.filename)
                except Exception:  # pragma: no cover - presentation only
                    logger.debug("Batch callback raised; continuing.", exc_info=True)

            try:
                result = self.process_document(document, opts)
                results.append(BatchFileResult(filename=document.filename, result=result))
            except PaperMintError as exc:
                logger.warning("Batch item %s failed: %s", document.filename, exc)
                results.append(
                    BatchFileResult(
                        filename=document.filename,
                        error=str(exc),
                        error_kind=exc.kind,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Unexpected failure on %s", document.filename)
                results.append(
                    BatchFileResult(
                        filename=document.filename,
                        error=f"Unexpected failure: {exc}",
                        error_kind="unexpected",
                    )
                )

        return BatchResult(
            files=results,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )


#: A ready-to-use service instance with default options.
default_pipeline = PipelineService()


def accepted_formats() -> list[str]:
    """List the human-readable formats the pipeline can process.

    Re-exported here so the presentation layer can describe what it accepts
    without importing the extractor registry directly.

    Returns:
        The format display names, such as ``["PDF", "Image", ...]``.
    """
    return supported_format_names()


def accepted_extensions() -> list[str]:
    """List the file extensions the pipeline can process.

    Returns:
        Sorted, lowercase extensions without a leading dot.
    """
    return supported_extensions()


__all__ = [
    "BatchCallback",
    "DocumentInput",
    "PipelineOptions",
    "PipelineService",
    "PipelineStage",
    "ProgressCallback",
    "accepted_extensions",
    "accepted_formats",
    "default_pipeline",
]
