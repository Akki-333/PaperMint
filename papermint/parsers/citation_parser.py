"""Parsing of individual citation strings into :class:`Citation` objects.

Field extraction is deliberately deterministic. General-purpose named entity
recognition was removed because it confidently reports content words such as
place names or animal names as human authors, which surfaces in the interface
as obviously wrong data.

Every extractor here follows the same shape: propose candidates in descending
order of reliability, then *validate* each candidate before accepting it. A
rejected candidate leaves the field empty, which the interface can render
honestly, rather than filling it with a plausible-looking fragment.

Two rules keep the output truthful.

**Author parsing is anchored.** The walk starts at the first character of the
entry, matches one complete name, steps over the separator, and stops at the
first thing that is not a name. An unanchored search finds names anywhere, so
on ``A. Eckardt, C. Weiss, and M. Holthaus, Superfluid-insulator transition``
it paired ``Eckardt`` with the *next* author's initial and ``Holthaus`` with
the *title's* first word, inventing two people who are not in the source.

**Everything after the authors is parsed from a known offset.** Because the
walk reports where the author list ends, the title no longer has to be guessed
by splitting on full stops, which broke on both author initials and journal
abbreviations such as ``Phys. Rev. Lett.``
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

#: An arXiv identifier, with or without a version suffix.
_ARXIV = re.compile(r"\barXiv:\s*(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)

#: Nobiliary and patronymic particles that belong to the surname.
_PARTICLE = (
    r"(?:d[eu]l?\s+|de\s+la\s+|van\s+der\s+|van\s+den\s+|van\s+|von\s+|"
    r"la\s+|le\s+|ter\s+|ten\s+|bin\s+|al-)?"
)

#: A surname allowing particles, hyphens, apostrophes and a two-word form.
_SURNAME = rf"{_PARTICLE}[A-Z][\w'-]*(?:[-\s][A-Z][\w'-]+)?"

#: A run of initials such as "J." or "V. M." or "C. D. E.".
_INITIALS = r"(?:[A-Z]\.[ \t]*){1,4}"

_INVERTED_UNIT = re.compile(
    rf"({_SURNAME}),[ \t]+({_INITIALS}|[A-Z][a-z]+(?:[ \t]+[A-Z]\.(?![a-z])|[ \t]+[A-Z]\b(?![A-Za-z]))*)"
)

#: One author written initials-first: "J. A. Smith", "V. M. Bastidas".
_DIRECT_UNIT = re.compile(rf"({_INITIALS})({_SURNAME})")

#: One author written out in full: "Robert B. Doe". Only ever accepted after an
#: explicit conjunction, because otherwise a title such as "Neural Networks For
#: Text" matches it and becomes a person.
_FULL_NAME_UNIT = re.compile(rf"([A-Z][a-z]+(?:[ \t]+[A-Z]\.?)*)[ \t]+({_SURNAME})")

#: What may sit between two author names.
_AUTHOR_SEP = re.compile(r"[ \t]*(?:,[ \t]*(?:and[ \t]+|&[ \t]*)?|[ \t]+and[ \t]+|[ \t]*&[ \t]*)")

#: A conjunction inside a separator, which licenses the written-out name form.
_CONJUNCTION = re.compile(r"\band\b|&")

#: A trailing "et al." that closes an author list.
_ET_AL = re.compile(r"[ \t]*,?[ \t]*et[ \t]+al\.?", re.IGNORECASE)

#: The closing "Journal Abbrev. Volume, Pages (Year)." of a numbered reference,
#: which is the dominant form in physics, chemistry and the life sciences.
_VENUE_TAIL = re.compile(
    r",[ \t]*(?P<journal>[A-Z][A-Za-z.&\- ]{1,60}?)[ \t]+(?P<volume>\d{1,4}),[ \t]*"
    r"(?P<pages>[A-Za-z]?\d[\w-]*)[ \t]*\((?P<year>(?:19|20)\d{2})\)\.?[ \t]*$"
)

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

#: A single initial closing a fragment, which is never a sentence end.
_INITIAL_END = re.compile(r"\b[A-Z]\.$")

#: Scholarly abbreviations that are never a sentence end either.
_ABBREV_END = re.compile(
    r"\b(?:phys|rev|lett|nucl|astrophys|chem|biol|proc|natl|acad|sci|ann|appl|math|"
    r"comput|eur|int|mod|opt|trans|soc|suppl|ser|adv|commun|res|technol|instrum|"
    r"vol|no|pp|ed|eds|al|fig|eq|ref|dr|prof|mr|mrs|ms|st|inc|ltd|co|univ|press|"
    r"jr|sr|repr|vols|pt|ch|sec|approx|cf|viz)\.$",
    re.IGNORECASE,
)

#: "136 p." — the monograph page count, written after the number rather than
#: before it as "pp. 136".
_MONOGRAPH_PAGES = re.compile(r"\b(\d{1,4})\s*pp?\.?(?=\s|$)", re.IGNORECASE)

#: A contributor credit, which marks a line as part of a catalogue entry.
_CONTRIBUTOR = re.compile(
    r"\b(?:Illus\.|Comp\.|Ed\.|Eds\.|Trans\.|Edited|Compiled|Translated)\s+by\b",
    re.IGNORECASE,
)

#: "Abelard-Schuman. 1968." — the imprint immediately before the year, which is
#: how a monograph names its publisher when no keyword such as "Press" appears.
#: A full stop is deliberately excluded from the name tokens: with it, the run
#: spanned the preceding sentence and "Illus. by Ray Cruz. Abelard-Schuman."
#: reported the illustrator as the publisher.
_IMPRINT_BEFORE_YEAR = re.compile(
    r"([A-Z][\w&'-]*(?:[\s-][A-Z][\w&'-]*){0,3})\.\s*(?:19|20)\d{2}\b"
)

#: Words on a line, at or above which it may be annotation prose.
_ANNOTATION_LINE_WORDS = 8

#: Volume, issue and page labels.
_VOLUME_LABEL = re.compile(r"\bvol(?:ume)?\.?\s*(\d{1,4})", re.IGNORECASE)
_ISSUE_LABEL = re.compile(r"\b(?:no|iss(?:ue)?)\.?\s*(\d{1,4})", re.IGNORECASE)
_PAGES_LABEL = re.compile(r"\bpp?\.?\s*(\d{1,5}\s*-\s*\d{1,5}|\d{1,5})\b", re.IGNORECASE)
_VOLUME_ISSUE_COMBO = re.compile(r"\b(\d{1,4})\s*\((\d{1,4})\)")
_PAGE_RANGE = re.compile(r"\b(\d{1,5})\s*-\s*(\d{1,5})\b")


# ---------------------------------------------------------------------------
# Author extraction
# ---------------------------------------------------------------------------


def _clean_given(value: str) -> str:
    """Tidy a given-name fragment captured by a name regex.

    Args:
        value: The raw capture.

    Returns:
        The cleaned given name.
    """
    return value.strip().rstrip(",&").strip()


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


def _match_author(
    region: str, position: int, *, allow_full_name: bool
) -> tuple[Author, int] | None:
    """Match exactly one author name anchored at a position.

    Args:
        region: The text being walked.
        position: Where in ``region`` the name must begin.
        allow_full_name: Whether a written-out "Robert B. Doe" form is allowed
            here. It is only safe directly after a conjunction.

    Returns:
        An ``(author, end_offset)`` pair, or None when no name starts here.
    """
    inverted = _INVERTED_UNIT.match(region, position)
    if inverted:
        author = Author(
            family=inverted.group(1).strip(),
            given=_clean_given(inverted.group(2)),
        )
        return author, inverted.end()

    if allow_full_name:
        full = _FULL_NAME_UNIT.match(region, position)
        if full:
            author = Author(given=_clean_given(full.group(1)), family=full.group(2).strip())
            return author, full.end()

    direct = _DIRECT_UNIT.match(region, position)
    if direct:
        author = Author(given=_clean_given(direct.group(1)), family=direct.group(2).strip())
        return author, direct.end()

    return None


def _author_span(region: str) -> tuple[list[Author], int]:
    """Walk the leading author list and report where it ends.

    The walk is anchored: it matches a name at the current position, steps over
    a separator, and stops the moment the next position does not begin a name.
    This is what prevents a surname being paired with the following author's
    initial, or with the first word of the title.

    Args:
        region: The entry text with any numeric prefix already removed.

    Returns:
        An ``(authors, end_offset)`` pair. ``end_offset`` is the index just past
        the last accepted name, or 0 when the entry does not open with one.
    """
    authors: list[Author] = []
    position = 0
    consumed = 0

    # The written-out form is refused at the head of an entry. Every style that
    # writes a first author in full also inverts it ("Smith, John A."), whereas
    # any title-case heading matches the written-out pattern: "National Digital
    # Literacy Scheme" became a person called National Digital Literacy. The
    # form is only reachable after an explicit "and", which is where a genuine
    # trailing author such as "and Robert B. Doe" appears.
    allow_full_name = False

    while True:
        matched = _match_author(region, position, allow_full_name=allow_full_name)
        if matched is None:
            break
        author, end = matched
        authors.append(author)
        consumed = end
        position = end

        trailing = _ET_AL.match(region, position)
        if trailing:
            consumed = trailing.end()
            break

        separator = _AUTHOR_SEP.match(region, position)
        if separator is None:
            break
        allow_full_name = bool(_CONJUNCTION.search(separator.group(0)))
        position = separator.end()

    return _dedupe_authors(authors), consumed


def _extract_authors_apa(text: str) -> list[Author]:
    """Parse APA-style authors: ``Smith, J. A., & Doe, R. B. (YYYY)``.

    Args:
        text: The citation header.

    Returns:
        The parsed authors, in citation order.
    """
    return _author_span(_ENTRY_PREFIX.sub("", text))[0]


def _extract_authors_ieee(text: str) -> list[Author]:
    """Parse IEEE-style authors: ``J. A. Smith and R. B. Doe, "Title"``.

    Args:
        text: The citation header.

    Returns:
        The parsed authors, in citation order.
    """
    return _author_span(_ENTRY_PREFIX.sub("", text))[0]


def _extract_authors_generic(text: str) -> list[Author]:
    """Extract authors without knowing the citation style.

    Args:
        text: The citation header.

    Returns:
        The parsed authors, possibly empty.
    """
    return _author_span(_ENTRY_PREFIX.sub("", text))[0]


# ---------------------------------------------------------------------------
# Identifier extraction
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
    four-digit token is accepted only when it is not part of a DOI, a URL, an
    arXiv identifier or a numeric range.

    Args:
        text: The citation text.

    Returns:
        A four-digit year, or an empty string.
    """
    paren = _YEAR_PAREN.search(text)
    if paren:
        return re.search(r"((?:19|20)\d{2})", paren.group(0)).group(1)

    masked = _ARXIV.sub(" ", _DOI.sub(" ", _URL.sub(" ", text)))
    for match in _YEAR_BARE.finditer(masked):
        start, end = match.span()
        before = masked[max(0, start - 1) : start]
        after = masked[end : end + 1]
        if before == "-" or after == "-":
            continue  # part of a range such as 1990-1995
        return match.group(0)
    return ""


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------


