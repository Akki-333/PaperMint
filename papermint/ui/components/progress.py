"""Component for displaying processing progress."""

import streamlit as st

def render_processing_steps(current_step: int, total_steps: int = 4) -> None:
    """Show processing pipeline step indicators.
    
    Args:
        current_step (int): The current active step (1-based index).
        total_steps (int): Total number of steps in the pipeline.
    """
    st.markdown("### Processing Pipeline")
    
    steps = [
        "Extracting Text",
        "Detecting Bibliography",
        "Parsing Citations",
        "Done!"
    ]
    
    progress_val = min(1.0, max(0.0, current_step / total_steps))
    st.progress(progress_val)
    
    cols = st.columns(total_steps)
    for i, col in enumerate(cols):
        step_num = i + 1
        with col:
            if step_num < current_step:
                # Completed
                st.markdown(f"✅ <span style='color: #94A3B8; text-decoration: line-through;'>{steps[i]}</span>", unsafe_allow_html=True)
            elif step_num == current_step:
                # In progress
                st.markdown(f"🔄 **{steps[i]}**", unsafe_allow_html=True)
            else:
                # Pending
                st.markdown(f"⏳ <span style='color: #475569;'>{steps[i]}</span>", unsafe_allow_html=True)
