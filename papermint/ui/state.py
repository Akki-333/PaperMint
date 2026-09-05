"""Session state that survives moving between pages.

Streamlit discards the state of any widget that is not instantiated during a
script run. Navigating from the analyzer to the dashboard and back therefore
used to reset the search box, the sort order, the reading mode and the upload
control itself, so a reader who glanced at the About page returned to an empty
screen and had to upload their document again.

The fix is a shadow copy. Every widget whose value should outlive a page
switch is mirrored under a prefixed key that no widget owns, so nothing
collects it. :func:`restore` seeds the widget key from that mirror *before* the
widget is created, which is the only point at which Streamlit accepts a
programmatic default, and :func:`retain` copies the live value back afterwards.

The cached pipeline results are ordinary session-state entries and were always
safe; what was lost was the widget state around them, which is why the results
appeared to vanish even though they were still in memory.
"""

from __future__ import annotations

import streamlit as st

#: Namespace for shadow copies. No widget may use this prefix, or Streamlit
#: would collect the mirror along with the value it is meant to protect.
_SHADOW = "_pm_kept_"


def restore(*keys: str) -> None:
    """Seed widget keys from their shadow copies.

    Call once at the top of a page render, before any of the named widgets is
    created. A key that already carries a value is left alone, so this can
    never overwrite something the reader has just entered.

    Args:
        *keys: The widget keys to restore.
    """
    for key in keys:
        shadow = _SHADOW + key
        if key not in st.session_state and shadow in st.session_state:
            st.session_state[key] = st.session_state[shadow]


def restore_within(key: str, low: int, high: int) -> None:
    """Restore an integer widget value, clamped to a range that may have moved.

    A page number is the case that needs this: the reader was on page four,
    then filtered the list down to a single page, and handing four back to the
    slider would raise rather than simply showing page one.

    Args:
        key: The widget key to restore.
        low: The lowest value the widget will now accept.
        high: The highest value the widget will now accept.
    """
    shadow = _SHADOW + key
    if key in st.session_state or shadow not in st.session_state:
        return
    remembered = st.session_state[shadow]
    if isinstance(remembered, int):
        st.session_state[key] = max(low, min(high, remembered))


def retain(*keys: str) -> None:
    """Copy live widget values into their shadow copies.

    Call after the widgets have been created, at the end of a page render.
    Absent keys are skipped, so a widget behind a collapsed expander or a
    conditional branch costs nothing.

    Args:
        *keys: The widget keys to remember.
    """
    for key in keys:
        if key in st.session_state:
            st.session_state[_SHADOW + key] = st.session_state[key]


def forget(*keys: str) -> None:
    """Drop a value and its shadow copy.

    Args:
        *keys: The keys to clear. Missing keys are ignored.
    """
    for key in keys:
        st.session_state.pop(key, None)
        st.session_state.pop(_SHADOW + key, None)


__all__ = ["forget", "restore", "restore_within", "retain"]
