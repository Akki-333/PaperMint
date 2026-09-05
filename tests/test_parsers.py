from papermint.models import CitationStyle, DetectionMethod, DocumentKind
from papermint.parsers.bibliography_detector import (
    _citation_signal,
    _is_prose,
    characterize_document,
    detect_bibliography_section,
)
from papermint.parsers.citation_parser import parse_citation
from papermint.parsers.citation_splitter import split_citations
from papermint.parsers.style_detector import detect_style

# --- Bibliography Detector Tests ---


def test_detect_references_header(sample_apa_text):
    full_text = "Some intro text.\n\n" + sample_apa_text
    extracted = detect_bibliography_section(full_text)
    assert "Smith, J. A." in extracted
    assert "References" not in extracted  # it skips the header


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


def test_detect_force_parse():
    text = "This is random text with no bibliography markers."
    extracted = detect_bibliography_section(text, force_parse=True)
    assert extracted == text.strip()


# --- Citation Splitter Tests ---


def test_split_numbered_citations(sample_ieee_text):
    citations = split_citations(sample_ieee_text)
    assert len(citations) == 3
    assert "J. A. Smith" in citations[0]


def test_split_blank_line_separated():
    text = "Smith, J. (2020). Title One. Journal, 1(1).\n\nDoe, A. (2021). Title Two. Journal, 2(2).\n\nBrown, B. (2019). Title Three."
    citations = split_citations(text)
    assert len(citations) == 3


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
    style, _conf = detect_style(citations)
    assert style == CitationStyle.UNKNOWN


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
    text = "Smith, J. A., & Doe, R. B. (2020). Machine learning in citation parsing. Journal of AI, 1(1), 45-67."
    cit = parse_citation(text, CitationStyle.APA)
    assert cit.year == "2020"
    assert len(cit.authors) == 2
    assert cit.authors[0].family == "Smith"
    assert cit.title == "Machine learning in citation parsing"


def test_parse_ieee_citation():
    text = '[1] J. A. Smith and R. B. Doe, "Machine learning," Journal, 2020.'
    cit = parse_citation(text, CitationStyle.IEEE)
    assert len(cit.authors) == 2
    assert cit.authors[0].family == "Smith"
    assert cit.title == "Machine learning"


def test_confidence_is_reasonable():
    """Confidence should be > 25% for citations with title, authors, year."""
    text = "Smith, J. (2020). Machine learning advances. Journal of AI, 1(1), 45-67."
    cit = parse_citation(text, CitationStyle.APA)
    assert cit.confidence >= 0.4, f"Confidence too low: {cit.confidence}"


def test_parse_extracts_volume_pages():
    """Parser should extract volume, issue, and pages."""
    text = "Smith, J. (2020). Title. Journal Name, vol. 12, no. 3, pp. 45-67."
    cit = parse_citation(text, CitationStyle.APA)
    assert cit.volume == "12"
    assert cit.pages == "45-67"


def test_parse_extracts_publisher():
    """Parser should extract publisher names."""
    text = "Smith, J. (2020). Book Title. Cambridge University Press."
    cit = parse_citation(text, CitationStyle.APA)
    assert "University Press" in cit.publisher or "Cambridge" in cit.publisher


def test_parse_empty():
    cit = parse_citation("")
    assert cit.confidence == 0.0
    assert cit.title == ""


def test_title_extraction_fallback():
    """Should extract title even without standard formatting."""
    text = "Smith, J. 2020. The impact of climate change on agriculture. Some Publisher."
    cit = parse_citation(text)
    assert cit.title != "", f"Title should not be empty for: {text}"


def test_detect_front_matter_annotated_bibliography():
    """Documents with front matter declaring an annotated bibliography must be recognized autonomously."""
    from papermint.models import DocumentKind
    from papermint.parsers.bibliography_detector import characterize_document

    text = (
        "RESOLUTION TEST CHART\n"
        "BUREAU OF STANDARDS-1963-A\n\n"
        "ED 060 699\n"
        "DOCUMENT RESUME\n"
        "TITLE An Annotated Bibliography of Young People's Fiction on American Indians.\n"
        "1972.\n\n"
        "Acker, Helen. LEE NATONI: YOUNG NAVAJO.\n"
        "Illus. by Richard Kennedy. 136 p.\n"
        "Abelard-Schuman. 1968.\n"
        "Lee Natoni and his sister and mother are happy living in their isolated home.\n\n"
        "Allen, Henry. VALLEY OF THE BEAR.\n"
        "Houghton Mifflin Co. 1964. 184 p.\n"
        "Because Mouse and his crippled grandmother have both been spared in encounters.\n"
    )
    outcome = characterize_document(text)
    assert outcome.kind is DocumentKind.ANNOTATED_BIBLIOGRAPHY
    assert outcome.found
    assert outcome.confidence >= 0.9