def _safe_sentences(text: str) -> list[str]:
    """Split text into sentences without breaking on initials or abbreviations.

    A naive split on ``". "`` cuts ``V. M. Bastidas`` into three pieces and
    ``Phys. Rev. Lett.`` into three more, which is how a title used to be
    reported as starting mid-name and ending mid-journal.

    Args:
        text: The text to segment.

    Returns:
        The sentences, in order.
    """
    sentences: list[str] = []
    buffer = ""
    for fragment in re.split(r"(?<=[.!?])\s+", text):
        buffer = f"{buffer} {fragment}".strip() if buffer else fragment
        if _INITIAL_END.search(buffer) or _ABBREV_END.search(buffer):
            continue
        sentences.append(buffer)
        buffer = ""
    if buffer:
        sentences.append(buffer)
    return [s.strip() for s in sentences if s.strip()]


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
    if _DOI.search(candidate) or _URL.search(candidate) or _ARXIV.search(candidate):
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


def _extract_title(
    body: str,
    remainder: str,
    author_region: str,
    tail: re.Match[str] | None,
    arxiv: re.Match[str] | None,
) -> str:
    """Extract the title using strategies ordered by reliability.

    Args:
        body: The entry with its numeric prefix removed.
        remainder: The part of ``body`` after the author list.
        author_region: The author span, used to reject author echoes.
        tail: A match of the closing "Journal Volume, Pages (Year)" form.
        arxiv: A match of an arXiv identifier inside ``remainder``.

    Returns:
        The title, or an empty string when no candidate is plausible.
    """
    candidates: list[str] = []

    # 1. A quoted title, used by IEEE and MLA.
    quoted = re.search(r'"([^"]{4,300})"', body)
    if quoted:
        candidates.append(quoted.group(1))

    # 2. The numbered form: everything between the authors and the journal.
    if tail is not None:
        candidates.append(remainder[: tail.start()])

    # 3. A preprint: everything between the authors and the identifier.
    if arxiv is not None:
        candidates.append(remainder[: arxiv.start()])

    # 4. APA: the sentence immediately after a parenthesised year.
    after_paren = re.search(r"\((?:19|20)\d{2}[a-z]?\)\.?\s*", body)
    if after_paren:
        following = body[after_paren.end() :].strip()
        candidates.append(re.split(r"\.\s|\.$", following, maxsplit=1)[0])

    # 5. Chicago and older styles: "Author. YYYY. Title. Publisher."
    after_bare = re.search(r"[.,]\s*(?:19|20)\d{2}[a-z]?\.\s+", body)
    if after_bare:
        following = body[after_bare.end() :].strip()
        candidates.append(re.split(r"\.\s|\.$", following, maxsplit=1)[0])

    # 6. An all-capitals title, common in mid-century catalogues.
    caps = re.search(r"(?:^|[.\s])([A-Z][A-Z\s\-',:]{8,}[A-Z])(?=[\s.]|$)", body)
    if caps:
        shout = caps.group(1).strip()
        if not re.fullmatch(r"[A-Z]+\s+(?:CO|INC|LTD|PRESS|PUBLISHING)", shout):
            candidates.append(shout)

    # 7. The monograph form: "Surname, Given. Title. Imprint. Year. NNN p."
    #    The title is the sentence directly after the author list, not the
    #    longest one, which in a catalogue entry is the annotation.
    sentences = [s for s in _safe_sentences(remainder) if len(s) > 10]
    if sentences:
        candidates.append(sentences[0])

    # 8. Fallback: the longest sentence after the authors. Segmentation is
    #    abbreviation-aware, so it can no longer cut through a name or a
    #    journal abbreviation.
    if sentences:
        candidates.append(max(sentences, key=len))

    for candidate in candidates:
        cleaned = normalize_field(candidate.strip(" ,.;")).strip('"').strip()
        if _is_plausible_title(cleaned, author_region=author_region):
            return cleaned

    logger.debug("No plausible title found in: %.80s", body)
    return ""


