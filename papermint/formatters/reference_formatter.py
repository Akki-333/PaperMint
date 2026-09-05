"""Render a parsed citation back out in a named citation style.

Everything above this module *reads* documents. This one writes: it takes a
:class:`~papermint.models.Citation` and produces the reference string a writer
would paste into a Works Cited page, plus the reference material explaining
what each style is and why it is shaped the way it is.

Two rules govern the output, and both follow from the project's honesty
principle.

**Nothing absent is invented.** An element that was never parsed is omitted
along with its punctuation, and every rendering reports which elements it had
to leave out. A reference missing its year is rendered without a year and says
so; it is never given a plausible one.

**Nothing present is silently rewritten.** Styles disagree about
capitalisation: APA sets an article title in sentence case, MLA and Chicago in
title case. Recasing means deciding which words are proper nouns, and a
recaser that lowercases "Indian" or "Dickens" has corrupted the source. Titles
are therefore printed exactly as they were read, and every style guide says so
in :attr:`StyleGuide.caveat`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from papermint.models import Author, Citation, CitationStyle, EntryType

# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

#: Entry types whose venue is a publisher rather than a periodical.
_PUBLISHER_TYPES: Final[frozenset[EntryType]] = frozenset(
    {EntryType.BOOK, EntryType.THESIS, EntryType.REPORT}
)

#: A given-name token already reduced to an initial, such as "J." or "J.-P."
_IS_INITIAL = re.compile(r"^[A-Z]\.?(?:-[A-Z]\.?)?$")

#: Trailing punctuation that must not be doubled when segments are joined.
_TERMINAL = ".!?"


def _initialise(given: str) -> str:
    """Reduce a given name to initials without disturbing ones already reduced.

    Args:
        given: The given name as parsed, which may be "Marjane", "J. A." or "".

    Returns:
        The initialised form, such as "M." or "J. A.", or an empty string.
    """
    parts = [part for part in given.replace(".", ". ").split() if part]
    initials: list[str] = []
    for part in parts:
        if _IS_INITIAL.match(part):
            initials.append(part if part.endswith(".") else f"{part}.")
        elif part[0].isalpha():
            initials.append(f"{part[0].upper()}.")
    return " ".join(initials)


def _inverted(author: Author, *, initials: bool) -> str:
    """Render one author surname first.

    Args:
        author: The author to render.
        initials: Reduce the given name to initials, as APA does. MLA and
            Chicago keep whatever given name the source supplied.

    Returns:
        "Ambler, Marjane", "Ambler, M.", or the surname alone.
    """
    given = _initialise(author.given) if initials else author.given.strip()
    if author.family and given:
        return f"{author.family}, {given}"
    return author.family or given


def _natural(author: Author, *, initials: bool) -> str:
    """Render one author in reading order, given name first.

    Args:
        author: The author to render.
        initials: Reduce the given name to initials, as IEEE does.

    Returns:
        "Marjane Ambler", "M. Ambler", or the surname alone.
    """
    given = _initialise(author.given) if initials else author.given.strip()
    if given and author.family:
        return f"{given} {author.family}"
    return author.family or given


def _apa_authors(authors: list[Author]) -> str:
    """Render an author list in APA order: inverted throughout, ampersand last.

    Args:
        authors: The parsed authors.

    Returns:
        The formatted author segment, or an empty string.
    """
    names = [_inverted(a, initials=True) for a in authors if a.family or a.given]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])}, & {names[-1]}"


def _mla_authors(authors: list[Author]) -> str:
    """Render an author list in MLA order: first inverted, then "et al."

    MLA 9 names at most two people. A work with three or more contributors is
    credited to the first followed by "et al.", because the entry's job is to
    point at an alphabetised slot rather than to enumerate a research group.

    Args:
        authors: The parsed authors.

    Returns:
        The formatted author segment, or an empty string.
    """
    people = [a for a in authors if a.family or a.given]
    if not people:
        return ""
    first = _inverted(people[0], initials=False)
    if len(people) == 1:
        return first
    if len(people) == 2:
        return f"{first}, and {_natural(people[1], initials=False)}"
    return f"{first}, et al."


def _ieee_authors(authors: list[Author]) -> str:
    """Render an author list in IEEE order: initials first, "and" before the last.

    Args:
        authors: The parsed authors.

    Returns:
        The formatted author segment, or an empty string.
    """
    names = [_natural(a, initials=True) for a in authors if a.family or a.given]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) > 6:
        return f"{names[0]} et al."
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _chicago_authors(authors: list[Author]) -> str:
    """Render an author list in Chicago order: first inverted, the rest natural.

    Args:
        authors: The parsed authors.

    Returns:
        The formatted author segment, or an empty string.
    """
    people = [a for a in authors if a.family or a.given]
    if not people:
        return ""
    first = _inverted(people[0], initials=False)
    if len(people) == 1:
        return first
    if len(people) > 3:
        return f"{first}, et al."
    rest = [_natural(a, initials=False) for a in people[1:]]
    if len(rest) == 1:
        return f"{first}, and {rest[0]}"
    return f"{first}, {', '.join(rest[:-1])}, and {rest[-1]}"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _standalone(citation: Citation) -> bool:
    """Whether this work stands alone rather than sitting inside a container.

    The distinction drives punctuation in three of the four styles. A book,
    thesis or report is italicised and unquoted; an article, chapter or paper
    is quoted, because the quotation marks say "this is a part, and the italic
    name after it is the whole".

    Args:
        citation: The citation being rendered.

    Returns:
        True for a self-contained work.
    """
    return citation.entry_type in _PUBLISHER_TYPES


def _venue(citation: Citation) -> str:
    """Return the container this work sits in: a periodical or a publisher.

    Args:
        citation: The citation being rendered.

    Returns:
        The venue name, or an empty string when none was parsed.
    """
    if _standalone(citation):
        return citation.publisher or citation.booktitle or citation.journal
    return citation.journal or citation.booktitle or citation.publisher


def _work_title(citation: Citation) -> str:
    """Render the title with the punctuation its containment implies.

    Args:
        citation: The citation being rendered.

    Returns:
        The title in quotation marks, bare when the work stands alone, or an
        empty string when no title was parsed.
    """
    if not citation.title:
        return ""
    return _sentence(citation.title) if _standalone(citation) else f'"{citation.title}."'


def _sentence(text: str) -> str:
    """Close a segment with a full stop unless it already ends in one.

    Args:
        text: The segment.

    Returns:
        The segment carrying exactly one terminal mark, or an empty string.
    """
    text = text.strip().rstrip(",;")
    if not text:
        return ""
    return text if text[-1] in _TERMINAL else f"{text}."


def _join(segments: list[str]) -> str:
    """Join finished segments into one reference string.

    Args:
        segments: The segments in style order; empty ones are dropped, which is
            how an element the parser never found leaves no punctuation behind.

    Returns:
        The joined reference.
    """
    return " ".join(segment for segment in (s.strip() for s in segments) if segment)


@dataclass(frozen=True, slots=True)
class FormattedReference:
    """One citation rendered in one style.

    Attributes:
        text: The complete reference string, ready to copy.
        marker: The list marker: "[3]" for IEEE, empty for the alphabetised
            styles, which identify an entry by its position on the page.
        italic: The exact substring of ``text`` set in italics in print, so the
            interface can style it without the domain layer emitting markup.
        omitted: Core elements this rendering had to leave out because the
            parser never found them. Empty means the reference is complete.
    """

    text: str
    marker: str = ""
    italic: str = ""
    omitted: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """Whether every core element was present."""
        return not self.omitted


def _omissions(citation: Citation) -> tuple[str, ...]:
    """Name the core elements a rendering will be missing.

    Args:
        citation: The citation being rendered.

    Returns:
        The absent element names, in the order a reader notices them.
    """
    present = (
        ("author", bool(citation.authors)),
        ("title", bool(citation.title)),
        ("year", bool(citation.year)),
        ("venue", bool(_venue(citation))),
        ("pages", bool(citation.pages)),
    )
    return tuple(name for name, found in present if not found)


def _apa(citation: Citation) -> str:
    """Assemble an APA 7 reference.

    Args:
        citation: The citation to render.

    Returns:
        The reference string.
    """
    locator = ""
    if citation.volume:
        locator = citation.volume
        if citation.issue:
            locator += f"({citation.issue})"
    tail = ", ".join(part for part in (_venue(citation), locator, citation.pages) if part)

    return _join(
        [
            _sentence(_apa_authors(citation.authors)),
            f"({citation.year})." if citation.year else "",
            _sentence(citation.title),
            _sentence(tail),
            citation.doi_url,
        ]
    )


def _mla(citation: Citation) -> str:
    """Assemble an MLA 9 entry from whichever core elements are available.

    Args:
        citation: The citation to render.

    Returns:
        The reference string.
    """
    venue = _venue(citation)
    container: list[str] = [venue] if venue else []
    if citation.volume:
        container.append(f"vol. {citation.volume}")
    if citation.issue:
        container.append(f"no. {citation.issue}")
    if citation.year:
        container.append(citation.year)
    if citation.pages:
        container.append(f"pp. {citation.pages}")

    return _join(
        [
            _sentence(_mla_authors(citation.authors)),
            _work_title(citation),
            _sentence(", ".join(container)),
            citation.doi_url,
        ]
    )


def _ieee(citation: Citation) -> str:
    """Assemble an IEEE reference, without its bracketed number.

    Args:
        citation: The citation to render.

    Returns:
        The reference string.
    """
    venue = _venue(citation)
    tail: list[str] = [venue] if venue else []
    if citation.volume:
        tail.append(f"vol. {citation.volume}")
    if citation.issue:
        tail.append(f"no. {citation.issue}")
    if citation.pages:
        tail.append(f"pp. {citation.pages}")
    if citation.year:
        tail.append(citation.year)

    authors = _ieee_authors(citation.authors)
    if not citation.title:
        title = ""
    elif _standalone(citation):
        title = _sentence(citation.title)
    else:
        title = f'"{citation.title},"'

    return _join(
        [
            f"{authors}," if authors else "",
            title,
            _sentence(", ".join(tail)),
            f"doi: {citation.doi}." if citation.doi else "",
        ]
    )


def _chicago(citation: Citation) -> str:
    """Assemble a Chicago 17 notes-and-bibliography entry.

    Args:
        citation: The citation to render.

    Returns:
        The reference string.
    """
    venue = _venue(citation)
    if _standalone(citation):
        # A book carries an imprint, not a volume: "New York: Viking, 1996."
        tail = f"{citation.address}: {venue}" if citation.address and venue else venue
        if citation.year:
            tail = f"{tail}, {citation.year}" if tail else citation.year
    else:
        tail = venue
        if citation.volume:
            tail = f"{tail} {citation.volume}".strip()
        if citation.issue:
            tail = f"{tail}, no. {citation.issue}" if tail else f"no. {citation.issue}"
        if citation.year:
            tail = f"{tail} ({citation.year})" if tail else f"({citation.year})"
        if citation.pages:
            tail = f"{tail}: {citation.pages}" if tail else citation.pages

    return _join(
        [
            _sentence(_chicago_authors(citation.authors)),
            _work_title(citation),
            _sentence(tail),
            citation.doi_url,
        ]
    )


#: The assembler for each supported style.
_ASSEMBLERS: Final[dict[CitationStyle, Callable[[Citation], str]]] = {
    CitationStyle.APA: _apa,
    CitationStyle.MLA: _mla,
    CitationStyle.IEEE: _ieee,
    CitationStyle.CHICAGO: _chicago,
}


def format_reference(citation: Citation, style: CitationStyle) -> FormattedReference:
    """Render one citation in one style.

    Args:
        citation: The parsed citation.
        style: The target style. ``UNKNOWN`` falls back to APA, the most widely
            recognised of the four.

    Returns:
        The rendered reference, reporting any element it had to omit.
    """
    resolved = style if style in _ASSEMBLERS else CitationStyle.APA
    # Italics mark the whole, not the part: the journal for an article, the
    # book's own title when the work stands alone.
    emphasis = citation.title if _standalone(citation) else _venue(citation)
    return FormattedReference(
        text=_ASSEMBLERS[resolved](citation),
        italic=emphasis,
        omitted=_omissions(citation),
    )


def _sort_key(citation: Citation) -> str:
    """Return the alphabetising key for a reference list.

    Args:
        citation: The citation to place.

    Returns:
        The first author's surname, falling back to the title, lowercased.
    """
    if citation.authors and citation.authors[0].family:
        return citation.authors[0].family.lower()
    return (citation.title or citation.raw_text).lower()


def format_reference_list(
    citations: list[Citation], style: CitationStyle
) -> list[FormattedReference]:
    """Render a whole reference list in one style, ordered as that style requires.

    IEEE numbers its list in order of first citation, so document order is kept
    and every entry carries its bracketed number. The other three styles
    alphabetise by the first author's surname and carry no marker.

    Args:
        citations: The citations to render.
        style: The target style.

    Returns:
        The rendered references, in list order.
    """
    resolved = style if style in _ASSEMBLERS else CitationStyle.APA
    if resolved is CitationStyle.IEEE:
        return [
            FormattedReference(
                text=rendered.text,
                marker=f"[{position}]",
                italic=rendered.italic,
                omitted=rendered.omitted,
            )
            for position, rendered in enumerate(
                (format_reference(c, resolved) for c in citations), start=1
            )
        ]
    return [format_reference(c, resolved) for c in sorted(citations, key=_sort_key)]


# ---------------------------------------------------------------------------
# Reference material
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StyleGuide:
    """What one citation style is, who uses it, and how an entry is built.

    Attributes:
        style: The style this describes.
        name: Its full name and edition.
        disciplines: The fields that use it.
        principle: Why the style is shaped the way it is. Every ordering and
            punctuation rule below follows from this paragraph.
        list_heading: What the reference list itself is called.
        ordering: How entries are ordered on the page.
        in_text: What a citation to this reference looks like in running text.
        elements: The ordered elements of an entry, each paired with the
            punctuation that closes it.
        distinctives: The details that tell this style apart from the others.
        caveat: What PaperMint deliberately declines to do to your text.
        sample: A complete worked entry.
    """

    style: CitationStyle
    name: str
    disciplines: str
    principle: str
    list_heading: str
    ordering: str
    in_text: str
    elements: tuple[tuple[str, str], ...]
    distinctives: tuple[str, ...]
    caveat: str
    sample: str

    @property
    def short_name(self) -> str:
        """Return the bare name of the style, without its edition."""
        return self.name.split(",")[0].strip()


_SHARED_CAVEAT = (
    "PaperMint prints titles exactly as they were read from your document. "
    "Recasing a title means deciding which words are proper nouns, and a "
    "recaser that lowercases a name has corrupted the source, so that "
    "judgement is left to you."
)

#: Everything the interface knows about the four supported styles.
STYLE_GUIDES: Final[dict[CitationStyle, StyleGuide]] = {
    CitationStyle.APA: StyleGuide(
        style=CitationStyle.APA,
        name="APA, 7th edition",
        disciplines="Psychology, education, nursing, business and the social sciences",
        principle=(
            "APA is an author-date style. The year sits second, immediately after the "
            "author, because in empirical fields the currency of a finding is part of "
            "its weight: a reader scanning your list needs to see at once whether the "
            "evidence is from 1974 or from last year."
        ),
        list_heading="References",
        ordering="Alphabetical by the first author's surname, with a hanging indent.",
        in_text=(
            "(Ambler, 1992) in parentheses, or Ambler (1992) when the author is the "
            "subject of your sentence."
        ),
        elements=(
            ("Author", "Surname, then initials. A full stop closes the element."),
            ("Year", "In parentheses, followed by a full stop."),
            ("Title of the work", "Sentence case. A full stop closes it."),
            ("Periodical or publisher", "Italic, followed by a comma."),
            ("Volume(issue)", "Volume italic, issue in parentheses, then a comma."),
            ("Pages", "Bare numbers, closed by a full stop."),
            ("DOI", "The full https://doi.org/ address, with no closing full stop."),
        ),
        distinctives=(
            "An ampersand, not the word 'and', joins the last two authors.",
            "Given names are always reduced to initials.",
            "Up to twenty authors are listed before the list is elided.",
            "Article titles take sentence case; journal names keep their own capitals.",
        ),
        caveat=_SHARED_CAVEAT,
        sample=(
            "Ambler, M. (1992). Women leaders in Indian education. Tribal College, 3(4), 10-15."
        ),
    ),
    CitationStyle.MLA: StyleGuide(
        style=CitationStyle.MLA,
        name="MLA, 9th edition",
        disciplines="Literature, languages, cultural studies, philosophy and the humanities",
        principle=(
            "MLA 9 has no separate template per source type. It has nine core elements "
            "in one fixed order, each closed by a fixed punctuation mark. You describe "
            "any source at all, a novel, a journal article, a film, a mural, a podcast "
            "episode, by filling in the elements that apply and skipping the ones that "
            "do not. This is the single largest difference between MLA and every other "
            "style here, and it is why MLA absorbed new media without needing a fresh "
            "rule for each one."
        ),
        list_heading="Works Cited",
        ordering=(
            "Alphabetical by the first author's surname, hanging indent, double spaced. "
            "The page is titled Works Cited, not References and not Bibliography: it "
            "holds what you actually cited. Background reading you did not cite belongs "
            "under Works Consulted."
        ),
        in_text=(
            "(Ambler 12): author and page, with no year and no comma. Literary argument "
            "turns on where in a text something happens, so MLA points at the page."
        ),
        elements=(
            ("Author", "Surname, given name. Closed by a full stop."),
            (
                "Title of source",
                (
                    "The work itself. In quotation marks when it sits inside something "
                    "larger, italic when it stands alone. Closed by a full stop."
                ),
            ),
            (
                "Title of container",
                (
                    "The larger whole holding the source: the journal, the anthology, "
                    "the streaming service. Italic, closed by a comma."
                ),
            ),
            (
                "Other contributors",
                (
                    "Editors, translators and illustrators, named by role, as in "
                    "'translated by'. Closed by a comma."
                ),
            ),
            ("Version", "An edition or a cut, such as '2nd ed.'. Closed by a comma."),
            ("Number", "Volume and issue, written 'vol. 3, no. 4'. Closed by a comma."),
            ("Publisher", "The organisation that issued it. Closed by a comma."),
            ("Publication date", "As specific as the source allows. Closed by a comma."),
            (
                "Location",
                (
                    "Where inside the container it sits: 'pp. 10-15', a DOI, or a URL. "
                    "Closed by a full stop."
                ),
            ),
        ),
        distinctives=(
            (
                "Elements 3 to 9 repeat for a second container, so an article read "
                "through a database names the journal first and the database second."
            ),
            "Three or more authors are credited as the first followed by 'et al.'",
            "Given names are written out in full rather than initialised.",
            "'vol.' and 'no.' are spelled out, and the date precedes the page range.",
            "An element that does not apply to a source is skipped, not left blank.",
        ),
        caveat=_SHARED_CAVEAT,
        sample=(
            'Ambler, Marjane. "Women Leaders in Indian Education." Tribal College, '
            "vol. 3, no. 4, 1992, pp. 10-15."
        ),
    ),
    CitationStyle.IEEE: StyleGuide(
        style=CitationStyle.IEEE,
        name="IEEE",
        disciplines="Electrical and electronic engineering, computer science and computing",
        principle=(
            "IEEE cites by number. The reference list is an index ordered by first "
            "appearance, and the in-text citation is a bracketed pointer into it. "
            "Technical prose often leans on several sources inside one clause, and "
            "'[3], [7]-[9]' interrupts a sentence far less than three sets of "
            "author-date parentheses would."
        ),
        list_heading="References",
        ordering="Numbered in order of first citation in the text, never alphabetised.",
        in_text="[1], or [3], [7]-[9] for several at once. The number is the reference.",
        elements=(
            ("[n]", "The entry's number, in square brackets at the left margin."),
            ("Author", "Initials before the surname, closed by a comma."),
            ("Title of paper", "In quotation marks, sentence case, comma inside the quotes."),
            ("Journal", "Abbreviated and italic, closed by a comma."),
            ("vol. / no.", "Volume then issue, each closed by a comma."),
            ("pp.", "The page range, closed by a comma."),
            ("Year", "Last, closed by a full stop."),
        ),
        distinctives=(
            "Initials precede the surname, the reverse of every other style here.",
            "More than six authors are cut to the first followed by 'et al.'",
            "Journal names are abbreviated: 'IEEE Trans. Signal Process.'",
            "The year sits at the end rather than beside the author.",
        ),
        caveat=_SHARED_CAVEAT,
        sample=(
            '[1] M. Ambler, "Women leaders in Indian education," Tribal College, '
            "vol. 3, no. 4, pp. 10-15, 1992."
        ),
    ),
    CitationStyle.CHICAGO: StyleGuide(
        style=CitationStyle.CHICAGO,
        name="Chicago, 17th edition, notes and bibliography",
        disciplines="History, art history, theology and the archival humanities",
        principle=(
            "Chicago carries two systems in one manual. Notes and bibliography puts the "
            "full citation in a footnote and repeats it in an alphabetised "
            "bibliography; author-date works much as APA does. Historians take the "
            "first, because a footnote can hold the archive box number and the "
            "qualification an argument needs, and a parenthesis cannot. PaperMint "
            "renders the bibliography entry."
        ),
        list_heading="Bibliography",
        ordering="Alphabetical by the first author's surname, with a hanging indent.",
        in_text=(
            "A superscript number in the text, with the full reference in the footnote "
            "beneath it and a shortened form on every later mention."
        ),
        elements=(
            ("Author", "First author inverted, later authors in reading order."),
            ("Title of article", "In quotation marks, title case, closed by a full stop."),
            ("Journal", "Italic, with no comma after it."),
            ("Volume, no. issue", "Volume bare, issue after 'no.'"),
            ("(Year)", "In parentheses, followed by a colon."),
            ("Pages", "After the colon, closed by a full stop."),
        ),
        distinctives=(
            "Only the first author is inverted; the rest read given name first.",
            "No comma separates the journal from the volume number.",
            "The year sits in parentheses and the page range follows a colon.",
            "The bibliography is the companion to footnotes, not a replacement for them.",
        ),
        caveat=_SHARED_CAVEAT,
        sample=(
            'Ambler, Marjane. "Women Leaders in Indian Education." Tribal College 3, '
            "no. 4 (1992): 10-15."
        ),
    ),
}


def style_guide(style: CitationStyle) -> StyleGuide:
    """Return the reference material for one style.

    Args:
        style: The style to describe. ``UNKNOWN`` falls back to APA.

    Returns:
        The matching guide.
    """
    return STYLE_GUIDES.get(style, STYLE_GUIDES[CitationStyle.APA])


def style_guides() -> list[StyleGuide]:
    """Return every style guide, in the order the interface presents them.

    Returns:
        The four guides.
    """
    return list(STYLE_GUIDES.values())


def formattable_styles() -> list[CitationStyle]:
    """List the styles a citation can be rendered in.

    Returns:
        The supported styles, in presentation order.
    """
    return list(STYLE_GUIDES)


__all__ = [
    "STYLE_GUIDES",
    "FormattedReference",
    "StyleGuide",
    "format_reference",
    "format_reference_list",
    "formattable_styles",
    "style_guide",
    "style_guides",
]
