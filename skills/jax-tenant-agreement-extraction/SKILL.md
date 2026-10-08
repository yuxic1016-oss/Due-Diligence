---
name: "jax-tenant-agreement-extraction"
description: "Use when the user wants to extract tenant/customer agreement terms (MSAs, Sales Orders, leases, amendments, renewal notices) from a folder of PDFs into a \"Customer Agreements Summary\" style workbook, or update/rebuild that workbook for a data-center or similar facility. Trigger on requests to pull customer contract data into a spreadsheet, build or refresh a tenant agreement tracker, process a folder of customer/tenant PDFs into structured rows, or extend an existing Customer Agreements Summary with new customers or a new as-of date. Applies even if the user doesn't name this skill directly — e.g. \"extract these customer folders into the summary sheet\" or \"add these new tenants to the agreements workbook.\""
---

## Overview

Turns a folder of customer/tenant agreement PDFs (MSAs, Sales Orders, leases,
amendments, renewal letters) into rows in a Customer Agreements Summary
workbook, with a single "As-of Date" cell that automatically recalculates each
customer's current recurring charge — including compounding escalations —
without anyone re-deriving "what's active right now" by hand every time the
sheet is reopened.

This captures a workflow validated end-to-end across 120+ real customer
folders for a Jacksonville data-center facility, refined through the account
owner's own review pass.

Note: this skill's full bundled resources (a Python assembly script and a
detailed conventions reference) are distributed as a `.skill` package. If you
only have this text and not the bundled `scripts/build_workbook.py` /
`references/conventions.md` files, ask the user for the `.skill` file (or
rebuild the script/reference content described below) before doing large-scale
extraction — the formulas and row-writing logic below are intricate enough
that hand-writing them from scratch each time invites mistakes.

## When to Use

Use this whenever the deliverable is a spreadsheet of customer/tenant
agreement terms built from a folder of source contract PDFs, whether that's:
- A brand-new pilot on a handful of customer folders
- Scaling up to dozens/hundreds of folders
- Adding new customers to an existing workbook
- Rebuilding a customer whose folder was updated (new amendment, renewal, etc.)
- Rolling the As-of Date forward on an existing workbook (no re-extraction
  needed — just update the As-of Date cell on each sheet; the formulas do the rest)

Don't use this for one-off single-document questions ("what does this lease
say about parking") — that's just reading a PDF. This skill is for building or
maintaining the structured, formula-driven summary workbook.

## The standing extraction rule

Every field in the workbook must trace back to something found in that
customer's own folder. Never carry forward numbers from a prior/master
version of the sheet on the assumption they're already correct — always
re-derive from the customer's own source documents. If a folder has no usable
documents, still create the customer's row with zero data rows and a note
explaining why — never silently omit the customer. If a document is
ambiguous, contradictory, illegible, or you're not fully confident in a value,
write your best-effort value AND flag the uncertainty in that row's notes —
never guess silently.

## Data model (four row kinds)

| kind | use for | begin/end behavior |
|---|---|---|
| `msa` | Governing agreement text, renewal/holdover/payment terms, escalation-rate anchor | No dates in Beginning/Ending/Total MRC columns — text only |
| `so_fixed` | A commitment with a confirmed, bounded end date and no confirmed renewal | Static begin+end; naturally drops out of Current Total once As-of Date passes the end date |
| `so_recurring` | Auto-renewing / open-ended commitment (the common case for active colo customers) | Static first period, then generated EDATE period-rows compounding at the escalation rate, extending past the As-of Date |
| `open` | No term at all — a standing base fee or always-on item | No dates; always counted |

Escalation rate is a decimal fraction (e.g. `0.03` for 3%) written once on the
customer's first `msa` row; every `so_recurring` row's generated period
formulas reference that one cell absolutely, so editing it updates every
projected period for that customer. Don't default everything to
`so_recurring` — use `so_fixed` whenever the source document actually states a
fixed end with no automatic renewal language.

