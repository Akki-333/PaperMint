"""Tests for rendering a parsed citation back out in a named style.

Two things are guarded here. The first is that each style is actually
distinct: an implementation that quietly rendered everything as APA would pass
a naive "does it produce a string" test. The second, and the one that matters
more, is that formatting obeys the honesty principle: an element the parser
never found must be absent from the output and named as absent, never filled
in to make the line look finished.
"""

from __future__ import annotations

import pytest

from papermint.formatters.reference_formatter import (
    format_reference,
    format_reference_list,
    formattable_styles,
    style_guide,
    style_guides,
)
from papermint.models import Author, Citation, CitationStyle, EntryType


@pytest.fixture
def article() -> Citation:
    """Return a completely parsed journal article."""
    return Citation(
        title="Women Leaders in Indian Education",
        authors=[Author(given="Marjane", family="Ambler")],
        year="1992",
        journal="Tribal College",
        volume="3",
        issue="4",
        pages="10-15",
        raw_text="Ambler, Marjane. Women Leaders in Indian Education.",
    )


@pytest.fixture
def book() -> Citation:
    """Return a completely parsed monograph."""
    return Citation(
        title="A History of Reading",
        authors=[Author(given="Alberto", family="Manguel")],
        year="1996",
        publisher="Viking",
        address="New York",
        entry_type=EntryType.BOOK,
        raw_text="Manguel, Alberto. A History of Reading.",
    )


# --- Each style is itself ---------------------------------------------------


def test_apa_leads_with_the_year_in_parentheses(article):
    rendered = format_reference(article, CitationStyle.APA)
    assert rendered.text.startswith("Ambler, M. (1992).")
    assert "Tribal College, 3(4), 10-15." in rendered.text


def test_mla_writes_the_given_name_out_and_spells_out_the_number(article):
    rendered = format_reference(article, CitationStyle.MLA)
    assert rendered.text.startswith("Ambler, Marjane.")
    assert '"Women Leaders in Indian Education."' in rendered.text
    assert "vol. 3, no. 4, 1992, pp. 10-15." in rendered.text


def test_ieee_puts_the_initials_first_and_the_year_last(article):
    rendered = format_reference(article, CitationStyle.IEEE)
    assert rendered.text.startswith('M. Ambler, "Women Leaders')
    assert rendered.text.rstrip().endswith("1992.")


def test_chicago_parenthesises_the_year_and_follows_it_with_a_colon(article):
    rendered = format_reference(article, CitationStyle.CHICAGO)
    assert "Tribal College 3, no. 4 (1992): 10-15." in rendered.text


def test_the_four_styles_produce_four_different_strings(article):
    rendered = {format_reference(article, style).text for style in formattable_styles()}
    assert len(rendered) == 4


# --- Standalone works -------------------------------------------------------


def test_a_book_title_is_not_put_in_quotation_marks(book):
    for style in (CitationStyle.MLA, CitationStyle.IEEE, CitationStyle.CHICAGO):
        assert '"A History of Reading' not in format_reference(book, style).text


def test_a_book_is_italicised_by_its_own_title_not_by_its_publisher(book):
    assert format_reference(book, CitationStyle.MLA).italic == "A History of Reading"


def test_an_article_is_italicised_by_its_journal(article):
    assert format_reference(article, CitationStyle.MLA).italic == "Tribal College"


def test_chicago_gives_a_book_its_place_of_publication(book):
    assert "New York: Viking, 1996." in format_reference(book, CitationStyle.CHICAGO).text


# --- Author lists -----------------------------------------------------------


def test_apa_initialises_every_given_name():
    citation = Citation(
        title="Habit formation in adolescence",
        authors=[Author(given="Li", family="Chen"), Author(given="Rosa", family="Diaz")],
        year="2011",
    )
    assert "Chen, L., & Diaz, R." in format_reference(citation, CitationStyle.APA).text


def test_mla_credits_three_or_more_authors_to_the_first():
    citation = Citation(
        title="A collaborative study",
        authors=[
            Author(given="Li", family="Chen"),
            Author(given="Rosa", family="Diaz"),
            Author(given="Paul", family="Ellis"),
        ],
        year="2011",
    )
    rendered = format_reference(citation, CitationStyle.MLA)
    assert rendered.text.startswith("Chen, Li, et al.")
    assert "Ellis" not in rendered.text


def test_chicago_inverts_only_the_first_author():
    citation = Citation(
        title="A joint study",
        authors=[Author(given="Li", family="Chen"), Author(given="Rosa", family="Diaz")],
        year="2011",
    )
    assert "Chen, Li, and Rosa Diaz." in format_reference(citation, CitationStyle.CHICAGO).text


# --- Honesty ----------------------------------------------------------------


def test_an_absent_element_is_omitted_rather_than_invented():
    sparse = Citation(title="Only a title", raw_text="Only a title")
    rendered = format_reference(sparse, CitationStyle.MLA)
    assert rendered.text == '"Only a title."'
    assert not rendered.complete


def test_an_absent_element_is_named_so_the_reader_can_supply_it():
    sparse = Citation(title="Only a title", raw_text="Only a title")
    assert set(format_reference(sparse, CitationStyle.APA).omitted) == {
        "author",
        "year",
        "venue",
        "pages",
    }


def test_a_complete_reference_reports_nothing_missing(article):
    assert format_reference(article, CitationStyle.IEEE).complete


def test_a_missing_year_leaves_no_empty_parentheses_behind():
    citation = Citation(
        title="Undated notes",
        authors=[Author(given="Li", family="Chen")],
        journal="Journal of Reading",
    )
    assert "()" not in format_reference(citation, CitationStyle.APA).text
    assert "()" not in format_reference(citation, CitationStyle.CHICAGO).text


def test_a_title_is_never_recased(article):
    # Recasing means deciding which words are proper nouns, and a recaser that
    # lowercases "Indian" has corrupted the source.
    for style in formattable_styles():
        assert "Women Leaders in Indian Education" in format_reference(article, style).text


# --- List ordering ----------------------------------------------------------


def test_ieee_numbers_the_list_in_document_order(article, book):
    rendered = format_reference_list([book, article], CitationStyle.IEEE)
    assert [ref.marker for ref in rendered] == ["[1]", "[2]"]
    assert "Manguel" in rendered[0].text


def test_the_alphabetised_styles_sort_by_surname_and_carry_no_marker(article, book):
    rendered = format_reference_list([book, article], CitationStyle.MLA)
    assert rendered[0].text.startswith("Ambler")
    assert rendered[1].text.startswith("Manguel")
    assert all(not ref.marker for ref in rendered)


def test_an_unknown_style_falls_back_to_apa(article):
    assert (
        format_reference(article, CitationStyle.UNKNOWN).text
        == format_reference(article, CitationStyle.APA).text
    )


# --- The reference material -------------------------------------------------


def test_every_style_is_documented():
    assert len(style_guides()) == 4
    for guide in style_guides():
        assert guide.principle.strip()
        assert guide.elements
        assert guide.distinctives
        assert guide.sample.strip()


def test_mla_documents_all_nine_core_elements():
    guide = style_guide(CitationStyle.MLA)
    assert len(guide.elements) == 9
    assert guide.list_heading == "Works Cited"
    assert "container" in " ".join(name for name, _rule in guide.elements).lower()


def test_a_short_name_drops_the_edition():
    assert style_guide(CitationStyle.CHICAGO).short_name == "Chicago"
    assert style_guide(CitationStyle.IEEE).short_name == "IEEE"
