"""Tests for the presentation layer.

The component tests assert on generated markup, which is where the interface's
two historical failure modes lived: unescaped document text corrupting a card,
and indented HTML being rendered as a Markdown code block. The page tests run
the real application through Streamlit's own harness and assert that no screen
raises.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from papermint.models import Author, Citation, CitationStyle, ConfidenceBand
from papermint.ui.components.citation_card import (
    _card_markup,
    _parse_author_field,
    citation_preview_text,
)
from papermint.ui.components.export_panel import EXPORT_FORMATS, safe_filename
from papermint.ui.components.file_uploader import read_upload, upload_signature
from papermint.ui.html import clamp, compact, dot_join, esc
from papermint.ui.icons import available_icons, icon
from papermint.ui.navigation import route_names
from papermint.ui.styles import build_stylesheet
from papermint.ui.theme import COLOR, band_color, css_variables


@pytest.fixture
def citation() -> Citation:
    """Return a fully populated citation."""
    return Citation(
        title="Machine learning in citation parsing",
        authors=[Author(given="J. A.", family="Smith")],
        year="2020",
        journal="Journal of Bibliometrics",
        volume="15",
        issue="2",
        pages="103-115",
        doi="10.1016/j.jbi.2020.01.002",
        style=CitationStyle.APA,
        confidence=0.9,
        raw_text="Smith, J. A. (2020). Machine learning in citation parsing.",
    )


# --- HTML helpers ----------------------------------------------------------


def test_escaping_neutralises_markup():
    assert esc('<script>alert("x")</script>') == (
        "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
    )


def test_escaping_handles_none():
    assert esc(None) == ""


def test_compact_removes_indentation_that_markdown_would_eat():
    markup = "    <div>\n        <span>hi</span>\n    </div>"
    result = compact(markup)
    assert not result.startswith(" ")
    assert "\n    " not in result
    assert result == "<div><span>hi</span></div>"


def test_clamp_breaks_on_a_word_boundary():
    assert clamp("alpha beta gamma delta", 12).endswith("…")
    assert clamp("short", 40) == "short"


def test_dot_join_drops_empty_parts():
    assert dot_join("a", "", "b") == "a · b"


# --- Theme and icons -------------------------------------------------------


def test_every_token_becomes_a_css_variable():
    variables = css_variables()
    assert "--pm-color-accent: #34D399;" in variables
    assert "--pm-space-4: 16px;" in variables


def test_confidence_bands_map_to_distinct_colours():
    colours = {band_color(band) for band in ConfidenceBand}
    assert len(colours) == 3
    assert band_color(ConfidenceBand.HIGH) == COLOR["positive"]


def test_icons_inherit_the_text_colour():
    svg = icon("leaf")
    assert 'stroke="currentColor"' in svg
    assert 'aria-hidden="true"' in svg


def test_an_unknown_icon_renders_nothing_rather_than_raising():
    assert icon("no-such-icon") == ""


def test_the_icon_set_is_not_empty():
    assert len(available_icons()) >= 15


def test_the_stylesheet_uses_tokens_not_literals():
    css = build_stylesheet()
    assert "--pm-color-accent" in css
    assert "stTabs" in css
    assert "pm-card" in css


# --- Citation card ---------------------------------------------------------


def test_card_shows_every_parsed_field(citation):
    markup = _card_markup(citation, 1)
    assert "Machine learning in citation parsing" in markup
    assert "Smith, J. A." in markup
    assert "Journal of Bibliometrics" in markup
    assert "vol. 15, no. 2, pp. 103-115" in markup
    assert "10.1016/j.jbi.2020.01.002" in markup


def test_card_escapes_document_text():
    hostile = Citation(title="A <b>bold</b> claim & more", raw_text="x", confidence=0.5)
    markup = _card_markup(hostile, 1)
    assert "<b>bold</b>" not in markup
    assert "&lt;b&gt;bold&lt;/b&gt;" in markup


def test_card_never_indents_enough_to_become_a_code_block(citation):
    assert "\n    " not in _card_markup(citation, 1)


def test_card_uses_raw_text_when_no_title_was_parsed():
    unparsed = Citation(raw_text="Some unparseable entry text here", confidence=0.1)
    markup = _card_markup(unparsed, 3)
    assert "Untitled" not in markup
    assert "Some unparseable entry text here" in markup
    assert "is-unparsed" in markup


def test_card_lists_missing_fields_on_low_confidence_entries():
    sparse = Citation(title="Only a title", confidence=0.2, raw_text="x")
    assert "Not found:" in _card_markup(sparse, 1)


def test_card_hides_missing_fields_on_complete_entries(citation):
    assert "Not found:" not in _card_markup(citation, 1)


def test_edited_authors_round_trip_in_either_order():
    authors = _parse_author_field("Smith, J. A.; Robert B. Doe")
    assert [a.family for a in authors] == ["Smith", "Doe"]
    assert authors[1].given == "Robert B."


def test_preview_text_is_one_line(citation):
    assert "\n" not in citation_preview_text(citation)


# --- Export panel ----------------------------------------------------------


def test_filenames_are_made_safe():
    assert safe_filename("My Paper (final)/v2") == "My_Paper_final_v2"
    assert safe_filename("") == "citations"
    assert safe_filename("///") == "citations"


def test_every_export_format_is_serialisable(citation):
    for fmt in EXPORT_FORMATS:
        payload = fmt.serialise([citation])
        assert payload is not None
        if isinstance(payload, str):
            assert payload.strip()


# --- Upload handling -------------------------------------------------------


def test_upload_is_readable_more_than_once():
    buffer = io.BytesIO(b"payload")
    assert read_upload(buffer) == b"payload"
    assert read_upload(buffer) == b"payload"


def test_upload_signature_changes_with_the_options():
    buffer = io.BytesIO(b"payload")
    assert upload_signature(buffer, False) != upload_signature(buffer, True)


# --- Pages -----------------------------------------------------------------


APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_the_app_starts_without_error():
    harness = AppTest.from_file(str(APP_PATH), default_timeout=120)
    harness.run()
    assert not harness.exception, [str(e.value) for e in harness.exception]


@pytest.mark.parametrize("route", route_names())
def test_every_page_renders_without_error(route: str):
    # A page object can only be executed through a navigation, so each route
    # is driven by a navigation restricted to that one page.
    script = (
        "from papermint.ui.styles import inject_custom_css\n"
        "from papermint.ui.navigation import build_navigation\n"
        "inject_custom_css()\n"
        f"build_navigation(only={route!r}).run()\n"
    )
    harness = AppTest.from_string(script, default_timeout=120)
    harness.run()
    assert not harness.exception, [str(e.value) for e in harness.exception]


def test_the_navigation_exposes_every_route():
    assert set(route_names()) == {"home", "extract", "batch", "doi", "about"}