Real-estate lease tenants (e.g. a tenant leasing whole suites, not just colo
cabinets) get read as a commercial lease: do NOT blend multiple suites into a
single combined rent figure — each suite gets its own row/row-group with its
own rent history. Skip floor plan and CAM reconciliation documents; they don't
contain rent commitment terms.

## The As-of Date / Current Total mechanism

A single "As-of Date" cell drives every customer's "Current Total" via a
SUMPRODUCT array formula that includes a period row when its Beginning Date is
blank or ≤ the As-of Date, AND its Ending Date is blank or ≥ the As-of Date,
AND its Total MRC is numeric — summing matches, returning "N/A" if none match.
Changing the As-of Date alone re-derives "what's currently active." Never
hand-write a static `=N<row>` reference to "the current row" — it goes stale
the moment the As-of Date changes or a new period is appended. The customer
header row's total column should be a simple pointer formula back to that
customer's Current Total row, so anything referencing it stays in sync.

## Formula-injection safety

Any string written to a cell that starts with `=`, `+`, `-`, or `@` gets
interpreted as a formula by Excel/openpyxl, silently corrupting the cell.
Guard every text write (customer names, descriptions, notes) by prepending a
space if the text starts with one of those characters — never write raw
extracted text straight into a cell without this check.

## Extraction mechanics

- Use `pdftotext -layout` first; it handles the large majority of documents.
- If output is empty/garbled (common with DocuSign merge-field encoded PDFs or
  scanned documents), fall back to OCR: `pdftoppm -r 200 -png` then
  `tesseract` on each page image. Ghostscript can help re-render a corrupted
  page as a last resort.
- For large folders (dozens to hundreds of customers), dispatch parallel
  subagents rather than working serially. Balance batches by file count, not
  customer count — some customers have 1 PDF, others have 15. Give each
  subagent a fully self-contained prompt: the schema above, the standing
  extraction rule, and an explicit instruction to write its output JSON to an
  exact file path (so results survive even if the subagent's final chat
  summary is imperfect or the run gets interrupted).
- After a batch returns, independently spot-check anything a subagent flagged
  as surprising (e.g. a filename that doesn't match its contents) before
  treating it as fact.

## Workflow

1. **Confirm scope**: which folder(s), new sheet vs. addition to an existing
   workbook, and what As-of Date to use (default: today). If the user has an
   existing workbook in this format, treat it as the authoritative style/
   convention source — it wins over any default assumption here.
2. **Extract** each customer folder into a JSON object per the schema above
   (inline for small batches, parallel subagents for large ones). Save every
   batch's JSON to disk before moving on.
3. **Assemble**: combine extracted customers into one JSON file and run the
   bundled `scripts/build_workbook.py` (see its module docstring for the exact
   schema and CLI flags) to produce the workbook — it implements the style
   copying, banner/header rows, per-customer blocks, EDATE escalation
   formulas, and SUMPRODUCT Current Total formulas described above so you
   don't have to hand-write them.
4. **Verify**: run the LibreOffice-based `recalc.py` (bundled with the `xlsx`
   skill) against the output and confirm zero formula errors. Spot-check that
   an expired `so_fixed` row reads "N/A" in Current Total and that a
   `so_recurring` customer's total reflects the escalated period that actually
   contains the As-of Date.
5. **Deliver**: copy the finished workbook to the user's selected folder and
   present it.

## Common Mistakes

- Trusting a prior/master sheet's numbers instead of the source folder —
  always re-derive from that customer's own documents.
- Blending multiple suites/spaces of a real-estate lease tenant into one row
  — keep each suite's rent as its own line.
- Hand-writing a static "current" total reference instead of the SUMPRODUCT
  date-window formula — it'll go stale.
- Skipping the `recalc.py` verification step and treating a clean openpyxl
  save as proof the formulas are valid.
