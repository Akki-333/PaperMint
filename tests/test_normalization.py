"""Tests for text normalisation and the parser's validation guards."""

from __future__ import annotations

from papermint.models import CitationStyle
from papermint.parsers.citation_parser import (
    is_bibliographic_entry,
    parse_citation,
    score_citation,
)
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.text_normalizer import (
    dehyphenate,
    normalize_document,
    normalize_field,
    normalize_unicode,
    sentence_count,
    strip_control_characters,
    strip_running_furniture,
    word_count,
)

# --- Character level -------------------------------------------------------


def test_ligatures_are_folded():
    assert normalize_unicode("ﬁeld ﬂow") == "field flow"


def test_dashes_and_quotes_become_ascii():
    assert normalize_unicode("“A–B”") == '"A-B"'


def test_soft_hyphens_are_removed():
    assert strip_control_characters("bib­liography") == "bibliography"


def test_newlines_survive_control_stripping():
    assert strip_control_characters("a\nb\tc") == "a\nb\tc"


# --- Line level ------------------------------------------------------------


def test_words_broken_across_lines_are_rejoined():
    assert dehyphenate("bibliomet-\nrics") == "bibliometrics"


def test_genuine_compounds_survive_dehyphenation():
    assert dehyphenate("self-\nAware") == "self-\nAware"


def test_bare_page_numbers_are_dropped():
    cleaned = strip_running_furniture("Real content here.\n12\nMore content here.\n13")
    assert "12" not in cleaned.split("\n")
    assert "Real content here." in cleaned


def test_repeated_running_headers_are_dropped():
    text = "Journal of Testing\n" * 4 + "Body line one is long enough.\n"
    assert "Journal of Testing" not in strip_running_furniture(text)


def test_document_normalisation_is_idempotent():
    once = normalize_document("Aﬁx-\ned  line.\n\n\n\nEnd.")
    assert normalize_document(once) == once


def test_empty_input_normalises_to_empty():
    assert normalize_document("") == ""
    assert normalize_document("   \n  ") == ""


# --- Field level -----------------------------------------------------------


def test_leading_connectors_are_stripped():
    assert normalize_field("In  Machine learning") == "Machine learning"


def test_orphaned_bracket_is_removed():
    assert normalize_field("The Title (") == "The Title"


def test_long_fields_are_truncated_on_a_word_boundary():
    result = normalize_field("word " * 200, max_length=40)
    assert len(result) <= 44
    assert result.endswith("...")


# --- Counting --------------------------------------------------------------


def test_author_initials_do_not_inflate_the_sentence_count():
    assert sentence_count("Smith, J. A. wrote this. Doe, R. B. agreed. Done!") == 3


def test_dois_do_not_inflate_the_sentence_count():
    assert sentence_count("See 10.1016/j.jbi.2020.01.002 for details. Yes.") == 2


def test_word_count_is_whitespace_delimited():
    assert word_count("one two  three") == 3
    assert word_count("") == 0


# --- Parser guards ---------------------------------------------------------


def test_a_date_span_in_a_title_is_not_read_as_pages():
    citation = parse_citation(
        "Ferguson, N. (2001). The cash nexus: Money and power, 1700-2000. Basic Books."
    )
    assert citation.pages == ""
    assert "1700-2000" in citation.title


def test_a_real_page_range_is_still_extracted():
    citation = parse_citation(
        "Smith, J. (2020). A title. Journal of AI, 15(2), 103-115.",
        CitationStyle.APA,
    )
    assert citation.pages == "103-115"
    assert citation.volume == "15"
    assert citation.issue == "2"


def test_three_authors_are_parsed_separately():
    citation = parse_citation(
        "Williams, C. D., Brown, E., & Davis, F. (2021). Neural networks. "
        "IEEE Transactions, 32(4), 10-25.",
        CitationStyle.APA,
    )
    assert [a.family for a in citation.authors] == ["Williams", "Brown", "Davis"]


