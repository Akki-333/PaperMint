import pytest
from unittest.mock import patch, MagicMock
from papermint.enrichment.crossref import extract_dois_from_text, lookup_doi

def test_extract_dois_from_text_found():
    text = "Here is a doi 10.1234/abc and another 10.5678/def.ghi in the text."
    dois = extract_dois_from_text(text)
    assert "10.1234/abc" in dois
    assert "10.5678/def.ghi" in dois

def test_extract_dois_from_text_empty():
    assert extract_dois_from_text("No doi here") == []
    assert extract_dois_from_text("") == []

@patch('papermint.enrichment.crossref.Crossref')
def test_lookup_doi_valid(mock_crossref_class):
    mock_instance = MagicMock()
    mock_crossref_class.return_value = mock_instance
    
    mock_instance.works.return_value = {
        "status": "ok",
        "message": {
            "title": ["Test Title"],
            "author": [{"given": "John", "family": "Doe"}],
            "published-print": {"date-parts": [[2021]]},
            "container-title": ["Test Journal"]
        }
    }
    
    result = lookup_doi("10.1234/test")
    assert result is not None
    assert result.title == "Test Title"
    assert result.year == "2021"
    assert result.journal == "Test Journal"
    assert len(result.authors) == 1
    assert result.authors[0].family == "Doe"
    assert result.doi == "10.1234/test"

@patch('papermint.enrichment.crossref.Crossref')
def test_lookup_doi_invalid(mock_crossref_class):
    mock_instance = MagicMock()
    mock_crossref_class.return_value = mock_instance
    mock_instance.works.return_value = {"status": "failed"}
    
    assert lookup_doi("10.invalid/doi") is None
    
def test_lookup_doi_empty():
    assert lookup_doi("") is None