def test_detect_multi_line_part_heading():
    """Two-line headings like PART TWO\\nAnnotated Bibliography must be recognized."""
    from papermint.parsers.bibliography_detector import characterize_document

    text = (
        "Introductory notes and administrative preface.\n\n"
        "PART TWO\n"
        "Annotated Bibliography\n\n"
        "Acker, Helen. LEE NATONI: YOUNG NAVAJO.\n"
        "Abelard-Schuman. 1968. 136 p.\n"
        "Lee Natoni and his sister are happy.\n\n"
        "Buff, Mary. HAH-NEE OF THE CLIFF DWELLERS.\n"
        "Houghton Mifflin Co. 1956. 68 p.\n"
        "It is the time of the long drought.\n"
    )
    outcome = characterize_document(text)
    assert outcome.found
    assert "PART TWO Annotated Bibliography" in outcome.notes[0]
    assert "Introductory notes" in outcome.body_text
    assert "Acker, Helen" in outcome.bibliography_text


# --- The line-level signal must not fire on prose -------------------------

PROSE_WITH_PROPER_NOUNS = [
    "The Ministry of Education published new guidance.",
    "This Agreement shall be governed by English law.",
    "The European Commission has proposed a new directive.",
    "Under the Data Protection Act citizens may request their records.",
    "The Prime Minister addressed Parliament on Tuesday morning.",
    "Chapter Three describes the Method in detail.",
    "The United States Department of Agriculture negotiated new terms.",
]

HUMANITIES_CATALOGUE_LINES = [
    "Acker, Helen. The Boy Who Lived With the Bears. Illus. by Ray Cruz.",
    "Abelard-Schuman. 1968. 136 p.",
    "* Buff, Mary and Conrad. Hah-Nee of the Cliff Dwellers.",
    "Acker, Helen. LEE NATONI: YOUNG NAVAJO.",
    "Houghton Mifflin Co. 1964. 184 p.",
]


def test_citation_signal_rejects_prose_carrying_proper_nouns():
    """A capitalised name in a sentence is not a reference.

    The signal briefly reduced to "starts with a capital, has a later capital,
    contains a period", which flagged ten of twelve ordinary prose lines and
    scored a pure-prose policy document at 89% citation density.
    """
    for line in PROSE_WITH_PROPER_NOUNS:
        assert _citation_signal(line) is False, line


def test_citation_signal_accepts_humanities_catalogue_lines():
    for line in HUMANITIES_CATALOGUE_LINES:
        assert _citation_signal(line) is True, line


def test_prose_lines_are_still_recognised_as_prose():
    """_is_prose drives the backwards scan's stopping condition.

    Once every prose line reads as a citation signal, _is_prose can never
    return True, the prose-run break becomes unreachable, and the scan walks
    up through the body swallowing it into the bibliography.
    """
    for line in PROSE_WITH_PROPER_NOUNS:
        if len(line.split()) >= 8:
            assert _is_prose(line) is True, line


def test_prose_document_with_proper_nouns_yields_no_bibliography():
    text = "\n".join(["National Digital Literacy Scheme", "", *PROSE_WITH_PROPER_NOUNS])
    outcome = characterize_document(text)
    assert outcome.kind is DocumentKind.NON_ACADEMIC
    assert outcome.bibliography_text == ""


# --- A front-matter keyword must not outrank structure --------------------


def test_an_abstract_mentioning_bibliography_is_not_a_bibliography():
    """The keyword must head the line, not merely appear in it.

    An unanchored search classified this paper as a bibliography at 0.95
    confidence, with the whole document as the reference list and no body.
    """
    text = (
        "Automated Citation Extraction at Scale\n\n"
        "Abstract\n"
        "We present a system that constructs a bibliography from scanned documents.\n"
        "The method is evaluated on twelve thousand records drawn from three archives.\n\n"
        "Introduction\n"
        "Citation parsing has been studied for decades in the digital libraries field.\n"
        "Prior systems relied on hand written rules that generalised poorly in practice.\n"
    )
    outcome = characterize_document(text)
    assert outcome.method is not DetectionMethod.TITLE_PAGE
    assert outcome.kind is not DocumentKind.BIBLIOGRAPHY
    assert outcome.bibliography_text == ""
    assert "We present a system" in outcome.body_text


def test_a_contents_line_is_not_a_declaration():
    """ "Bibliography .......... 89" names a section, it does not declare a kind."""
    text = (
        "A Study of Urban Transport Policy\n\n"
        "TABLE OF CONTENTS\n"
        "1. Introduction ......... 1\n"
        "Bibliography .......... 89\n\n"
        "1. Introduction\n"
        "Urban transport policy has shifted markedly over the past decade in Europe.\n"
        "This study examines rail and road investment across three mid sized cities.\n\n"
        "References\n"
        "Smith, J. A. (2020). Machine learning. Journal of Bibliometrics, 15(2), 103-115.\n"
        "Johnson, L. (2019). The future of AI. Tech Press.\n"
    )
    outcome = characterize_document(text)
    assert outcome.kind is DocumentKind.RESEARCH_PAPER
    assert outcome.method is DetectionMethod.SECTION_HEADER
    assert "Urban transport policy" in outcome.body_text


