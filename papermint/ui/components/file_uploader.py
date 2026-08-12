"""Component for handling file uploads."""

import streamlit as st
from typing import Any
from papermint.config import ACCEPTED_FILE_TYPES, MAX_FILE_SIZE_MB

def render_file_uploader(key: str = "file_upload", accept_multiple: bool = False) -> Any:
    """Render a file uploader with supported format info.
    
    Args:
        key (str): Unique Streamlit widget key.
        accept_multiple (bool): Whether to allow multiple file uploads.
        
    Returns:
        Any: The uploaded file object, a list of uploaded file objects, or None.
    """
    st.markdown(f"**Upload Document(s)** (Max file size: {MAX_FILE_SIZE_MB}MB)")
    st.caption("Supported formats: PDF, PNG, JPG, DOCX, PPTX")
    
    uploaded_files = st.file_uploader(
        label="Choose a file",
        type=ACCEPTED_FILE_TYPES,
        accept_multiple_files=accept_multiple,
        help="Upload an academic document to extract its bibliography.",
        key=key,
        label_visibility="collapsed"
    )
    
    # Optional size validation could go here
    
    return uploaded_files
