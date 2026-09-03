"""Application-wide constants and configuration for PaperMint.

This module is deliberately dependency-free. It is imported by the domain
layer, the orchestration layer and the presentation layer alike, so it must
never import Streamlit or any heavyweight runtime.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "PaperMint"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Extract, parse, and export academic citations from PDFs, images, and documents"
APP_ICON = "🌿"
APP_TAGLINE = "Extract · Parse · Export"
APP_REPO_URL = "https://github.com/Akki-333/PaperMint"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS: dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

ACCEPTED_FILE_TYPES: list[str] = list(SUPPORTED_EXTENSIONS.keys())

MAX_FILE_SIZE_MB = 50

IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = SUPPORTED_EXTENSIONS["docx"]
PPTX_MIME_TYPE = SUPPORTED_EXTENSIONS["pptx"]

# ---------------------------------------------------------------------------
# spaCy
# ---------------------------------------------------------------------------
SPACY_MODEL = "en_core_web_sm"

#: Hard ceiling on characters handed to the summarizer, to bound memory use.
MAX_SUMMARY_INPUT_CHARS = 100_000

# ---------------------------------------------------------------------------
# CrossRef API
# ---------------------------------------------------------------------------
CROSSREF_API_BASE = "https://api.crossref.org/works"
CROSSREF_MAILTO = "placeholder@example.com"  # Replace with real email for Polite Pool

# ---------------------------------------------------------------------------
# Bibliography section detection — header keywords
# ---------------------------------------------------------------------------
BIBLIOGRAPHY_HEADERS: list[str] = [
    "references",
    "bibliography",
    "annotated bibliography",
    "selected bibliography",
    "works cited",
    "literature cited",
    "reference list",
    "references and notes",
    "selected references",
    "sources cited",
    "sources consulted",
    "cited literature",
    "list of references",
    "list of books",
    "reading list",
    "literature",
]

#: Maximum lines from the beginning of a document inspected for title-page declarations.
FRONT_MATTER_MAX_LINES = 120

#: Fraction of trailing lines that must look bibliographic to trigger the
#: density fallback in :mod:`papermint.parsers.bibliography_detector`.
BIBLIOGRAPHY_DENSITY_THRESHOLD = 0.20

#: Fraction of a split that must look like citations for the split to be
#: accepted by :mod:`papermint.parsers.citation_splitter`.
SPLIT_VALIDATION_RATIO = 0.40

#: When the detected bibliography covers at least this share of the document,
#: the document is treated as a reference list rather than a paper.
REFERENCE_ONLY_COVERAGE = 0.80

# ---------------------------------------------------------------------------
# Confidence bands
# ---------------------------------------------------------------------------
#: Score at or above which a citation is considered complete.
CONFIDENCE_HIGH = 0.60

#: Score at or above which a citation is considered partial.
CONFIDENCE_MEDIUM = 0.30

#: Score below which a citation is flagged for human review.
CONFIDENCE_REVIEW = 0.50

# ---------------------------------------------------------------------------
# Summarization defaults
# ---------------------------------------------------------------------------
DEFAULT_SUMMARY_SENTENCES = 5
MAX_SUMMARY_SENTENCES = 10

# ---------------------------------------------------------------------------
# Presentation defaults
# ---------------------------------------------------------------------------
#: Words per page used when a real page count is unavailable.
WORDS_PER_PAGE = 300

#: Citations rendered per page in the results list.
CITATIONS_PER_PAGE = 25

#: Lines shown in the raw-text preview before the reader expands it.
RAW_TEXT_PREVIEW_LINES = 40

# ---------------------------------------------------------------------------
# Export settings
# ---------------------------------------------------------------------------
EXPORT_FORMATS: dict[str, str] = {
    "BibTeX (.bib)": "bib",
    "RIS (.ris)": "ris",
    "CSV (.csv)": "csv",
    "Excel (.xlsx)": "xlsx",
    "Word (.docx)": "docx",
    "PDF (.pdf)": "pdf",
}
