import pytest
from pydantic import ValidationError

from papermint.models import Author, Citation, CitationStyle, EntryType, ExtractionResult


def test_citation_defaults():
    citation = Citation()
    assert citation.title == ""
    assert citation.authors == []
    assert citation.style == CitationStyle.UNKNOWN
    assert citation.entry_type == EntryType.ARTICLE
    assert citation.confidence == 0.0


def test_citation_full_data(sample_citation):
    assert sample_citation.title == "Machine learning in citation parsing"
    assert len(sample_citation.authors) == 2
    assert sample_citation.year == "2020"
    assert sample_citation.style == CitationStyle.APA


def test_author_full_name():
    author = Author(given="John", family="Doe")
    assert author.full_name == "John Doe"

    author_only_family = Author(family="Smith")
    assert author_only_family.full_name == "Smith"


def test_author_citation_name():
    author = Author(given="John", family="Doe")
    assert author.citation_name == "Doe, John"

    author_only_family = Author(family="Smith")
    assert author_only_family.citation_name == "Smith"


def test_citation_cite_key(sample_citation):
    assert sample_citation.cite_key == "smith_2020_machine"

    empty_cit = Citation()
    assert empty_cit.cite_key == "unknown"


def test_citation_author_string():
    # 1 author
    c1 = Citation(authors=[Author(given="John", family="Doe")])
    assert c1.author_string == "Doe, John"

    # 2 authors
    c2 = Citation(
        authors=[Author(given="John", family="Doe"), Author(given="Jane", family="Smith")]
    )
    assert c2.author_string == "Doe, John & Smith, Jane"

    # 3 authors
    c3 = Citation(
        authors=[
            Author(given="John", family="Doe"),
            Author(given="Jane", family="Smith"),
            Author(given="Bob", family="Brown"),
        ]
    )
    assert c3.author_string == "Doe, John, Smith, Jane, & Brown, Bob"

    # 0 authors
    c0 = Citation()
    assert c0.author_string == ""


def test_citation_fields_found(sample_citation):
    # title, year, journal, doi, volume, pages, publisher, authors -> 8 fields
    assert sample_citation.fields_found == 8

    empty_cit = Citation()
    assert empty_cit.fields_found == 0


def test_citation_style_enum():
    assert CitationStyle.APA.value == "apa"
    assert CitationStyle.MLA.value == "mla"
    assert CitationStyle.IEEE.value == "ieee"
    assert CitationStyle.CHICAGO.value == "chicago"
    assert CitationStyle.UNKNOWN.value == "unknown"


def test_entry_type_enum():
    assert EntryType.ARTICLE.value == "article"
    assert EntryType.BOOK.value == "book"


def test_extraction_result_citation_count(sample_citations):
    res = ExtractionResult(citations=sample_citations)
    assert res.citation_count == 3

    res_empty = ExtractionResult()
    assert res_empty.citation_count == 0


def test_citation_confidence_bounds():
    # Valid
    c = Citation(confidence=0.5)
    assert c.confidence == 0.5

    # Invalid
    with pytest.raises(ValidationError):
        Citation(confidence=-0.1)

    with pytest.raises(ValidationError):
        Citation(confidence=1.1)
