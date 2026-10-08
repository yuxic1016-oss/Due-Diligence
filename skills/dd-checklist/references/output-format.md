# Output format

The deliverable is the user's own checklist workbook, saved under a new name, with two columns added. This spec is not negotiable — it is the format the user converged on after editing an earlier version by hand.

## Workbook structure

| Tab | Contents |
|---|---|
| **Checklist** | The working tab. Original columns A–E untouched, plus F STATUS and G NOTE. Nothing else. |
| **Detail** | Per-row backing: matching document names, VDR folder path, notes from opening the document. |
| **Status Summary** | Counts by status, and the list of disputed items with checklist line numbers — a ready-made re-open list for the seller. |
| **Tracker vs Data Room** | Only when a seller tracker exists. One row per tracker item: item #, request, seller's status, your verdict, what you actually see. |

Put the working tab first. The user reads and forwards that one.

## Checklist tab formatting

- Header row is wherever the original checklist's header sits (often row 12, under a title block). Put `STATUS` and `NOTE` there — bold, centred, wrapped, medium border, matching the existing headers.
- Body cells in F and G: **Times New Roman 11, regular weight, black, horizontal centre, vertical centre, wrap on.**
- **No fill. No colour coding. No conditional formatting.** Match the neighbouring columns exactly.
- Turn gridlines off: `ws.sheet_view.showGridLines = False`.
- Column widths: F ≈ 17, G ≈ 32.
- Leave every non-Received, non-Partial row **blank** in both F and G.
- Do not add an autofilter or freeze panes to this tab unless the original had them.

## Note style

Short, plain, forwardable. No leading label, no bullet, no formatting.

Good:

- `Waiting on benefits`
- `No PCA found`
- `ESA received`
- `Most recent report is 12/31/2025. Missing 2026`

When recording the seller's own answer, quote it and attribute it:

- `From seller: Please refer to the financial model`
- `From seller: Cash basis is not available; The greatest detail is the KMPG QoE`

Bad: anything that reads like analysis rather than a status line. Long reasoning belongs on the Detail tab.

## Naming

`<Project> - DD Checklist Status <data room date>.xlsx`

Never overwrite the source checklist. If the user has hand-edited a prior version, read their edits first and carry them forward — their status and note wording wins over yours.