def test_a_structural_heading_outranks_a_front_matter_keyword():
    """A heading on its own line is stronger evidence than a keyword."""
    text = (
        "Notes toward a bibliography of ceramics research\n\n"
        + "Ceramic fatigue is poorly understood in polycrystalline samples.\n" * 12
        + "\nReferences\n"
        "Smith, J. A. (2020). Ceramics. Journal of Materials, 4(1), 1-9.\n"
        "Doe, A. B. (2019). More ceramics. Journal of Materials, 3(2), 2-8.\n"
    )
    outcome = characterize_document(text)
    assert outcome.kind is DocumentKind.RESEARCH_PAPER
    assert outcome.method is DetectionMethod.SECTION_HEADER


def test_a_front_matter_declaration_needs_corroboration():
    """A title alone classifies nothing; the text beneath it must be dense."""
    text = (
        "Selected Bibliography\n\n"
        "This chapter surveys the literature without listing individual entries.\n"
        "It discusses broad trends in the field and offers a narrative overview.\n"
        "No formal reference list follows this heading anywhere in the document.\n"
    )
    outcome = characterize_document(text)
    assert outcome.method is not DetectionMethod.TITLE_PAGE
    assert outcome.kind is not DocumentKind.BIBLIOGRAPHY


# --- Collecting every reference block ---------------------------------------

#: A paper with two reference lists, an appendix between them and an index
#: after them. Reading only the last heading would lose the first list; reading
#: everything after the last heading would turn the index into citations.
MULTI_BLOCK_PAPER = """A Study of Reading Habits

This chapter argues that reading habits are formed early and that the school
library is the decisive institution in that formation. We review the evidence
from three decades of classroom studies and set out a model of acquisition.

References

Ambler, M. (1992). Women leaders in Indian education. Tribal College, 3(4), 10-15.
Brown, T. (2004). Reading and the school library. Educational Press.
Chen, L. and Diaz, R. (2011). Habit formation. Journal of Reading, 22(1), 44-61.

Appendix A: Survey instrument

Respondents were asked to rate each statement on a five point scale running
from strongly disagree to strongly agree. The instrument was piloted with a
sample of forty pupils drawn from two schools in the same local authority.
Item wording was revised twice before the main study went into the field.

Further reading

Ellis, P. (2015). The library as classroom. vol. 8, pp. 3-19.
Fisher, K. (2019). Adolescent literacy now. Reading Trust Press. 210 p.

Index

reading habits, 3
school library, 4
"""

#: A paper whose first heading introduces discussion rather than references.
#: The block beneath it must not be collected, or a chapter of prose joins the
#: bibliography on the strength of a keyword.
DISCURSIVE_HEADING_PAPER = """Reading and its Institutions

Further reading

The literature on this question is uneven and much of it predates the
comprehensive reforms, so a reader coming to it now should begin with the
review articles rather than the primary studies, which assume a policy
context that no longer holds anywhere in the system as it stands today.

References

Ambler, M. (1992). Women leaders in Indian education. Tribal College, 3(4), 10-15.
Brown, T. (2004). Reading and the school library. Educational Press.
Chen, L. and Diaz, R. (2011). Habit formation. Journal of Reading, 22(1), 44-61.
"""


def test_every_reference_block_is_collected_not_only_the_last():
    outcome = characterize_document(MULTI_BLOCK_PAPER)
    assert "Ambler" in outcome.bibliography_text
    assert "Ellis" in outcome.bibliography_text
    assert "2 reference blocks" in outcome.notes[0]


def test_an_appendix_between_two_lists_stays_in_the_body():
    outcome = characterize_document(MULTI_BLOCK_PAPER)
    assert "five point scale" not in outcome.bibliography_text
    assert "five point scale" in outcome.body_text


def test_an_index_after_the_references_is_not_read_as_entries():
    outcome = characterize_document(MULTI_BLOCK_PAPER)
    assert "school library, 4" not in outcome.bibliography_text


def test_a_heading_whose_block_is_prose_is_not_collected():
    # The negative case: an earlier heading has to earn its place by looking
    # like references, or a keyword drags a chapter of discussion in with it.
    outcome = characterize_document(DISCURSIVE_HEADING_PAPER)
    assert "predates the" not in outcome.bibliography_text
    assert "Ambler" in outcome.bibliography_text


def test_a_single_reference_section_still_names_its_heading():
    outcome = characterize_document(DISCURSIVE_HEADING_PAPER)
    assert outcome.notes[0].startswith("Matched the heading")
