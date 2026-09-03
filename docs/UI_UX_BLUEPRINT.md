# PaperMint — Design System

## 1. Philosophy

Three commitments, in priority order.

**Tell the truth about the data.** The interface's hardest job is not showing a
parsed citation, it is showing a *partly* parsed one without pretending
otherwise. Confidence is visible at three levels of detail, and an entry the
parser could not read shows its own raw text rather than the word "Untitled".

**Show the outcome before the mechanism.** Reference count, style and field
coverage come first. Detection reasoning, processing notes and raw text are one
interaction away.

**Never let the framework's defaults leak through.** Streamlit's own tabs,
buttons, inputs and dropzone are restyled from the same tokens as the custom
components, so nothing on a page looks bolted on.

---

## 2. Tokens

Every value lives in `papermint/ui/theme.py` and is emitted as a CSS custom
property by `css_variables()`. A hard-coded hex value anywhere else in
`papermint/ui/` is a defect.

### Colour

| Token | Value | Role |
|:---|:---|:---|
| `accent` | `#34D399` | Brand, primary action, high confidence |
| `accent-bright` | `#6EE7B7` | Hover |
| `accent-ink` | `#052E20` | Text on an accent fill |
| `canvas` | `#0F172A` | Page ground |
| `surface` | `#161F33` | Cards and panels |
| `surface-raised` | `#1D293D` | Hover, secondary buttons |
| `surface-sunken` | `#0B1120` | Inputs, source text, sidebar |
| `border` | `#27354C` | Default hairline |
| `border-strong` | `#3A4B66` | Emphasised edge |
| `text` | `#EEF2F8` | Primary |
| `text-muted` | `#9DACC2` | Secondary |
| `text-faint` | `#6B7C96` | Labels and captions |
| `caution` | `#FBBF24` | Partial confidence, review flag |
| `critical` | `#F87171` | Sparse confidence, errors |
| `info` | `#60A5FA` | Links, neutral notices |

`.streamlit/config.toml` carries the same four surface and text values so the
framework's own chrome sits on the same palette.

### Type

Two families, deliberately paired. **Inter** for interface chrome; **Source
Serif 4** for bibliographic content, which is what makes a citation card read as
scholarship rather than as a form field. **JetBrains Mono** for identifiers,
source text and card index numerals.

Scale, in rem against a 16px root: `micro` 0.6875 · `xs` 0.75 · `sm` 0.8125 ·
`base` 0.875 · `md` 1 · `lg` 1.125 · `xl` 1.375 · `2xl` 1.75 · `3xl` 2.25.

### Space, shape, motion

Spacing steps: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Radii: 6 for chips, 10 for
cards, 14 for panels, pill for badges. Two elevation levels only. Two durations:
120ms for state changes, 200ms for anything larger.

### What is deliberately absent

- **No gradient text.** Applying one to every heading flattens hierarchy. The
  earlier interface used the same mint gradient on the hero, the metric values
  and the wordmark, so none of them read as more important than the others.
- **No emoji as iconography.** Emoji render differently on every platform and
  cannot inherit text colour. `papermint/ui/icons.py` supplies a stroked SVG
  set drawn on `currentColor`.
- **No hover lift on static content.** Motion on a non-interactive card is
  decoration pretending to be an affordance.

---

## 3. The citation card

```
+-+----------------------------------------------------------------------+
| | 01                                  [APA]  [* Complete 100%]         |
| | Machine learning in citation parsing        <- serif, 18px           |
| | Smith, J. A. & Doe, R. B. - 2020            <- 14px, muted           |
| | Journal of Bibliometrics - vol. 15, no. 2, pp. 103-115 - Article     |
| | 10.1016/j.jbi.2020.01.002                   <- mono, link            |
+-+----------------------------------------------------------------------+
 ^ 2px rule, coloured by confidence band
```

A low-confidence card adds one more line:

```
  Not found: year, venue, DOI
```

### Confidence, at three levels of detail

| Level | Where | What it shows |
|:---|:---|:---|
| Glance | 2px rule on the card's left edge | Band colour only |
| Scan | Badge in the card header | Band label plus percentage |
| Inspect | Line beneath the metadata | Exactly which fields are missing |

Bands: **Complete** at 60% and above, **Partial** from 30%, **Sparse** below
that. An entry under 50% is additionally flagged for review, which drives the
"Needs review" filter and the export panel's warning count. Thresholds live in
`papermint/config.py`, not in the components.

### Rules

- **Never "Untitled".** `Citation.display_title` falls back to the entry's own
  opening text, rendered in italic sans to mark it as unparsed.
- **Escape everything.** Titles come from arbitrary uploaded documents. Every
  interpolated value passes through `esc()`; a title containing a raw angle
  bracket used to eat the rest of the card.
- **Interactive cards wrap real widgets.** An editable card is a keyed
  `st.container`, styled through its `st-key-` class, so the editor popover and
  the BibTeX view live inside the card's chrome rather than floating beneath it.

---

## 4. Code-block leaks: fixed structurally

The old guidance was "never indent HTML by four or more spaces inside a
multiline string", which forced components to be written as unreadable string
concatenation and still failed whenever someone forgot.

`st.html()` does not run the Markdown parser at all. `papermint/ui/html.py`
wraps it in `render()`, which also strips template indentation, so component
markup can be written and indented normally and the failure mode is gone rather
than merely avoided. A test asserts the emitted card markup contains no
four-space indentation.

---

## 5. Layout

**Page header.** Eyebrow with icon, serif title, one-sentence lede at 62
characters maximum.

**Statistics row.** Four tiles: label above in micro caps, value below in
tabular numerals, supporting note beneath. Auto-fitting grid from 170px.

**Stepper.** Four stages driven by `PipelineStage`, drawn into a single
placeholder and updated in place. The earlier version called its render function
once per stage, appending a fresh progress bar each time, so a finished run left
four stacked widgets on the page.

**Tabs.** References, Summary, Source text. Plain words, mint underline
indicator. Tabs collapse to two when a document has no bibliography.

**Notices.** A tone-tinted panel with an icon, headline, explanation and
optional bullets. Used wherever the interface must explain a decision, above all
the one where it declines to invent citations for a document that has none.

**Empty states.** Every view that can be empty has a designed placeholder saying
what would appear there, rather than a bare Streamlit info box.

---

## 6. Responsiveness and accessibility

- Content column caps at 1180px; prose caps at 68 characters.
- Below 640px the card gutter collapses and the badge row stacks.
- Icons carry `aria-hidden` and inherit `currentColor`.
- Focus rings are explicit on buttons, and the accent colour is never the only
  carrier of meaning, since every confidence band also has a text label.
- Wide content scrolls inside its own container; the page body never scrolls
  horizontally.
