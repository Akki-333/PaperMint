"""The upload control and the safe way to read what it returns.

``UploadedFile`` subclasses ``BytesIO`` and Streamlit hands back the same
object on every rerun. Calling ``read()`` therefore works exactly once: after
the first call the cursor sits at end-of-file, and every later rerun, which
means every keystroke in a search box and every change of a sort order, reads
back zero bytes. :func:`read_upload` uses ``getvalue()`` so the bytes are
always complete.
"""

from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st

from papermint.config import MAX_FILE_SIZE_MB
from papermint.pipeline import accepted_extensions, accepted_formats


def read_upload(uploaded_file: Any) -> bytes:
    """Return the complete bytes of an uploaded file.

    Args:
        uploaded_file: A Streamlit ``UploadedFile``, or any object exposing
            ``getvalue`` or ``read``.

    Returns:
        The file's bytes, independent of the stream position.
    """
    if uploaded_file is None:
        return b""
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()
    return uploaded_file.read()


def upload_signature(uploaded_file: Any, *extra: object) -> str:
    """Build a stable cache key for an uploaded file.

    The digest lets a page reuse the previous pipeline result across reruns,
    so interacting with a filter does not reprocess the document.

    Args:
        uploaded_file: The uploaded file.
        *extra: Additional values that should invalidate the cache when they
            change, such as the force-parse toggle.

    Returns:
        A hexadecimal digest identifying this file and option set.
    """
    digest = hashlib.sha256()
    digest.update(read_upload(uploaded_file))
    digest.update(str(getattr(uploaded_file, "name", "")).encode("utf-8"))
    for value in extra:
        digest.update(repr(value).encode("utf-8"))
    return digest.hexdigest()


def render_file_uploader(key: str = "file_upload", accept_multiple: bool = False) -> Any:
    """Render a file uploader with supported format information.

    Args:
        key: Unique Streamlit widget key.
        accept_multiple: Whether to allow multiple file uploads.

    Returns:
        The uploaded file object, a list of uploaded file objects, or None.
    """
    label = "Choose files" if accept_multiple else "Choose a file"
    formats = " · ".join(accepted_formats())

    uploaded = st.file_uploader(
        label=label,
        type=accepted_extensions(),
        accept_multiple_files=accept_multiple,
        help=(f"Accepted formats: {formats}. Maximum size {MAX_FILE_SIZE_MB} MB per file."),
        key=key,
        label_visibility="collapsed",
    )
    st.caption(f"{formats} · up to {MAX_FILE_SIZE_MB} MB per file")
    return uploaded


__all__ = ["read_upload", "render_file_uploader", "upload_signature"]
