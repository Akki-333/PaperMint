"""Parsing of individual citation strings into :class:`Citation` objects.

Field extraction is deliberately deterministic. General-purpose named entity
recognition was removed because it confidently reports content words such as
place names or animal names as human authors, which surfaces in the interface
as obviously wrong data.

Every extractor here follows the same shape: propose candidates in descending
order of reliability, then *validate* each candidate before accepting it. A
rejected candidate leaves the field empty, which the interface can render
honestly, rather than filling it with a plausible-looking fragment.
"""

from __future__ import annotations

import logging
import re

from papermint.models import Author, Citation, CitationStyle, EntryType
from papermint.parsers.text_normalizer import normalize_field, normalize_unicode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared patterns
# ---------------------------------------------------------------------------

_DOI = re.compile(r"10\.\d{4,9}/[^\s,;\])]+")
_URL = re.compile(r"https?://[^\s,;\])]+")
_YEAR_PAREN = re.compile(r"\((?:19|20)\d{2}[a-z]?\)")
_YEAR_BARE = re.compile(r"\b(?:19|20)\d{2}\b")
_ENTRY_PREFIX = re.compile(r"^\s*(?:\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}\.)\s+")
_BLANK_LINE = re.compile(r"\n\s*\n")

#: Nobiliary and patronymic particles that belong to the surname.
_PARTICLE = (
    r"(?:d[eu]l?\s+|de\s+la\s+|van\s+der\s+|van\s+den\s+|van\s+|von\s+|"
    r"la\s+|le\s+|ter\s+|ten\s+|bin\s+|al-)?"
)

#: A surname allowing particles, hyphens, apostrophes and a two-word form.
_SURNAME = rf"{_PARTICLE}[A-Z][\w'-]*(?:[-\s][A-Z][\w'-]+)?"

#: "Smith, J. A." or "Smith, John A." — the inverted form used by APA and MLA.
_INVERTED_NAME = re.compile(rf"({_SURNAME}),\s+((?:[A-Z]\.\s*){{1,4}}|[A-Z][a-z]+(?:\s+[A-Z]\.?)*)")

#: "J. A. Smith" — the initials-first form used by IEEE.
_DIRECT_NAME = re.compile(rf"((?:[A-Z]\.\s*){{1,4}})({_SURNAME})")

#: A trailing "and Robert B. Doe" after an inverted first author.
_TRAILING_DIRECT = re.compile(rf"(?:\band\b|&)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)*\s+{_SURNAME})")

#: Words that mark a string as a publisher rather than a journal.
_PUBLISHER_WORDS = (
    "press",
    "publishing",
    "publishers",
    "publications",
    "books",
    "verlag",
    "editions",
)

#: Tokens that disqualify a string from being a title.
_TITLE_STOP_WORDS = (
    "retrieved from",
    "available at",
    "accessed on",
    "doi:",
    "isbn",
)

#: A locator such as "15(2), 103-115" that must never become a title.
_LOCATOR_ONLY = re.compile(r"^[\d\s,;:()\[\]/.-]*$")

#: Volume, issue and page labels.
_VOLUME_LABEL = re.compile(r"\bvol(?:ume)?\.?\s*(\d{1,4})", re.IGNORECASE)
_ISSUE_LABEL = re.compile(r"\b(?:no|iss(?:ue)?)\.?\s*(\d{1,4})", re.IGNORECASE)
_PAGES_LABEL = re.compile(r"\bpp?\.?\s*(\d{1,5}\s*-\s*\d{1,5}|\d{1,5})\b", re.IGNORECASE)
_VOLUME_ISSUE_COMBO = re.compile(r"\b(\d{1,4})\s*\((\d{1,4})\)")
_PAGE_RANGE = re.compile(r"\b(\d{1,5})\s*-\s*(\d{1,5})\b")


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------


def _extract_doi(text: str) -> str:
    """Extract a DOI from citation text.

    Args:
        text: The citation text.

    Returns:
        The DOI, or an empty string.
    """
    match = _DOI.search(text)
    if not match:
        return ""
    return match.group(0).rstrip(".,;")