def test_a_publisher_is_not_reported_as_a_journal():
    citation = parse_citation(
        "Johnson, L. (2019). The future of AI. Tech Press.", CitationStyle.APA
    )
    assert citation.journal == ""
    assert "Press" in citation.publisher


def test_a_book_with_a_publisher_is_typed_as_a_book():
    citation = parse_citation(
        "Johnson, L. (2019). The future of AI. Basic Books.", CitationStyle.APA
    )
    assert citation.entry_type.value == "book"


def test_no_authors_are_invented_from_prose():
    citation = parse_citation("The quick brown fox jumped over the lazy dog in 2020.")
    assert citation.authors == []


def test_an_unparsed_entry_shows_its_own_text_not_untitled():
    citation = parse_citation("!!! ??? ...")
    assert citation.title == ""
    assert citation.display_title
    assert "Untitled" not in citation.display_title
    assert citation.is_parsed is False


def test_confidence_can_be_rescored_after_an_edit():
    citation = parse_citation("Smith, J. (2020). A title. Journal of AI, 15(2), 1-9.")
    before = citation.confidence
    citation.doi = "10.1234/abc"
    assert score_citation(citation) >= before


# --- Surname particles -----------------------------------------------------

PARTICLE_BIBLIOGRAPHY = """Smith, J. A. (2020). Machine learning in citation parsing. Journal of AI, 15(2), 103-115.
van der Berg, A., & O'Brien, K. (2019). Multilingual reference parsing. Tech Press.
de la Cruz, M. (2018). Corpus methods for linguistics. Academic Press.
von Neumann, J. (1945). First draft of a report. Moore School."""


def test_a_lowercase_particle_does_not_swallow_an_entry():
    """A surname particle opens in lower case but still starts a new entry.

    The continuation-merge heuristic folds any segment beginning in lower case
    into the entry above it. Without an exception for author boundaries, every
    reference by "van der Berg" or "de la Cruz" disappeared into its
    predecessor.
    """
    assert len(split_citations(PARTICLE_BIBLIOGRAPHY)) == 4


def test_particles_are_kept_as_part_of_the_surname():
    families = [
        parse_citation(entry, CitationStyle.APA).authors[0].family
        for entry in split_citations(PARTICLE_BIBLIOGRAPHY)
    ]
    assert families == ["Smith", "van der Berg", "de la Cruz", "von Neumann"]


# --- The numbered reference form ------------------------------------------

# The dominant form in physics, chemistry and the life sciences:
# "Initials Surname, and Initials Surname, Title, Journal Abbrev. Vol, Page (Year)."
NUMBERED_ENTRY = (
    "[1] A. Eckardt, C. Weiss, and M. Holthaus, Superfluid-insulator transition "
    "in a periodically driven optical lattice, Phys. Rev. Lett. 95, 260404 (2005)."
)


def test_the_author_walk_stops_before_the_title():
    """A surname must not absorb the first word of the title.

    The walk used to be an unanchored ``finditer``, so the inverted-name
    pattern matched "Holthaus, Superfluid" and reported a person called
    Superfluid Holthaus who does not exist.
    """
    citation = parse_citation(NUMBERED_ENTRY)
    assert [a.family for a in citation.authors] == ["Eckardt", "Weiss", "Holthaus"]
    assert all("Superfluid" not in a.given for a in citation.authors)


def test_a_surname_is_not_paired_with_the_next_authors_initial():
    """ "A. Eckardt, C. Weiss" must not yield an author named "C. Eckardt"."""
    citation = parse_citation(NUMBERED_ENTRY)
    pairs = {(a.given.strip(), a.family) for a in citation.authors}
    assert ("A.", "Eckardt") in pairs
    assert ("C.", "Eckardt") not in pairs


def test_a_journal_abbreviation_does_not_end_the_title():
    """The title must not stop at "Phys." nor start mid-author.

    The old fallback took the longest fragment of a split on ". ", which cuts
    through both author initials and journal abbreviations.
    """
    citation = parse_citation(NUMBERED_ENTRY)
    assert citation.title == (
        "Superfluid-insulator transition in a periodically driven optical lattice"
    )
    assert citation.journal == "Phys. Rev. Lett."
    assert citation.volume == "95"
    assert citation.year == "2005"


