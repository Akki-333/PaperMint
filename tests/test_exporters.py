import pytest
from io import BytesIO
from papermint.exporters.bibtex_exporter import export_bibtex
from papermint.exporters.ris_exporter import export_ris
from papermint.exporters.csv_exporter import export_csv, export_excel

def test_bibtex_export_valid(sample_citations):
    output = export_bibtex(sample_citations)
    assert "@article{smith_2020_machine," in output
    assert "author  = {Smith, John A. and Doe, Robert B.}" in output
    assert "title   = {Machine learning in citation parsing}" in output
    assert "year    = {2020}" in output
    
def test_bibtex_export_empty():
    assert export_bibtex([]) == ""

def test_ris_export_valid(sample_citations):
    output = export_ris(sample_citations)
    assert "TY  - JOUR" in output
    assert "AU  - Smith, John A." in output
    assert "TI  - Machine learning in citation parsing" in output
    assert "PY  - 2020" in output
    assert "ER  - " in output

def test_ris_export_empty():
    assert export_ris([]) == ""

def test_csv_export_headers(sample_citations):
    output = export_csv(sample_citations)
    headers = "Title,Authors,Year,Journal,Volume,Issue,Pages,DOI,URL,Publisher,Confidence"
    assert headers in output
    
def test_csv_export_data(sample_citations):
    output = export_csv(sample_citations)
    assert "Machine learning in citation parsing" in output
    assert "Smith, John A. & Doe, Robert B." in output or "Smith, John A.; Doe, Robert B." in output
    assert "2020" in output

def test_excel_export_returns_bytesio(sample_citations):
    output = export_excel(sample_citations)
    assert isinstance(output, BytesIO)
    output.seek(0)
    assert len(output.read()) > 0