# ---------------------------------------------------------------------------
# Venue extraction
# ---------------------------------------------------------------------------


def _looks_like_publisher(value: str) -> bool:
    """Whether a venue string names a publisher rather than a journal.

    Args:
        value: The candidate venue.

    Returns:
        True when the string carries a publisher keyword.
    """
    lowered = value.lower()
    return any(word in lowered for word in _PUBLISHER_WORDS)


def _extract_journal(text: str, *, title: str = "", tail: re.Match[str] | None = None) -> str:
    """Extract the journal or container title from citation text.

    Args:
        text: The citation header.
        title: The already-extracted title, excluded from the result.
        tail: A match of the closing "Journal Volume, Pages (Year)" form, which
            names the journal directly and is trusted over the fallbacks.

    Returns:
        The journal name, or an empty string.
    """
    if tail is not None:
        # Only the comma is stripped: a closing period belongs to the
        # abbreviation, as in "Phys. Rev. Lett." or "Nucl. Phys. B".
        named = normalize_field(tail.group("journal").strip().rstrip(","), max_length=120)
        if len(named) >= 3 and not _looks_like_publisher(named):
            return named

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


def _extract_volume_issue_pages(
    text: str, *, tail: re.Match[str] | None = None
) -> tuple[str, str, str]:
    """Extract volume, issue and page range from citation text.

    Guards reject the two mistakes that most often produce nonsense output: a
    year range read as a page range, and DOI digits read as a volume.

    Args:
        text: The citation header.
        tail: A match of the closing "Journal Volume, Pages (Year)" form, whose
            volume and page locator are unambiguous when it is present.

    Returns:
        A ``(volume, issue, pages)`` triple; each element may be empty.
    """
    masked = _ARXIV.sub(" ", _DOI.sub(" ", _URL.sub(" ", text)))
    volume = issue = pages = ""

    if tail is not None:
        volume = tail.group("volume")
        pages = tail.group("pages")

    if not volume:
        vol_match = _VOLUME_LABEL.search(masked)
        if vol_match:
            volume = vol_match.group(1)

    issue_match = _ISSUE_LABEL.search(masked)
    if issue_match:
        issue = issue_match.group(1)

    if not pages:
        pages_match = _PAGES_LABEL.search(masked)
        if pages_match:
            pages = pages_match.group(1).replace(" ", "")

    if not pages:
        # A monograph states a page count, not a range: "136 p."
        monograph = _MONOGRAPH_PAGES.search(masked)
        if monograph:
            pages = monograph.group(1)

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
        # A monograph names its imprint immediately before the year and often
        # carries no keyword at all: "Abelard-Schuman. 1968."
        _IMPRINT_BEFORE_YEAR.pattern,
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


