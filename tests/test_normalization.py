"""Tests for text normalisation and the parser's validation guards."""

from __future__ import annotations

from papermint.models import CitationStyle
from papermint.parsers.citation_parser import parse_citation, score_citation
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
