import pytest
from papermint.parsers.bibliography_detector import detect_bibliography_section
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style
from papermint.parsers.citation_parser import parse_citation
from papermint.models import CitationStyle

# --- Bibliography Detector Tests ---

def test_detect_references_header(sample_apa_text):
    full_text = "Some intro text.\n\n" + sample_apa_text
    extracted = detect_bibliography_section(full_text)
    assert "Smith, J. A." in extracted
    assert "References" not in extracted # it skips the header

def test_detect_bibliography_header():
    full_text = "Content.\n\nBibliography\nCitation 1\nCitation 2"
    extracted = detect_bibliography_section(full_text)
    assert extracted == "Citation 1\nCitation 2"

def test_detect_numbered_section_header():
    full_text = "Content.\n\n7. References\nCitation 1"
    extracted = detect_bibliography_section(full_text)
    assert extracted == "Citation 1"

def test_detect_fallback_no_header():
    text = "Line 1\nLine 2\nSmith, J. (2020). Book. 10.1234/567\nDoe, A. (2021). Article."
    # Should use density heuristic or fallback
    extracted = detect_bibliography_section(text)
    assert "Smith, J." in extracted

def test_detect_empty_text():
    assert detect_bibliography_section("") == ""
    assert detect_bibliography_section("   ") == ""


# --- Citation Splitter Tests ---

def test_split_numbered_citations(sample_ieee_text):
    citations = split_citations(sample_ieee_text)
    assert len(citations) == 3
    assert "J. A. Smith" in citations[0]

def test_split_blank_line_separated():
    text = "Citation 1 text\nmore text\n\nCitation 2 text\n\nCitation 3"
    citations = split_citations(text)
    assert len(citations) == 3
    assert citations[0] == "Citation 1 text\nmore text"

def test_split_author_boundaries(sample_apa_text):
    # Strip "References\n"
    text = "\n".join(sample_apa_text.split("\n")[1:])
    citations = split_citations(text)
    assert len(citations) == 3
    assert "Smith, J. A." in citations[0]

def test_split_single_citation():
    text = "Just one single citation block."
    assert split_citations(text) == [text]

def test_split_empty_text():
    assert split_citations("") == []


# --- Style Detector Tests ---

def test_detect_apa(sample_apa_text):
    citations = sample_apa_text.split("\n")[1:]
    style, conf = detect_style(citations)
    assert style == CitationStyle.APA
    assert 0 < conf <= 1.0

def test_detect_ieee(sample_ieee_text):
    citations = split_citations(sample_ieee_text)
    style, conf = detect_style(citations)
    assert style == CitationStyle.IEEE
    assert 0 < conf <= 1.0

def test_detect_mla(sample_mla_text):
    citations = sample_mla_text.split("\n")
    style, conf = detect_style(citations)
    assert style == CitationStyle.MLA
    assert 0 < conf <= 1.0

def test_detect_unknown():
    citations = ["Random string 1", "Random string 2"]
    style, conf = detect_style(citations)
    assert style == CitationStyle.UNKNOWN
    assert conf < 0.2

def test_detect_style_empty():
    style, conf = detect_style([])
    assert style == CitationStyle.UNKNOWN
    assert conf == 0.0


# --- Citation Parser Tests ---

def test_extract_doi():
    cit = parse_citation("Text 10.1234/abc.def text")
    assert cit.doi == "10.1234/abc.def"

def test_extract_year():
    cit = parse_citation("Author (2020). Title.")
    assert cit.year == "2020"
    
    cit2 = parse_citation("Author. 1999. Title.")
    assert cit2.year == "1999"

def test_parse_apa_citation():
    text = "Smith, J. A., & Doe, R. B. (2020). Machine learning. Journal, 1(1)."
    cit = parse_citation(text, CitationStyle.APA)
    assert cit.year == "2020"
    assert len(cit.authors) == 2
    assert cit.authors[0].family == "Smith"
    assert cit.title == "Machine learning"

def test_parse_ieee_citation():
    text = "[1] J. A. Smith and R. B. Doe, \"Machine learning,\" Journal, 2020."
    cit = parse_citation(text, CitationStyle.IEEE)
    assert len(cit.authors) == 2
    assert cit.authors[0].family == "Smith"
    assert cit.title == "Machine learning"

def test_confidence_calculation():
    text = "Smith, J. (2020). Title. 10.1234/56"
    cit = parse_citation(text, CitationStyle.APA)
    # has year, authors, title, doi -> 4 fields
    assert cit.confidence > 0.0

def test_parse_empty():
    cit = parse_citation("")
    assert cit.confidence == 0.0
    assert cit.title == ""