def _is_annotation_line(line: str) -> bool:
    """Judge whether a line is commentary rather than part of the citation.

    A catalogue entry is a citation followed by a sentence or two about the
    work, with no blank line between them, so the boundary can only be found by
    content. An annotation reads as a sentence and carries none of the markers
    a citation line does.

    Args:
        line: One line of the entry.

    Returns:
        True when the line is annotation prose.
    """
    stripped = line.strip()
    if len(stripped.split()) < _ANNOTATION_LINE_WORDS:
        return False
    if _YEAR_BARE.search(stripped) or _DOI.search(stripped) or _ARXIV.search(stripped):
        return False
    if _CONTRIBUTOR.search(stripped) or _MONOGRAPH_PAGES.search(stripped):
        return False
    if any(word in stripped.lower() for word in _PUBLISHER_WORDS):
        return False
    return not _INVERTED_UNIT.match(stripped)


def _split_header(text: str) -> str:
    """Isolate the bibliographic header from any annotation prose.

    In an annotated bibliography each entry is a citation followed by one or
    more descriptive paragraphs. Parsing the whole block would let a phrase
    inside the annotation win the title strategy, so only the leading block is
    used for field extraction.

    Args:
        text: The full entry, header plus annotation.

    Returns:
        The citation header.
    """
    blocks = _BLANK_LINE.split(text.strip())
    header = blocks[0] if blocks else text

    lines = [ln for ln in header.split("\n") if ln.strip()]
    if len(lines) < 2:
        return header

    # Look for the start of annotation prose by walking forward.
    # In catalogue entries and annotated bibliographies, metadata (authors,
    # title, contributors, pagination, imprint, year) heads the entry. The
    # descriptive commentary begins at the first line of narrative prose.
    for i in range(2, len(lines)):
        if _is_annotation_line(lines[i]):
            return "\n".join(lines[:i])

    # Walk back over trailing commentary as fallback.
    end = len(lines)
    while end > 1 and _is_annotation_line(lines[end - 1]):
        end -= 1
    if end < len(lines):
        return "\n".join(lines[:end])

    if len(lines) > 3 and len(" ".join(lines[3:]).split()) >= 40:
        return "\n".join(lines[:3])
    return header


