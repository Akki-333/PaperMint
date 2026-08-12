"""Component for handling file uploads."""

from typing import Any

import streamlit as st

from papermint.config import ACCEPTED_FILE_TYPES, MAX_FILE_SIZE_MB


def render_file_uploader(key: str = "file_upload", accept_multiple: bool = False) -> Any:
    """Render a file uploader with supported format info.

    Args:
        key (str): Unique Streamlit widget key.
        accept_multiple (bool): Whether to allow multiple file uploads.

    Returns:
        Any: The uploaded file object, a list of uploaded file objects, or None.
    """
    # Format badges
    formats = ["PDF", "PNG", "JPG", "DOCX", "PPTX"]
    format_str = " · ".join(formats)
    st.caption(f"Supported formats: {format_str}")

    uploaded_files = st.file_uploader(
        label="Choose a file",
        type=ACCEPTED_FILE_TYPES,
        accept_multiple_files=accept_multiple,
        help=f"Upload academic documents to extract their bibliography. Max size: {MAX_FILE_SIZE_MB}MB.",
        key=key,
        label_visibility="collapsed"
    )

    return uploaded_files
