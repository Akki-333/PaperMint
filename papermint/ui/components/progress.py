"""Component for displaying processing progress."""

import streamlit as st


def render_processing_steps(current_step: int, total_steps: int = 4) -> None:
    """Show processing pipeline step indicators.

    Args:
        current_step (int): The current active step (1-based index).
        total_steps (int): Total number of steps in the pipeline.
    """
    st.markdown('<div class="pipeline-header">⚡ Processing Pipeline</div>', unsafe_allow_html=True)

    steps = [
        ("📄", "Extracting Text"),
        ("🔍", "Detecting Bibliography"),
        ("🧠", "Parsing Citations"),
        ("✅", "Done!"),
    ]

    progress_val = min(1.0, max(0.0, current_step / total_steps))
    st.progress(progress_val)

    cols = st.columns(total_steps)
    for i, col in enumerate(cols):
        step_num = i + 1
        icon, label = steps[i]
        with col:
            if step_num < current_step:
                st.markdown(f"✅ ~~{label}~~")
            elif step_num == current_step:
                st.markdown(f"{icon} **{label}**")
            else:
                st.caption(f"⏳ {label}")
