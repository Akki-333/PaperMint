"""Tests for the orchestration layer and the extractor registry."""

from __future__ import annotations

import pymupdf
import pytest

from papermint.cli import main as cli_main
from papermint.errors import (
    EmptyDocumentError,
    ExtractionError,
    PaperMintError,
    UnsupportedFileTypeError,
)
from papermint.extractors.registry import (
    resolve_extractor,
    supported_extensions,
    supported_format_names,
)
from papermint.models import DetectionMethod, DocumentKind
from papermint.pipeline import (
    DocumentInput,
    PipelineOptions,
    PipelineService,
    PipelineStage,
)

PAPER_TEXT = """A Study of Urban Transport Policy

Introduction
Urban transport policy has shifted markedly over the past decade.
This study examines rail and road investment across three mid-sized cities.
We surveyed four hundred households over eighteen months.

Conclusion
Policy makers should prioritise service frequency over new construction.

References
Smith, J. A., & Doe, R. B. (2020). Machine learning in citation parsing. Journal of Bibliometrics, 15(2), 103-115. https://doi.org/10.1016/j.jbi.2020.01.002
Johnson, L. (2019). The future of AI. Tech Press.
Williams, C. D., Brown, E., & Davis, F. (2021). Neural networks for text extraction. IEEE Transactions on Neural Networks, 32(4), 10-25.
"""

POLICY_TEXT = """National Digital Literacy Scheme

The scheme was launched in 2015 to widen access to computing skills.
Eligible households receive a subsidy of up to forty percent.
Applications opened in 2021 and close at the end of the financial year.
District offices process claims within thirty working days.
Beneficiaries must hold a valid residence certificate.
"""


def make_pdf(text: str) -> bytes:
    """Render text into a single-page PDF.

    Args:
        text: The body text.

    Returns:
        The PDF bytes.
    """
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(40, 40, 555, 760), text, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def service() -> PipelineService:
    """Return a pipeline service with default options."""
    return PipelineService()


# --- Registry --------------------------------------------------------------


def test_registry_resolves_by_mime():
    extractor = resolve_extractor("application/pdf", "x.pdf")
    assert type(extractor).__name__ == "PDFExtractor"


def test_registry_falls_back_to_extension():
    extractor = resolve_extractor("application/octet-stream", "deck.pptx")
    assert type(extractor).__name__ == "PPTXExtractor"


def test_registry_rejects_unknown_type():
    with pytest.raises(UnsupportedFileTypeError) as excinfo:
        resolve_extractor("application/zip", "archive.zip")
    assert excinfo.value.remedy
    assert isinstance(excinfo.value, ExtractionError)


def test_registry_lists_formats():
    assert "pdf" in supported_extensions()
    assert "PDF" in supported_format_names()


# --- Single document -------------------------------------------------------


def test_pipeline_parses_a_research_paper(service):
    result = service.process_document(
        DocumentInput("paper.pdf", make_pdf(PAPER_TEXT), "application/pdf")
    )

    assert result.document_kind is DocumentKind.RESEARCH_PAPER
    assert result.detection_method is DetectionMethod.SECTION_HEADER
    assert result.citation_count == 3
    assert result.average_confidence > 0.7
    assert result.stats.page_count == 1
    assert result.summary
    assert result.duration_ms >= 0


def test_pipeline_reports_every_stage(service):
    seen: list[PipelineStage] = []
    service.process_document(
        DocumentInput("paper.pdf", make_pdf(PAPER_TEXT), "application/pdf"),
        on_progress=seen.append,
    )
    assert seen == [
        PipelineStage.EXTRACT,
        PipelineStage.CHARACTERIZE,
        PipelineStage.PARSE,
        PipelineStage.SUMMARIZE,
        PipelineStage.DONE,
    ]


