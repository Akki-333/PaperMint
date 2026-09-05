"""The processing flow: what the pipeline is doing, while it does it.

The indicator reports which stage is running as a chain of nodes joined by a
rail that fills as the run advances. It writes into a single placeholder and
replaces that placeholder's contents in place, so a run leaves one widget
behind rather than one per stage.

It is driven by :class:`papermint.pipeline.PipelineStage`, which means the
displayed steps can never drift out of step with the stages the service
actually runs, and each step's explanatory line comes from that stage's own
``detail`` property rather than from a copy kept here.

**Why the motion is built the way it is.** Streamlit replaces the whole DOM
node on every placeholder write, so a CSS *transition* on the rail would never
play: the new node would simply start at its new width. The rail therefore
carries a keyframe animation running from the previous stage's position to the
current one, and the stepper remembers where it had reached. Everything else is
either a continuous loop, which does not care about being remounted, or a
one-shot entrance.
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

#: The icon shown inside each stage's node.
_STAGE_ICON: dict[PipelineStage, str] = {
    PipelineStage.EXTRACT: "document",
    PipelineStage.CHARACTERIZE: "search",
    PipelineStage.PARSE: "library",
    PipelineStage.SUMMARIZE: "quote",
}


def _progress(stage: PipelineStage) -> float:
    """Return how far along the rail a stage sits, as a percentage.

    A running stage fills the rail to the centre of its own node rather than
    past it, so the leading edge and the pulsing node agree about where the
    work has reached.

    Args:
        stage: The stage now running, or ``DONE``.

    Returns:
        A percentage between 0 and 100.
    """
    if stage is PipelineStage.DONE:
        return 100.0
    if stage not in _VISIBLE_STAGES:
        return 0.0
    position = _VISIBLE_STAGES.index(stage)
    return (position + 0.5) / len(_VISIBLE_STAGES) * 100.0


def _state(
    stage: PipelineStage,
    current: PipelineStage,
    *,
    failed_stage: PipelineStage | None = None,
) -> str:
    """Classify one step against the stage now running or failed.

    Args:
        stage: The step being drawn.
        current: The stage now running, or ``DONE``.
        failed_stage: The stage that encountered an error, if any.

    Returns:
        The CSS state class for that step.
    """
    if failed_stage is not None:
        if stage.order < failed_stage.order:
            return "is-done"
        if stage == failed_stage:
            return "is-failed"
        return "is-waiting"

    if current is PipelineStage.DONE or stage.order < current.order:
        return "is-done"
    if stage is current:
        return "is-active"
    return "is-waiting"


def _flow_markup(
    current: PipelineStage,
    *,
    previous: float = 0.0,
    animated: bool = True,
    failed_stage: PipelineStage | None = None,
    failure_message: str = "",
) -> str:
    """Build the markup for the flow at a given stage.

    Args:
        current: The stage now running, or ``DONE``.
        previous: Where the rail had already reached, as a percentage, so the
            fill animates forward from there rather than from zero.
        animated: Run the entrance and rail animations and show the live status
            line. Set False for the motionless record of a finished run.
        failed_stage: The stage that encountered an error, if any.
        failure_message: Optional specific error message to surface.

    Returns:
        The flow's HTML.
    """
    target = _progress(failed_stage) if failed_stage is not None else _progress(current)
    steps: list[str] = []
    for position, stage in enumerate(_VISIBLE_STAGES):
        state = _state(stage, current, failed_stage=failed_stage)
        if state == "is-failed":
            glyph = icon("x", size=14, stroke=2.2)
        elif state == "is-done":
            glyph = icon("check", size=14, stroke=2.0)
        else:
            glyph = icon(_STAGE_ICON[stage], size=14)

        steps.append(
            f'<li class="pm-flow-step {state}" style="--pm-step:{position};">'
            f'<span class="pm-flow-node">{glyph}</span>'
            f'<span class="pm-flow-name">{esc(stage.label)}</span>'
            "</li>"
        )

    status = ""
    if failed_stage is not None:
        msg = (
            failure_message or f"Processing interrupted at the {failed_stage.label.lower()} stage."
        )
        status = (
            '<div class="pm-flow-status">'
            '<span class="pm-flow-beacon is-failed"></span>'
            f'<span class="pm-flow-said"><b>Failed at {esc(failed_stage.label)}:</b> {esc(msg)}</span>'
            "</div>"
        )
    elif animated and current is not PipelineStage.DONE:
        status = (
            '<div class="pm-flow-status">'
            '<span class="pm-flow-beacon"></span>'
            f'<span class="pm-flow-said"><b>{esc(current.label)}</b> {esc(current.detail)}</span>'
            "</div>"
        )

    if failed_stage is not None:
        classes = "pm-flow is-failed"
    elif animated:
        classes = "pm-flow is-live"
    else:
        classes = "pm-flow"

    return (
        f'<div class="{classes}" style="--pm-from:{previous:.1f}%;--pm-to:{target:.1f}%;">'
        '<div class="pm-flow-rail"><div class="pm-flow-fill"></div></div>'
        f'<ol class="pm-flow-steps">{"".join(steps)}</ol>'
        f"{status}"
        "</div>"
    )


@dataclass(slots=True)
class PipelineStepper:
    """A live stage indicator bound to one placeholder in the page.

    Pass :meth:`update` as the pipeline's ``on_progress`` callback and the
    indicator advances as the run proceeds.

    Attributes:
        slot: The placeholder the flow draws into.
        reached: How far along the rail the last redraw left the fill, so the
            next one animates on from there instead of restarting at zero.
        current_stage: The stage that is currently running or was last reported.
    """

    slot: Any = field(default_factory=st.empty)
    reached: float = 0.0
    current_stage: PipelineStage = PipelineStage.EXTRACT

    def update(self, stage: PipelineStage) -> None:
        """Redraw the flow for the given stage.

        Args:
            stage: The stage that has just started, or ``DONE``.
        """
        self.current_stage = stage
        is_done = stage is PipelineStage.DONE
        self.slot.html(compact(_flow_markup(stage, previous=self.reached, animated=(not is_done))))
        self.reached = _progress(stage)

    def fail(self, stage: PipelineStage | None = None, message: str = "") -> None:
        """Mark the flow as failed at the given or current stage with an X mark.

        Args:
            stage: The stage that failed. If None, uses ``current_stage``.
            message: The human-readable reason or error message.
        """
        failed = stage or self.current_stage
        self.slot.html(
            compact(
                _flow_markup(
                    failed,
                    previous=self.reached,
                    animated=False,
                    failed_stage=failed,
                    failure_message=message,
                )
            )
        )
        self.reached = _progress(failed)

    def finish(self) -> None:
        """Settle the flow in its completed state."""
        self.update(PipelineStage.DONE)

    def clear(self) -> None:
        """Remove the flow from the page."""
        self.slot.empty()


def render_stepper(
    current: PipelineStage = PipelineStage.DONE,
    *,
    animated: bool = False,
    failed_stage: PipelineStage | None = None,
    failure_message: str = "",
) -> None:
    """Render a one-shot flow at a fixed stage.

    Args:
        current: The stage to display as active, or ``DONE``.
        animated: Whether to play the entrance animation.
        failed_stage: Optional stage that encountered an error.
        failure_message: Optional error message.
    """
    prev = 100.0 if current is PipelineStage.DONE else _progress(current)
    st.html(
        compact(
            _flow_markup(
                current,
                previous=prev,
                animated=animated,
                failed_stage=failed_stage,
                failure_message=failure_message,
            )
        )
    )


__all__ = ["PipelineStepper", "render_stepper"]
