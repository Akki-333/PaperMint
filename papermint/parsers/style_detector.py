"""Module for detecting citation styles."""

from __future__ import annotations

import re

from papermint.models import CitationStyle


def detect_style(citations: list[str]) -> tuple[CitationStyle, float]:
    """Detect citation style from sample citations. Returns (style, confidence).

    Args:
        citations: A list of citation strings.

    Returns:
        A tuple containing the detected CitationStyle and a confidence score (0.0 to 1.0).
    """
    if not citations:
        return CitationStyle.UNKNOWN, 0.0

    scores = {
        CitationStyle.APA: 0.0,
        CitationStyle.MLA: 0.0,
        CitationStyle.IEEE: 0.0,
        CitationStyle.CHICAGO: 0.0,
    }

    for cit in citations:
        # --- APA signals ---
        # "Lastname, F." author format
        if re.search(r"[A-Z][a-z]+,\s+[A-Z]\.", cit):
            scores[CitationStyle.APA] += 1.0
        # Year in parentheses: (2020)
        if re.search(r"\(\d{4}\)", cit):
            scores[CitationStyle.APA] += 1.5
        # Ampersand between authors
        if "&" in cit:
            scores[CitationStyle.APA] += 0.5

        # --- IEEE signals ---
        # [N] bracket prefix
        if re.search(r"^\s*\[\d+\]", cit):
            scores[CitationStyle.IEEE] += 2.0
        # Initials-first: "J. A. Smith"
        if re.search(r"[A-Z]\.\s+[A-Z]\.?\s+[A-Z][a-z]+", cit):
            scores[CitationStyle.IEEE] += 1.0
        # vol. and pp. labels
        if re.search(r"vol\.\s*\d+", cit, re.IGNORECASE):
            scores[CitationStyle.IEEE] += 0.5
        if re.search(r"pp?\.\s*\d+", cit, re.IGNORECASE):
            scores[CitationStyle.IEEE] += 0.5

        # --- MLA signals ---
        # Quoted title
        if re.search(r'"[^"]+"', cit) or re.search(r"\u201c[^\u201d]+\u201d", cit):
            scores[CitationStyle.MLA] += 1.0
        # Full first name after comma: "Smith, John"
        if re.search(r"[A-Z][a-z]+,\s+[A-Z][a-z]{2,}", cit):
            scores[CitationStyle.MLA] += 0.5
        # No year in parentheses (MLA puts year at end)
        if not re.search(r"\(\d{4}\)", cit) and re.search(r"\d{4}", cit):
            scores[CitationStyle.MLA] += 0.3

        # --- Chicago signals ---
        # Volume(Issue): Pages format
        if re.search(r"\d+\s*\(\d+\)\s*:\s*\d+", cit):
            scores[CitationStyle.CHICAGO] += 1.5
        # Full first name with period-separated segments
        if re.search(r"[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+", cit):
            scores[CitationStyle.CHICAGO] += 0.5

    # Find the style with the highest score
    best_style = max(scores, key=scores.get)
    best_score = scores[best_style]

    if best_score == 0:
        return CitationStyle.UNKNOWN, 0.0

    # Calculate confidence: ratio of best score to total scores
    total_score = sum(scores.values())
    if total_score == 0:
        return CitationStyle.UNKNOWN, 0.0

    # Confidence is how dominant the winning style is
    confidence = best_score / total_score

    # Must have at least some signal per citation
    avg_signal = best_score / len(citations)
    if avg_signal < 0.3:
        return CitationStyle.UNKNOWN, confidence * 0.5

    return best_style, min(1.0, confidence)
