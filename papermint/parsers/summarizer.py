"""Extractive summarisation of a document's narrative body.

The summariser prefers spaCy for sentence segmentation, but never requires it.
If the model is absent the module falls back to a deterministic regex
segmenter and the same scoring function, so a missing model degrades the
quality of the summary rather than breaking the page.

Downloading a model at request time is deliberately not attempted: it would
stall a user-facing page for minutes with no feedback.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from papermint.config import (
    DEFAULT_SUMMARY_SENTENCES,
    MAX_SUMMARY_INPUT_CHARS,
    SPACY_MODEL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy NLP pipeline
# ---------------------------------------------------------------------------

_nlp: Any | None = None
_nlp_loaded = False

#: Sentence-boundary heuristic used when spaCy is unavailable.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")

#: Abbreviations that must not end a sentence.
_ABBREVIATIONS = re.compile(
    r"\b(?:[A-Z]|Dr|Mr|Mrs|Ms|Prof|St|vs|etc|al|eds?|Fig|No|Vol|pp)\.\s*$",
    re.IGNORECASE,
)

#: Operators that mark a line as a displayed equation rather than a sentence.
#: The multiplication sign is deliberately absent: it is visually ambiguous
#: with the letter x, and the relational operators already catch any line that
#: carries one.
_MATH_OPERATOR = re.compile(r"[=<>±÷≈≠≤≥∑∏∫√∂∇⟨⟩]|\^|\\[a-zA-Z]+\{")

#: Words carrying no topical signal, used by the fallback scorer.
_STOPWORDS = frozenset(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "cannot",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "ought",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    ]
)


def _get_nlp() -> Any | None:
    """Load and cache the spaCy pipeline, or return None if unavailable.

    Returns:
        The loaded pipeline, or None when spaCy or its model is missing.
    """
    global _nlp, _nlp_loaded
    if _nlp_loaded:
        return _nlp

    _nlp_loaded = True
    try:
        import spacy
    except ImportError:
        logger.info("spaCy is not installed; using the built-in sentence segmenter.")
        _nlp = None
        return None

    try:
        _nlp = spacy.load(SPACY_MODEL, disable=["ner", "lemmatizer", "textcat"])
    except OSError:
        logger.warning(
            "The spaCy model %r is not installed. Falling back to the built-in "
            "segmenter. Install it with: python -m spacy download %s",
            SPACY_MODEL,
            SPACY_MODEL,
        )
        _nlp = None
    return _nlp


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------


def _is_reference_line(text: str) -> bool:
    """Check if a line looks like a bibliographic reference rather than prose.

    Args:
        text: One line of text.

    Returns:
        True when the line should be excluded from the summary input.
    """
    text = text.strip()
    if not text:
        return True
    if re.match(r"^\s*\[?\d+\]?\.?\s", text):
        return True
    if re.search(r"10\.\d{4,9}/[^\s]+", text):
        return True
    if len(re.findall(r"[A-Z][a-z]+,\s+[A-Z]\.", text)) >= 2:
        return True
    return bool(re.search(r"\bvol\.\s*\d+.*\bpp?\.\s*\d+", text, re.IGNORECASE))


def _is_equation_like(text: str) -> bool:
    """Check whether a line is mathematics rather than a sentence of prose.

    An appendix of a physics or mathematics paper is mostly displayed
    equations. Scored as prose they win on content-word frequency, because a
    symbol repeated across a derivation looks exactly like a keyword, and the
    summary then reads as a string of fragments rather than the document's
    argument.

    Args:
        text: One line of text.

    Returns:
        True when the line should be excluded from the summary input.
    """
    stripped = text.strip()
    if len(stripped) < 12:
        return True

    alphabetic = sum(1 for character in stripped if character.isalpha())
    if alphabetic < len(stripped) * 0.6:
        return True

    words = re.findall(r"[A-Za-z]{3,}", stripped)
    if len(words) < 3:
        return True
    return bool(_MATH_OPERATOR.search(stripped) and len(words) < 6)


def _clean_for_summary(text: str) -> str:
    """Remove reference lines and structural noise before summarising.

    Args:
        text: The document body.

    Returns:
        A single paragraph of prose suitable for sentence scoring.
    """
    clean_lines = [
        line.strip()
        for line in text.split("\n")
        if not _is_reference_line(line) and not _is_equation_like(line)
    ]
    return " ".join(clean_lines)


def _split_sentences(text: str) -> list[str]:
    """Segment text into sentences without spaCy.

    Args:
        text: Cleaned prose.

    Returns:
        The sentences, in document order.
    """
    sentences: list[str] = []
    buffer = ""
    for fragment in _SENTENCE_BOUNDARY.split(text):
        buffer = f"{buffer} {fragment}".strip() if buffer else fragment
        if not _ABBREVIATIONS.search(buffer):
            sentences.append(buffer)
            buffer = ""
    if buffer:
        sentences.append(buffer)
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _content_words(sentence: str) -> list[str]:
    """Extract lowercase content words from a sentence.

    Args:
        sentence: One sentence.

    Returns:
        The content words, stopwords and short tokens removed.
    """
    return [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", sentence.lower())
        if word not in _STOPWORDS
    ]


def _score_sentences(tokenised: list[list[str]], raw_sentences: list[str]) -> dict[int, float]:
    """Score sentences by normalised content-word frequency and position.

    Args:
        tokenised: Per-sentence lists of lowercase content words.
        raw_sentences: The original sentence strings, used for penalties.

    Returns:
        A mapping of sentence index to score.
    """
    frequencies = Counter(word for sentence in tokenised for word in sentence)
    if not frequencies:
        return {}
    peak = max(frequencies.values())

    scores: dict[int, float] = {}
    total = len(tokenised)
    for index, words in enumerate(tokenised):
        if not words:
            scores[index] = 0.0
            continue

        score = sum(frequencies[word] / peak for word in words) / (len(words) + 1)

        # An abstract opens a paper and a conclusion closes it; both carry the
        # document's thesis more reliably than the middle does. The opening is
        # weighted highest because it states what the document is *about*,
        # which is what a reader wants from a summary.
        position = index / total
        if position < 0.15:
            score *= 1.5
        elif position > 0.85:
            score *= 1.2

        raw = raw_sentences[index]
        if len(raw.split()) < 6:
            score *= 0.3  # headings and captions
        if _is_reference_line(raw):
            score *= 0.1
        if _is_equation_like(raw):
            score *= 0.1  # a derivation is not the document's argument

        scores[index] = score
    return scores


def _select(raw_sentences: list[str], tokenised: list[list[str]], num_sentences: int) -> str:
    """Pick the highest scoring sentences and restore document order.

    Args:
        raw_sentences: The original sentences.
        tokenised: Their content words.
        num_sentences: How many sentences the summary should contain.

    Returns:
        The assembled summary.
    """
    scores = _score_sentences(tokenised, raw_sentences)
    if not scores:
        return " ".join(raw_sentences[:num_sentences])

    ranked = sorted(scores, key=lambda i: scores[i], reverse=True)[:num_sentences]
    return " ".join(raw_sentences[i] for i in sorted(ranked))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def summarize(text: str, num_sentences: int = DEFAULT_SUMMARY_SENTENCES) -> str:
    """Generate an extractive summary of the text.

    The text is first stripped of reference lines and short structural
    fragments, then segmented into sentences and scored by normalised content
    word frequency with a positional boost.

    Args:
        text: The text to summarize.
        num_sentences: The number of sentences to include in the summary.

    Returns:
        The summary, or an empty string when there is nothing to summarise.
    """
    if not text or not text.strip():
        return ""

    clean_text = _clean_for_summary(text) or text.strip()

    if len(clean_text) > MAX_SUMMARY_INPUT_CHARS:
        logger.info(
            "Truncating summary input from %d to %d characters.",
            len(clean_text),
            MAX_SUMMARY_INPUT_CHARS,
        )
        clean_text = clean_text[:MAX_SUMMARY_INPUT_CHARS]

    nlp = _get_nlp()
    raw_sentences: list[str]
    tokenised: list[list[str]]

    if nlp is not None:
        try:
            doc = nlp(clean_text)
            spans = [s for s in doc.sents if s.text.strip()]
            raw_sentences = [s.text.strip() for s in spans]
            tokenised = [
                [
                    token.text.lower()
                    for token in span
                    if not token.is_stop and not token.is_punct and len(token.text) > 2
                ]
                for span in spans
            ]
        except Exception as exc:
            logger.warning("spaCy segmentation failed (%s); using the fallback.", exc)
            raw_sentences = _split_sentences(clean_text)
            tokenised = [_content_words(s) for s in raw_sentences]
    else:
        raw_sentences = _split_sentences(clean_text)
        tokenised = [_content_words(s) for s in raw_sentences]

    if not raw_sentences:
        return ""
    if len(raw_sentences) <= num_sentences:
        return " ".join(raw_sentences)

    return _select(raw_sentences, tokenised, num_sentences)


def summarize_reference_list(citation_count: int, kind_label: str) -> str:
    """Describe a document that is itself a reference list.

    Such a document has no narrative body, so an extractive summary of it
    would just repeat citations back to the reader.

    Args:
        citation_count: How many entries were parsed.
        kind_label: The human-readable document kind.

    Returns:
        A short factual description of the document.
    """
    if citation_count:
        return (
            f"This document is a {kind_label.lower()} rather than a narrative text. "
            f"{citation_count} entries were parsed from it, and each one is listed "
            "under Citations with its extracted fields."
        )
    return (
        f"This document is a {kind_label.lower()}. No individual entries could be "
        "isolated from it, so the full text is available under Raw Text."
    )


__all__ = ["summarize", "summarize_reference_list"]
