"""The processing stepper.

The stepper reports which pipeline stage is running. It writes into a single
placeholder and updates that placeholder in place, so a run leaves one widget
behind rather than one per stage.

It is driven by :class:`papermint.pipeline.PipelineStage`, which means the
displayed steps can never drift out of step with the stages the service
actually runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from papermint.pipeline import PipelineStage
from papermint.ui.html import compact, esc
from papermint.ui.icons import icon

#: The stages shown to the reader, in order. ``DONE`` is a terminal marker
#: rather than a step, so it is excluded.
_VISIBLE_STAGES: tuple[PipelineStage, ...] = (
    PipelineStage.EXTRACT,
    PipelineStage.CHARACTERIZE,
    PipelineStage.PARSE,
    PipelineStage.SUMMARIZE,
)

#: The icon shown beside each stage.
_STAGE_ICON: dict[PipelineStage, str] = {
    PipelineStage.EXTRACT: "document",
    PipelineStage.CHARACTERIZE: "search",
    PipelineStage.PARSE: "library",
    PipelineStage.SUMMARIZE: "quote",
}


def _stepper_markup(current: PipelineStage) -> str:
    """Build the markup for the stepper at a given stage.

    Args:
        current: The stage now running, or ``DONE``.

    Returns:
        The stepper's HTML.
    """
    pills: list[str] = []
    for position, stage in enumerate(_VISIBLE_STAGES):
        if current is PipelineStage.DONE or stage.order < current.order:
            state, glyph = "is-done", icon("check", size=13)
        elif stage is current:
            state, glyph = "is-active", icon(_STAGE_ICON[stage], size=13)
        else:
            state, glyph = "", icon(_STAGE_ICON[stage], size=13)

        pills.append(f'<span class="pm-step {state}">{glyph}{esc(stage.label)}</span>')
        if position < len(_VISIBLE_STAGES) - 1:
            pills.append('<span class="pm-step-rule"></span>')

    return f'<div class="pm-steps">{"".join(pills)}</div>'


@dataclass(slots=True)
class PipelineStepper:
    """A live stage indicator bound to one placeholder in the page.

    Pass :meth:`update` as the pipeline's ``on_progress`` callback and the
    indicator advances as the run proceeds.

    Attributes:
        slot: The placeholder the stepper draws into.
    """

    slot: Any = field(default_factory=st.empty)

    def update(self, stage: PipelineStage) -> None:
        """Redraw the stepper for the given stage.

        Args:
            stage: The stage that has just started.
        """
        self.slot.html(compact(_stepper_markup(stage)))

    def clear(self) -> None:
        """Remove the stepper from the page once a run has finished."""
        self.slot.empty()


def render_stepper(current: PipelineStage) -> None:
    """Render a one-shot stepper at a fixed stage.

    Args:
        current: The stage to display as active.
    """
    st.html(compact(_stepper_markup(current)))


__all__ = ["PipelineStepper", "render_stepper"]