def test_a_two_author_numbered_entry_keeps_both_names():
    citation = parse_citation(
        "[4] T. Oka and H. Aoki, Photovoltaic Hall effect in graphene, "
        "Phys. Rev. B 79, 081406 (2009)."
    )
    assert [a.family for a in citation.authors] == ["Oka", "Aoki"]
    assert citation.title == "Photovoltaic Hall effect in graphene"
    assert citation.journal == "Phys. Rev. B"


def test_an_arxiv_preprint_is_parsed():
    """A preprint carries its date in its identifier, so the year is known."""
    citation = parse_citation(
        "[6] T. Haga, Quasi-stationary states in driven open systems, "
        "arXiv:2506.04740 [cond-mat.stat-mech]."
    )
    assert [a.family for a in citation.authors] == ["Haga"]
    assert citation.title == "Quasi-stationary states in driven open systems"
    assert citation.year == "2025"
    assert citation.url == "https://arxiv.org/abs/2506.04740"


# --- The relevance gate ----------------------------------------------------


def test_a_title_case_heading_is_not_read_as_a_person():
    """A written-out name is only accepted after an explicit conjunction.

    Allowing it at the head of an entry turned the heading "National Digital
    Literacy Scheme" into an author named National Digital Literacy. Every
    style that writes a first author in full also inverts it, so refusing the
    form here costs nothing and stops a heading becoming a person.
    """
    citation = parse_citation("National Digital Literacy Scheme was launched in 2015.")
    assert citation.authors == []


def test_a_trailing_written_out_author_is_still_parsed():
    """The conjunction form that MLA genuinely uses must keep working."""
    citation = parse_citation(
        'Smith, John A., and Robert B. Doe. "Machine learning in citation parsing." '
        "Journal of Bibliometrics, vol. 15, no. 2, 2020, pp. 103-115.",
        CitationStyle.MLA,
    )
    assert [a.family for a in citation.authors] == ["Smith", "Doe"]


def test_a_real_reference_passes_the_relevance_gate():
    assert is_bibliographic_entry(parse_citation(NUMBERED_ENTRY))


def test_appendix_prose_fails_the_relevance_gate():
    """Body prose segmented by a numeric prefix must not be shown as a citation."""
    prose = parse_citation(
        "We then compute the bifurcation diagram for each of these initial "
        "states and plot them together in Fig."
    )
    assert prose.authors == []
    assert is_bibliographic_entry(prose) is False


def test_a_section_heading_fails_the_relevance_gate():
    """ "H. This" parsed as an author, but a name alone is not a reference."""
    heading = parse_citation("H. This. collective spin J = 3.")
    assert is_bibliographic_entry(heading) is False


# --- Entry numbering vs appendix numbering ---------------------------------


APPENDIX_AND_REFERENCES = """1. Basis states
An orthonormal basis is given by the product states over the six spins here.
2. Summing the dimensions
Summing the total dimensions gives sixty four as expected from the counting.
1. Young diagrams
For the four shapes above one finds the dimensions five, nine and five again.
[1] A. Eckardt, C. Weiss, and M. Holthaus, Superfluid-insulator transition, Phys. Rev. Lett. 95, 260404 (2005).
[2] T. Oka and H. Aoki, Photovoltaic Hall effect in graphene, Phys. Rev. B 79, 081406 (2009).
[3] D. Manzano, A short introduction to the Lindblad master equation, AIP Advances 10, 025106 (2020)."""


def test_bracketed_indices_win_over_appendix_numbering():
    """Only one index form may segment a block.

    An appendix numbers its subsections and restarts under each new appendix,
    so "1. 2. 1." is not reference numbering. Allowing both forms to cut the
    same block turned appendix headings into citations.
    """
    segments = split_citations(APPENDIX_AND_REFERENCES)
    assert len(segments) == 3
    assert all(segment.startswith("[") for segment in segments)
    assert not any("Young diagrams" in segment for segment in segments)
