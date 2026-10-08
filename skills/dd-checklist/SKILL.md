---
name: dd-checklist
description: Reconcile an acquisition due-diligence checklist against a data room, and against the seller's diligence/Q&A tracker, then write the answer back into the checklist workbook as a STATUS and NOTE column. Use whenever the user asks to check a DD checklist against a data room, find which requested documents have been received, mark up a diligence checklist, compare a seller tracker or Q&A log to what was actually posted, chase outstanding diligence items, or build a re-open list for the seller. Trigger on phrases like "check the data room against the checklist", "what's still outstanding", "did we get X", "compare the tracker status", "mark up the DD list", or any request that pairs a checklist workbook with a folder or zip of deal documents — even if the user does not say the words "due diligence".
---

# DD checklist vs. data room

Turn a due-diligence checklist into a live status tracker by matching every line to what is actually in the data room, then cross-checking the seller's own tracker.

The deliverable is the user's own checklist workbook with two columns filled in — **STATUS** and **NOTE** — plus supporting tabs. Do not invent a new layout.

## Inputs

Three inputs. **Confirm all of them with the user before touching their machine.**

1. **The checklist workbook** (.xlsx). Line items usually sit in one column with sub-items indented into the next column; section headers have no responsible party.
2. **The data room** — a folder or a `OneDrive_*.zip` export.
3. **The seller's diligence / Q&A tracker** (optional, .xlsx). Adds a second dimension: what the seller *claims* is closed.

## Workflow

### 0. Ask which folder — first, always

**Do not browse, list, or search the user's machine to work out which data room they mean.** Users keep many deals and many vintages of the same room side by side; picking one yourself is a coin flip, and doing it before asking reads as rummaging.

Ask with AskUserQuestion, in one round:

- which data room folder or zip
- which checklist workbook to mark up
- whether a seller tracker is in play

Offer concrete options only where this conversation already established them — a folder the user named, a file they attached, a room worked on earlier in the session. Otherwise offer "I'll name it" and wait.

Two exceptions, and only these:

- The user named the folder or attached the files in the request that triggered this skill.
- A prior turn in this same conversation already settled which room and checklist, and nothing suggests they have moved on.

When re-running against a room already worked on in this session, still ask whether to start from the original checklist or carry forward the user's hand-edited version — their edits and wording take precedence over anything regenerated.

### 1. Index the data room

Once the user has named it, run `scripts/index_dataroom.py` (works on a zip or an extracted folder) to get a flat path list. Read the folder tree before matching anything — VDR numbering (`5.3.1.7_Third-Party Reports`) is the map.

If the data room is a zip on the user's machine and they want clickable paths, extract it. See `references/environment.md` — background `unzip` gets killed, so extract in foreground chunks.

**Record empty folders.** A folder the seller created and left empty is a finding, not a miss.

### 2. Map every checklist line

Work down the checklist, row by row, and assign a status. Read `references/status-rules.md` for the decision rules and the four shapes "Partial" takes.

Capture per row: status, the document name(s), the VDR folder path, and what is missing.

### 3. Verify by opening documents — do not stop at filenames

Filename matching is a first pass, not an answer. Open the documents the judgement calls hang on. `references/verification.md` lists which ones repay opening, the extraction recipes, and the specific traps that have burned this workflow before (a "Key Vendor Summary" that contains no vendors, a Certificate of *Completion* passed off as a Certificate of *Occupancy*, a title policy six years stale).

Expect to move rows in **both** directions. Roughly a fifth of filename-based calls change once the file is open.

### 4. Reconcile the seller's tracker

If a tracker exists, check every item the seller marked Closed against what is actually posted. Read `references/tracker-reconciliation.md`. The recurring failure is a cited VDR reference that does not exist.

Also look for items the tracker still shows Open or Partial that have since been delivered — the tracker goes stale, and telling the user what they can close is as useful as telling them what to chase.

### 5. Write the workbook

Run `scripts/build_checklist.py` or follow the same spec by hand. The format is fixed — see `references/output-format.md`.

Summary of the house style:

- Sheet named **Checklist**. Columns A–E are the user's original checklist, untouched.
- **F = STATUS**, **G = NOTE**. Nothing else added to this tab.
- Only two status values: **Received** and **Partial**. Everything not yet in hand is left **blank** — a blank cell reads as an open item and fills in as documents arrive.
- **No colour fill, no conditional formatting.** Times New Roman 11, black, centred and wrapped. Gridlines off.
- Notes are short and plain — "Waiting on benefits", "No PCA found", "Most recent report is 12/31/2025. Missing 2026". When quoting the seller's tracker answer, prefix it: **"From seller: …"**.
- Detail — matching document names, VDR paths, verification findings, the tracker comparison — goes on separate tabs, never on the Checklist tab.

### 6. Report the gaps

In chat, lead with what blocks the deal, not with counts. Name the item, the checklist line, and why it matters. Flag separately:

- files the seller says exist but do not
- empty folders
- documents whose existence is *proven elsewhere* but which were never posted (see the SOC-report trick in `references/verification.md`)
- items the tracker can now close

## Reference files

| File | Read when |
|---|---|
| `references/status-rules.md` | Assigning statuses; deciding Partial vs Received |
| `references/output-format.md` | Writing the workbook; exact formatting spec |
| `references/verification.md` | Opening documents; extraction recipes; known traps |
| `references/tracker-reconciliation.md` | A seller tracker or Q&A log is in play |
| `references/environment.md` | Data room lives on the user's machine (device bridge, unzip, staging) |

## Scripts

| Script | Does |
|---|---|
| `scripts/index_dataroom.py` | Flat path index from a zip or folder; flags empty folders |
| `scripts/build_checklist.py` | Writes STATUS/NOTE into the checklist in house format, from a mapping file |

## Rules

- **Ask which folder before looking.** Never browse the user's machine to guess which data room or checklist they mean.
- **Never mark something Received on a filename alone** when the line item is material — power, title, permits, financials, insurance.
- **Say what is missing, not just that something is missing.** "Waiting on benefits" beats "incomplete".
- **Do not colour-code.** The user strips it.
- **Do not fill rows for items nobody has requested yet.** Blank is a valid, meaningful state.
- **Quote the seller verbatim** when recording their answer, so the note survives being forwarded.
- **Preserve the original workbook.** Write to a new file; never overwrite the user's checklist in place.