def _extract_url(text: str) -> str:
    """Extract the first URL from citation text.

    Args:
        text: The citation text.

    Returns:
        The URL, or an empty string.
    """
    match = _URL.search(text)
    return match.group(0).rstrip(".,;") if match else ""


def _extract_year(text: str) -> str:
    """Extract the publication year from citation text.

    A parenthesised year is preferred because it is unambiguous. A bare
    four-digit token is accepted only when it is not part of a DOI, a URL or a
    numeric range.

    Args:
        text: The citation text.

    Returns:
        A four-digit year, or an empty string.
    """
    paren = _YEAR_PAREN.search(text)
    if paren:
        return re.search(r"((?:19|20)\d{2})", paren.group(0)).group(1)

    masked = _DOI.sub(" ", _URL.sub(" ", text))
    for match in _YEAR_BARE.finditer(masked):
        start, end = match.span()
        before = masked[max(0, start - 1) : start]
        after = masked[end : end + 1]
        if before == "-" or after == "-":
            continue  # part of a range such as 1990-1995
        return match.group(0)
    return ""


def _author_region(text: str) -> str:
    """Isolate the leading span of a citation that holds the author names.

    Args:
        text: The citation header.

    Returns:
        The substring believed to contain only author names.
    """
    text = _ENTRY_PREFIX.sub("", text)

    for pattern in (_YEAR_PAREN, re.compile(r'"'), _YEAR_BARE):
        match = pattern.search(text)
        if match and match.start() > 0:
            return text[: match.start()]

    head, _, _ = text.partition(". ")
    return head