def _flatten(text: str) -> str:
    """Collapse the line wrapping a PDF imposes on a single reference.

    Args:
        text: The citation header, possibly wrapped across several lines.

    Returns:
        The same text on one line, with runs of whitespace collapsed.
    """
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Scoring and relevance
# ---------------------------------------------------------------------------


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


def is_bibliographic_entry(citation: Citation) -> bool:
    """Judge whether a parsed segment is really a reference at all.

    Segmentation is structural: it splits on numeric prefixes, blank lines and
    author boundaries. A document whose appendix is numbered, or whose body
    wraps oddly, therefore yields segments that are prose rather than
    references. Those segments parse into a citation with almost no fields, and
    presenting them as citations is exactly the fabrication this project
    refuses to commit.

    An entry is kept only when it carries positive evidence of being a
    reference: a resolvable identifier, or a named author together with a year
    or a venue, or a title with a venue and a locator.

    Args:
        citation: A citation returned by :func:`parse_citation`.

    Returns:
        True when the entry should be shown to the reader as a citation.
    """
    if citation.doi:
        return True

    has_author = bool(citation.authors)
    has_year = bool(citation.year)
    has_venue = bool(citation.journal or citation.publisher)
    has_locator = bool(citation.volume or citation.pages)

    if has_author and (has_year or has_venue):
        return True
    if citation.url and (has_year or has_author):
        return True
    return bool(citation.title and has_venue and (has_year or has_locator))


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

    header = _flatten(_split_header(raw))
    body = _ENTRY_PREFIX.sub("", header)

    authors, author_end = _author_span(body)
    citation.authors = authors
    author_region = body[:author_end]
    remainder = body[author_end:]

    tail = _VENUE_TAIL.search(remainder)
    arxiv = _ARXIV.search(remainder)

    citation.year = _extract_year(header)
    citation.title = _extract_title(body, remainder, author_region, tail, arxiv)
    citation.journal = _extract_journal(header, title=citation.title, tail=tail)
    citation.volume, citation.issue, citation.pages = _extract_volume_issue_pages(header, tail=tail)
    citation.publisher = _extract_publisher(header, title=citation.title)

    if arxiv is not None and not citation.doi:
        identifier = arxiv.group(1)
        citation.url = citation.url or f"https://arxiv.org/abs/{identifier}"
        citation.journal = citation.journal or "arXiv preprint"
        # A modern arXiv identifier encodes its own submission date as YYMM,
        # so the year is read from the identifier rather than left blank.
        if not citation.year:
            citation.year = f"20{identifier[:2]}"

    if citation.journal and _looks_like_publisher(citation.journal):
        citation.publisher = citation.publisher or citation.journal
        citation.journal = ""

    citation.entry_type = _detect_entry_type(raw, citation)
    citation.confidence = score_citation(citation)
    return citation


__all__ = ["is_bibliographic_entry", "parse_citation", "score_citation"]