def test_pipeline_invents_no_citations_for_prose(service):
    result = service.process_document(
        DocumentInput("policy.pdf", make_pdf(POLICY_TEXT), "application/pdf")
    )

    assert result.citation_count == 0
    assert result.document_kind is DocumentKind.NON_ACADEMIC
    assert result.detection_method is DetectionMethod.NONE
    assert result.summary


def test_pipeline_honours_force_parse(service):
    result = service.process_document(
        DocumentInput("policy.pdf", make_pdf(POLICY_TEXT), "application/pdf"),
        PipelineOptions(force_parse=True),
    )
    assert result.detection_method is DetectionMethod.FORCED
    assert result.document_kind is DocumentKind.BIBLIOGRAPHY


def test_pipeline_tags_source_file(service):
    result = service.process_document(
        DocumentInput("paper.pdf", make_pdf(PAPER_TEXT), "application/pdf")
    )
    assert all(c.source_file == "paper.pdf" for c in result.citations)


def test_pipeline_rejects_an_empty_document(service):
    with pytest.raises(EmptyDocumentError) as excinfo:
        service.process_document(DocumentInput("blank.pdf", make_pdf("   "), "application/pdf"))
    assert excinfo.value.remedy


def test_pipeline_rejects_an_unreadable_file(service):
    with pytest.raises(PaperMintError):
        service.process_document(
            DocumentInput("broken.pdf", b"not a pdf at all", "application/pdf")
        )


# --- Batch -----------------------------------------------------------------


def test_batch_isolates_a_failing_file(service):
    result = service.process_batch(
        [
            DocumentInput("good.pdf", make_pdf(PAPER_TEXT), "application/pdf"),
            DocumentInput("broken.pdf", b"garbage", "application/pdf"),
            DocumentInput("policy.pdf", make_pdf(POLICY_TEXT), "application/pdf"),
        ]
    )

    assert result.file_count == 3
    assert result.error_count == 1
    assert result.success_count == 2
    assert result.citation_count == 3
    assert result.files[1].error_kind == "corrupted_document"
    assert result.files[1].error


def test_batch_reports_progress(service):
    seen: list[tuple[int, int, str]] = []
    service.process_batch(
        [DocumentInput("a.pdf", make_pdf(PAPER_TEXT), "application/pdf")],
        on_file=lambda i, t, n: seen.append((i, t, n)),
    )
    assert seen == [(0, 1, "a.pdf")]


def test_batch_of_nothing_is_empty(service):
    result = service.process_batch([])
    assert result.file_count == 0
    assert result.citations == []
    assert result.average_confidence == 0.0


# --- Headless command line -------------------------------------------------


def test_the_cli_runs_without_streamlit(tmp_path, capsys):
    """The engine must be usable with no presentation layer present."""
    source = tmp_path / "paper.pdf"
    source.write_bytes(make_pdf(PAPER_TEXT))

    exit_code = cli_main([str(source), "--quiet"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "@article{smith_2020_machine," in captured.out


def test_the_cli_writes_the_requested_format(tmp_path):
    source = tmp_path / "paper.pdf"
    source.write_bytes(make_pdf(PAPER_TEXT))
    target = tmp_path / "refs.ris"

    assert cli_main([str(source), "--format", "ris", "--out", str(target), "--quiet"]) == 0
    written = target.read_text(encoding="utf-8")
    assert written.startswith("TY  - JOUR")
    assert "ER  - " in written


def test_the_cli_emits_structured_json(tmp_path, capsys):
    import json

    source = tmp_path / "paper.pdf"
    source.write_bytes(make_pdf(PAPER_TEXT))

    assert cli_main([str(source), "--json", "--quiet"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["citation_count"] == 3
    assert payload["files"][0]["result"]["document_kind"] == "research_paper"


def test_the_cli_reports_a_missing_file(tmp_path, capsys):
    assert cli_main([str(tmp_path / "absent.pdf"), "--quiet"]) == 2
    assert "No readable documents" in capsys.readouterr().err
