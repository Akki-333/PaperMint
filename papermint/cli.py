"""Headless command line interface.

This module exists to prove, and to keep proving, that the engine is
independent of its interface. It runs the same
:class:`~papermint.pipeline.PipelineService` the web application uses, imports
nothing from Streamlit, and works in a terminal, a container or a continuous
integration job.

Usage::

    papermint paper.pdf
    papermint *.pdf --format bibtex --out references.bib
    papermint catalogue.pdf --force-parse --json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, TextIO

from papermint.config import APP_NAME, APP_VERSION
from papermint.errors import PaperMintError
from papermint.exporters.bibtex_exporter import export_bibtex
from papermint.exporters.csv_exporter import export_csv
from papermint.exporters.ris_exporter import export_ris
from papermint.models import BatchResult, Citation
from papermint.pipeline import DocumentInput, PipelineOptions, PipelineService

logger = logging.getLogger(__name__)

#: Text serialisers available from the command line.
_WRITERS = {
    "bibtex": export_bibtex,
    "ris": export_ris,
    "csv": export_csv,
}


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(
        prog="papermint",
        description=f"{APP_NAME} {APP_VERSION} - extract citations from documents.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="Documents to process.")
    parser.add_argument(
        "--format",
        choices=sorted(_WRITERS),
        default="bibtex",
        help="Output format for extracted references (default: bibtex).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write the references to this file instead of standard output.",
    )
    parser.add_argument(
        "--force-parse",
        action="store_true",
        help="Treat every document as a bibliography, skipping detection.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the full structured result as JSON.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-file report on standard error.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log every pipeline stage at debug level.",
    )
    return parser


def _read_documents(paths: list[Path]) -> tuple[list[DocumentInput], list[str]]:
    """Load the requested files from disk.

    Args:
        paths: The paths named on the command line.

    Returns:
        A ``(documents, problems)`` pair; unreadable paths are reported rather
        than raising.
    """
    documents: list[DocumentInput] = []
    problems: list[str] = []

    for path in paths:
        if not path.is_file():
            problems.append(f"{path}: not a file")
            continue
        try:
            documents.append(DocumentInput(filename=path.name, data=path.read_bytes()))
        except OSError as exc:
            problems.append(f"{path}: {exc}")
    return documents, problems


def _report(result: BatchResult, stream: TextIO) -> None:
    """Write a per-file summary of the run.

    Args:
        result: The completed batch.
        stream: The text stream to write to.
    """
    for entry in result.files:
        if not entry.succeeded or entry.result is None:
            stream.write(f"  {entry.filename}: failed - {entry.error}\n")
            continue
        document = entry.result
        stream.write(
            f"  {entry.filename}: {document.citation_count} references"
            f" · {document.document_kind.label}"
            f" · {document.detected_style.label}"
            f" · {document.average_confidence:.0%} coverage\n"
        )

    stream.write(
        f"\n{result.citation_count} references from {result.success_count}"
        f" of {result.file_count} files in {result.duration_ms / 1000:.2f}s\n"
    )


def _payload(result: BatchResult, citations: list[Citation], args: Any) -> str:
    """Build the text the run should emit.

    Args:
        result: The completed batch.
        citations: Every citation collected across the run.
        args: The parsed command line arguments.

    Returns:
        The serialised output.
    """
    if args.as_json:
        return json.dumps(
            {
                "files": [
                    {
                        "filename": entry.filename,
                        "error": entry.error,
                        "result": entry.result.model_dump(mode="json") if entry.result else None,
                    }
                    for entry in result.files
                ],
                "citation_count": result.citation_count,
                "duration_ms": result.duration_ms,
            },
            indent=2,
        )
    return _WRITERS[args.format](citations)


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        A process exit code: 0 on success, 1 when a file failed, 2 when
        nothing could be read at all.
    """
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    documents, problems = _read_documents(args.files)
    for problem in problems:
        sys.stderr.write(f"  {problem}\n")

    if not documents:
        sys.stderr.write("No readable documents were given.\n")
        return 2

    options = PipelineOptions(force_parse=args.force_parse)
    try:
        result = PipelineService().process_batch(documents, options)
    except PaperMintError as exc:
        sys.stderr.write(f"Processing failed: {exc}\n")
        return 2

    if not args.quiet:
        _report(result, sys.stderr)

    payload = _payload(result, result.citations, args)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
        if not args.quiet:
            sys.stderr.write(f"Wrote {args.out}\n")
    else:
        sys.stdout.write(f"{payload}\n")

    return 1 if (result.error_count or problems) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