def _dedupe_authors(authors: list[Author]) -> list[Author]:
    """Remove duplicate authors while preserving order.

    Args:
        authors: The parsed authors.

    Returns:
        The de-duplicated list.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Author] = []
    for author in authors:
        key = (author.family.lower(), author.given.lower())
        if key not in seen and (author.family or author.given):
            seen.add(key)
            unique.append(author)
    return unique


def _clean_given(value: str) -> str:
    """Tidy a given-name fragment captured by a name regex.

    Args:
        value: The raw capture.

    Returns:
        The cleaned given name.
    """
    return value.strip().rstrip(",&").strip()


def _extract_authors_apa(text: str) -> list[Author]:
    """Parse APA-style authors: ``Smith, J. A., & Doe, R. B. (YYYY)``.

    Args:
        text: The citation header.

    Returns:
        The parsed authors, in citation order.
    """
    region = _author_region(text)
    authors = [
        Author(family=m.group(1).strip(), given=_clean_given(m.group(2)))
        for m in _INVERTED_NAME.finditer(region)
    ]

    for match in _TRAILING_DIRECT.finditer(region):
        words = match.group(1).split()
        if len(words) >= 2:
            authors.append(Author(given=" ".join(words[:-1]), family=words[-1]))

    return _dedupe_authors(authors)


def _extract_authors_ieee(text: str) -> list[Author]:
    """Parse IEEE-style authors: ``J. A. Smith and R. B. Doe, "Title"``.

    Args:
        text: The citation header.

    Returns:
        The parsed authors, in citation order.
    """
    region = _author_region(text)
    authors = [
        Author(given=_clean_given(m.group(1)), family=m.group(2).strip())
        for m in _DIRECT_NAME.finditer(region)
    ]
    if authors:
        return _dedupe_authors(authors)
    return _extract_authors_apa(text)


def _extract_authors_generic(text: str) -> list[Author]:
    """Extract authors without knowing the citation style.

    The inverted form is tried first because it is the least ambiguous, then
    the initials-first form. When neither matches, no authors are reported;
    guessing from capitalised words invents names that are not in the source.

    Args:
        text: The citation header.

    Returns:
        The parsed authors, possibly empty.
    """
    inverted = _extract_authors_apa(text)
    if inverted:
        return inverted
    return _dedupe_authors(
        [
            Author(given=_clean_given(m.group(1)), family=m.group(2).strip())
            for m in _DIRECT_NAME.finditer(_author_region(text))
        ]
    )


def _is_plausible_title(candidate: str, *, author_region: str = "") -> bool:
    """Decide whether a candidate string can be shown as a title.

    Args:
        candidate: The proposed title.
        author_region: The author span, used to reject author echoes.

    Returns:
        True when the candidate reads like a real title.
    """
    candidate = candidate.strip()
    if not 6 <= len(candidate) <= 300:
        return False
    if _LOCATOR_ONLY.match(candidate):
        return False
    if _DOI.search(candidate) or _URL.search(candidate):
        return False

    lowered = candidate.lower()
    if any(stop in lowered for stop in _TITLE_STOP_WORDS):
        return False

    words = re.findall(r"[A-Za-z]{3,}", candidate)
    if len(words) < 2:
        return False

    if author_region and candidate.strip(" .,") in author_region:
        return False

    # A run of initials such as "Smith, J. A., & Doe, R. B" is an author list.
    initials = len(re.findall(r"\b[A-Z]\.", candidate))
    return not (initials >= 2 and len(words) < 5)


def _extract_title(text: str, style: CitationStyle) -> str:
    """Extract the title from citation text using ordered strategies.

    Args:
        text: The citation header.
        style: The detected citation style, used only for logging.

    Returns:
        The title, or an empty string when no candidate is plausible.
    """
    region = _author_region(text)
    candidates: list[str] = []

    # 1. A quoted title, used by IEEE and MLA.
    quoted = re.search(r'"([^"]{4,300})"', text)
    if quoted:
        candidates.append(quoted.group(1))

    # 2. APA: the sentence immediately after a parenthesised year.
    after_paren = re.search(r"\((?:19|20)\d{2}[a-z]?\)\.?\s*", text)
    if after_paren:
        tail = text[after_paren.end() :].strip()
        candidates.append(re.split(r"\.\s|\.$", tail, maxsplit=1)[0])

    # 3. Chicago and older styles: "Author. YYYY. Title. Publisher."
    after_bare = re.search(r"[.,]\s*(?:19|20)\d{2}[a-z]?\.\s+", text)
    if after_bare:
        tail = text[after_bare.end() :].strip()
        candidates.append(re.split(r"\.\s|\.$", tail, maxsplit=1)[0])

    # 4. An all-capitals title, common in mid-century catalogues.
    caps = re.search(r"(?:^|[.\s])([A-Z][A-Z\s\-',:]{8,}[A-Z])(?=[\s.]|$)", text)
    if caps:
        shout = caps.group(1).strip()
        if not re.fullmatch(r"[A-Z]+\s+(?:CO|INC|LTD|PRESS|PUBLISHING)", shout):
            candidates.append(shout)

    # 5. Fallback: the longest sentence that is not the author block.
    sentences = [s.strip() for s in re.split(r"\.\s+", text) if len(s.strip()) > 10]
    if len(sentences) >= 2:
        candidates.append(max(sentences[1:], key=len))

    for candidate in candidates:
        cleaned = normalize_field(candidate).strip('"').strip()
        if _is_plausible_title(cleaned, author_region=region):
            return cleaned

    logger.debug("No plausible title found in: %.80s", text)
    return ""


def _looks_like_publisher(value: str) -> bool:
    """Whether a venue string names a publisher rather than a journal.

    Args:
        value: The candidate venue.

    Returns:
        True when the string carries a publisher keyword.
    """
    lowered = value.lower()
    return any(word in lowered for word in _PUBLISHER_WORDS)


def _extract_journal(text: str, *, title: str = "") -> str:
    """Extract the journal or container title from citation text.

    Args:
        text: The citation header.
        title: The already-extracted title, excluded from the result.

    Returns:
        The journal name, or an empty string.
    """
    search_space = text
    if title and title in text:
        search_space = text[text.index(title) + len(title) :]

    candidates: list[str] = []

    # "Journal of Bibliometrics, 15(2), 103-115"
    match = re.search(
        r"([A-Z][A-Za-z&.\s-]{3,80}?)\s*,\s*(?:vol\.?\s*)?\d{1,4}\s*[(,]",
        search_space,
    )
    if match:
        candidates.append(match.group(1))

    # "Journal of AI, vol. 15" or "IEEE Transactions, vol. 32"
    match = re.search(r"([A-Z][A-Za-z&.\s-]{3,80}?)\s*,\s*vol\.?\s*\d", search_space, re.IGNORECASE)
    if match:
        candidates.append(match.group(1))

    # "In Proceedings of ..." for chapters and conference papers.
    match = re.search(r"\bIn\s+([A-Z][A-Za-z&:,\s-]{5,80})", search_space)
    if match:
        candidates.append(match.group(1))

    for candidate in candidates:
        cleaned = normalize_field(candidate, max_length=120)
        if len(cleaned) < 4 or _LOCATOR_ONLY.match(cleaned):
            continue
        if title and cleaned.lower() in title.lower():
            continue
        if _looks_like_publisher(cleaned):
            continue
        return cleaned
    return ""


def _extract_volume_issue_pages(text: str) -> tuple[str, str, str]:
    """Extract volume, issue and page range from citation text.

    Guards reject the two mistakes that most often produce nonsense output: a
    year range read as a page range, and DOI digits read as a volume.

    Args:
        text: The citation header.

    Returns:
        A ``(volume, issue, pages)`` triple; each element may be empty.
    """
    masked = _DOI.sub(" ", _URL.sub(" ", text))
    volume = issue = pages = ""

    vol_match = _VOLUME_LABEL.search(masked)
    if vol_match:
        volume = vol_match.group(1)

    issue_match = _ISSUE_LABEL.search(masked)
    if issue_match:
        issue = issue_match.group(1)

    pages_match = _PAGES_LABEL.search(masked)
    if pages_match:
        pages = pages_match.group(1).replace(" ", "")

    if not volume or not issue:
        year_free = _YEAR_PAREN.sub(" ", masked)
        combo = _VOLUME_ISSUE_COMBO.search(year_free)
        if combo:
            volume = volume or combo.group(1)
            issue = issue or combo.group(2)

    if not pages:
        for match in _PAGE_RANGE.finditer(masked):
            first, last = int(match.group(1)), int(match.group(2))
            if last <= first:
                continue
            # A span of two four-digit numbers in the calendar range is a date
            # range inside a title, not a page range.
            both_four_digit = len(match.group(1)) == 4 and len(match.group(2)) == 4
            if both_four_digit and first >= 1000 and last <= 2100:
                continue
            # Real page ranges are short; anything wider is a numeric artefact.
            if (last - first) > 500:
                continue
            pages = f"{first}-{last}"
            break

    return volume, issue, pages


def _extract_publisher(text: str, *, title: str = "") -> str:
    """Extract the publisher from citation text.

    Args:
        text: The citation header.
        title: The already-extracted title, excluded from the result.

    Returns:
        The publisher name, or an empty string.
    """
    search_space = text
    if title and title in text:
        search_space = text[text.index(title) + len(title) :]

    patterns = (
        r"(?:Published\s+by|Publisher:?)\s*([A-Z][A-Za-z&.\s-]{2,60})",
        (
            r"([A-Z][A-Za-z&.\s-]{0,40}?(?:University\s+Press|Press|Publishing|"
            r"Publishers|Publications|Books|Verlag))"
        ),
        r"([A-Z][A-Za-z&.\s-]{2,40}?(?:Co\.|Inc\.|Ltd\.))",
    )

    for pattern in patterns:
        match = re.search(pattern, search_space)
        if not match:
            continue
        cleaned = normalize_field(match.group(1), max_length=80)
        if len(cleaned) > 2 and (not title or cleaned.lower() not in title.lower()):
            return cleaned
    return ""


def _detect_entry_type(text: str, citation: Citation | None = None) -> EntryType:
    """Detect the bibliographic entry type.

    When a populated citation is supplied the decision also uses the extracted
    fields, so a work with a publisher and no volume is recognised as a book
    even though its text contains no keyword such as "Press".

    Args:
        text: The citation text.
        citation: The citation after field extraction, when available.

    Returns:
        The most specific matching entry type.
    """
    lowered = text.lower()
    if any(k in lowered for k in ("proceedings", "conference", "symposium", "workshop")):
        return EntryType.INPROCEEDINGS
    if any(k in lowered for k in ("thesis", "dissertation")):
        return EntryType.THESIS
    if any(k in lowered for k in ("technical report", "tech. rep.", "report no.")):
        return EntryType.REPORT
    if "chapter" in lowered and re.search(r"\bin\s+[A-Z]", text):
        return EntryType.INCOLLECTION
    if any(k in lowered for k in ("press", "publisher", "edition", "chapter")):
        return EntryType.BOOK

    if citation is not None:
        if citation.journal or citation.volume:
            return EntryType.ARTICLE
        if citation.publisher:
            return EntryType.BOOK

    if re.search(r"vol\.?\s*\d|\d+\s*\(\d+\)|pp?\.\s*\d", lowered):
        return EntryType.ARTICLE
    return EntryType.MISC


def _split_header(text: str) -> str:
    """Isolate the bibliographic header from any annotation prose.

    In an annotated bibliography each entry is a citation followed by one or
    more descriptive paragraphs. Parsing the whole block would let a quoted
    phrase inside the annotation win the title strategy, so only the leading
    block is used for field extraction.

    Args:
        text: The full entry, header plus annotation.

    Returns:
        The citation header.
    """
    blocks = _BLANK_LINE.split(text.strip())
    header = blocks[0] if blocks else text

    if len(blocks) == 1:
        lines = [ln for ln in header.split("\n") if ln.strip()]
        if len(lines) > 3:
            tail_words = len(" ".join(lines[3:]).split())
            if tail_words >= 40:
                return "\n".join(lines[:3])
    return header


def score_citation(citation: Citation) -> float:
    """Score how completely a citation was parsed.

    Exposed publicly so that the interface can recompute confidence after a
    reader corrects a field by hand, keeping the badge honest.

    Args:
        citation: The populated citation.

    Returns:
        A normalised score between 0.0 and 1.0.
    """
    core = 5  # title, authors, year, doi, venue
    found = sum(
        1
        for present in (
            citation.title,
            citation.authors,
            citation.year,
            citation.doi,
            citation.journal or citation.publisher,
        )
        if present
    )

    bonus = 0.0
    if citation.volume:
        bonus += 0.5
    if citation.pages:
        bonus += 0.5

    return min(1.0, (found + bonus) / core)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_citation(text: str, style: CitationStyle = CitationStyle.UNKNOWN) -> Citation:
    """Parse a single citation string into a :class:`Citation` object.

    Args:
        text: The citation string, header plus any annotation.
        style: The detected or assumed citation style.

    Returns:
        A populated :class:`Citation`. Fields that could not be extracted
        confidently are left empty rather than filled with a guess.
    """
    if not text or not text.strip():
        return Citation(raw_text=text, confidence=0.0)

    raw = normalize_unicode(text)
    citation = Citation(
        raw_text=raw.strip(),
        style=style,
        entry_type=_detect_entry_type(raw),
        confidence=0.0,
    )

    # A DOI or URL may sit anywhere in the entry, including the annotation.
    citation.doi = _extract_doi(raw)
    citation.url = _extract_url(raw)

    header = _split_header(raw)

    citation.year = _extract_year(header)
    citation.title = _extract_title(header, style)

    if style is CitationStyle.APA:
        authors = _extract_authors_apa(header)
    elif style is CitationStyle.IEEE:
        authors = _extract_authors_ieee(header)
    else:
        authors = _extract_authors_generic(header)
    citation.authors = authors

    citation.journal = _extract_journal(header, title=citation.title)
    citation.volume, citation.issue, citation.pages = _extract_volume_issue_pages(header)
    citation.publisher = _extract_publisher(header, title=citation.title)

    if citation.journal and _looks_like_publisher(citation.journal):
        citation.publisher = citation.publisher or citation.journal
        citation.journal = ""

    citation.entry_type = _detect_entry_type(raw, citation)
    citation.confidence = score_citation(citation)
    return citation


__all__ = ["parse_citation", "score_citation"]
