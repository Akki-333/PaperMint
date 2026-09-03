import pytest

from papermint.models import Author, Citation, CitationStyle, EntryType


@pytest.fixture
def sample_apa_text():
    return """References
Smith, J. A., & Doe, R. B. (2020). Machine learning in citation parsing. Journal of Bibliometrics, 15(2), 103-115. https://doi.org/10.1016/j.jbi.2020.01.002
Johnson, L. (2019). The future of AI. Tech Press.
Williams, C. D., Brown, E., & Davis, F. (2021). Neural networks for text extraction. IEEE Transactions on Neural Networks, 32(4), 10-25."""


@pytest.fixture
def sample_ieee_text():
    return """[1] J. A. Smith and R. B. Doe, "Machine learning in citation parsing," Journal of Bibliometrics, vol. 15, no. 2, pp. 103-115, 2020.
[2] L. Johnson, "The future of AI," Tech Press, 2019.
[3] C. D. Williams, E. Brown, and F. Davis, "Neural networks for text extraction," IEEE Transactions on Neural Networks, vol. 32, no. 4, pp. 10-25, 2021."""


@pytest.fixture
def sample_mla_text():
    return """Smith, John A., and Robert B. Doe. "Machine learning in citation parsing." Journal of Bibliometrics, vol. 15, no. 2, 2020, pp. 103-115.
Johnson, Laura. "The future of AI." Tech Press, 2019.
Williams, Charles D., et al. "Neural networks for text extraction." IEEE Transactions on Neural Networks, vol. 32, no. 4, 2021, pp. 10-25."""


@pytest.fixture
def sample_author():
    return Author(given="John A.", family="Smith")


@pytest.fixture
def sample_citation(sample_author):
    return Citation(
        title="Machine learning in citation parsing",
        authors=[sample_author, Author(given="Robert B.", family="Doe")],
        year="2020",
        journal="Journal of Bibliometrics",
        volume="15",
        issue="2",
        pages="103-115",
        doi="10.1016/j.jbi.2020.01.002",
        url="https://doi.org/10.1016/j.jbi.2020.01.002",
        publisher="Elsevier",
        address="New York",
        edition="1st",
        booktitle="",
        raw_text="Smith, J. A., & Doe, R. B. (2020). Machine learning in citation parsing. Journal of Bibliometrics, 15(2), 103-115.",
        style=CitationStyle.APA,
        entry_type=EntryType.ARTICLE,
        confidence=0.9,
    )


@pytest.fixture
def sample_citations(sample_citation):
    c2 = Citation(
        title="The future of AI",
        authors=[Author(given="Laura", family="Johnson")],
        year="2019",
        publisher="Tech Press",
        entry_type=EntryType.BOOK,
        style=CitationStyle.APA,
        confidence=0.8,
    )
    c3 = Citation(
        title="Neural networks for text extraction",
        authors=[
            Author(given="Charles D.", family="Williams"),
            Author(given="Emily", family="Brown"),
            Author(given="Frank", family="Davis"),
        ],
        year="2021",
        journal="IEEE Transactions on Neural Networks",
        volume="32",
        issue="4",
        pages="10-25",
        style=CitationStyle.APA,
        confidence=0.85,
    )
    return [sample_citation, c2, c3]
