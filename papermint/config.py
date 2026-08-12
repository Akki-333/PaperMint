"""Application-wide constants and configuration for PaperMint."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "PaperMint"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "Extract, parse, and export academic citations from PDFs, images, and documents"
)
APP_ICON = "🌿"
APP_TAGLINE = "Extract · Parse · Export"

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

# ---------------------------------------------------------------------------
# spaCy
# ---------------------------------------------------------------------------
SPACY_MODEL = "en_core_web_sm"

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
    "works cited",
    "literature cited",
    "reference list",
    "references and notes",
    "selected references",
    "sources cited",
    "cited literature",
    "literature",
]

# ---------------------------------------------------------------------------
# Summarization defaults
# ---------------------------------------------------------------------------
DEFAULT_SUMMARY_SENTENCES = 3
MAX_SUMMARY_SENTENCES = 10

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
