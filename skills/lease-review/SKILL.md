---
name: lease-review
description: Answer a question about what a set of leases says — CAM and expense recovery, chilled water or utility charges, termination and renewal rights, assignment, insurance, holdover, any provision — by reading the documents and citing document, section and page for every answer, with page-image snips as backup. Use whenever someone points at a folder, zip or data room of leases, amendments, sales orders, MSAs or estoppels and asks what they say, whether a tenant pays or owes something, how a provision differs across tenants, or wants proof of a lease term. Trigger on "check these leases for X", "do they charge CAM", "what does the lease say about termination", "pull the language on renewal options", "give me a snip of where it says that", "which tenants have Y", or any request pairing tenant documents with a question about their terms — even when nobody says "lease review". Also use it when a lease answer supports budget, underwriting, abstract, diligence or audit work.
---

# Lease Review

Answering a lease question well is mostly about not being fooled. The provision you are asked about is rarely in one place: it lives in a base lease written decades ago, narrowed by a first amendment, superseded by a third, and carved out for one suite by a fourth. Grep will find a keyword. It will not tell you which document controls, that a clause applies to only half the tenant's space, or that the base lease answer was replaced in 2025.

So the work is: inventory everything, make every page searchable, reconstruct the amendment chain, read whole clauses rather than keyword hits, and cite precisely enough that someone can check you.

## Workflow

### 1. Inventory before reading

List the folder recursively and build a table: tenant (usually the subfolder), document name, page count, file size. Group by tenant.

This takes a minute and tells you the shape of the job — how many documents, which tenants have long base leases versus a stack of short amendments, and whether anything is suspiciously small (a one-page signature fragment) or large (a 50-page packet that turns out to contain several documents concatenated).

### 2. Determine which documents are text and which are scans

Run `pdftotext -layout` over everything and compare output size to page count. A born-digital PDF yields roughly 1,500–3,000 bytes per page. A scan yields near zero — often just a Docusign envelope header.

In a typical tenant folder the recent amendments are digital and the base leases from the 1990s and 2000s are scans. Expect to OCR the majority of pages, and expect the base leases — where the operative definitions live — to be the ones that need it.

### 3. OCR the scans

Use `scripts/ocr_pdfs.sh`. It renders each page at 200 dpi grayscale and runs tesseract, writing one text file per PDF with `=== PAGE nn ===` markers so you can map a hit back to a page.

```bash
scripts/ocr_pdfs.sh <source-dir> <output-dir>          # single worker
scripts/ocr_pdfs.sh <source-dir> <output-dir> 2        # two workers, roughly halves wall time
```

Budget about 8–10 seconds per page. A 300-page folder is 20–40 minutes. Start it early and read the digital documents while it runs — that overlap is most of the time saving available.

Read `references/ocr-notes.md` before improvising your own OCR loop. It documents the failure modes that cost real time: filenames with spaces silently producing empty output, background jobs being killed when a remote shell returns, and `pkill -f` matching your own shell.

OCR of a 1998 fax-quality scan will be imperfect. Section numbers, dollar figures and percentages are where errors hurt most — treat any figure you intend to report as provisional until you have looked at the rendered page (step 7).

### 4. Reconstruct the amendment chain

Before searching for the provision, work out what documents exist for each tenant and in what order. The recitals of every amendment enumerate the ones before it: "WHEREAS, Landlord and Tenant entered into that certain Third Amendment dated March 30, 2023…"

Build a chain per tenant: base lease → first amendment → second → and so on, with date, subject, and whether you actually have the document.

This does two things at once. It tells you **which document controls** — generally the most recent amendment that addresses your provision, since amendments routinely include a clause saying they prevail over the lease in the event of conflict. And it surfaces **what might be missing**, because a recital naming a Second Amendment you do not have is proof it exists.

**Before calling anything missing, search the other PDFs for it.** File names in a data room describe the first document in the file, not everything in it. A PDF called "Lease" is very often a compendium: the lease, then its amendments, then a renewal notice, sometimes an estoppel — all scanned together, with nothing in the name to say so. In one folder of 23 documents, four of the five amendments believed missing were sitting inside other PDFs, and one of them resolved the central question of the review.

The check is quick once every page is extracted. Search all the text for document headings and report which file and page each lands on:

```bash
grep -n "AMENDMENT\|NOTICE TO RENEW\|ESTOPPEL\|GUARANTY" <textdir>/*.txt
```

Then map each hit back to its page marker. A heading appearing deep inside a long file — page 21 of a file whose first document ran 17 pages — is a separate document bound into the same PDF.

This also means page counts are a signal worth reading at inventory time. A base lease is rarely 50 pages; if one is, something else is probably in there.

Genuinely missing documents are a finding, not a gap to paper over. Report them by name and date, and say what you would expect them to affect. But a document reported missing that was in the folder all along undermines the whole review, so do this check before you write that sentence.

### 5. Search broadly, then read whole clauses

Search across the extracted text for the provision family — several terms, not one. For CAM: operating expense, common area, additional rent, prorata, proportionate share, base year, real estate taxes, utilities. For termination: terminate, right to return, surrender, notice, default, cure. For renewal: option, extension term, renewal term, holdover.

Then open the section around each hit and read it in full, including:

- **The defined terms it depends on.** "Tenant shall pay its Proportionate Share of Operating Expenses" means nothing until you read both definitions.
- **The exceptions.** Almost every substantive clause has a carve-out, an exclusion list, or a "notwithstanding the foregoing." These are frequently where the answer actually is. An inclusion list and its exclusion list can contradict each other — when they do, say so rather than picking one.
- **Which premises it covers.** Amendments regularly apply a provision to expansion space "only and not the Initial Premises," or add a suite with its own share. A tenant can be half gross and half net.
- **Exhibits.** Rates, schedules and rent tables usually live in exhibits at the back, and the body of the document just points at them.

### 6. Treat the absence of a provision as a real finding

If a lease has no CAM article, or the summary table says "NA," or a numbered section has been left blank, that is an answer and it needs a citation like any other. Cite the page showing the "NA," or the section number that turns out to be about something else. "This lease has no Operating Costs Adjustment article — Paragraph 6 is 'Services'" is a stronger, more checkable finding than silence.

### 7. Produce snips as backup — and look at each one

For every provision cited, render the page as a PNG:

```bash
pdftoppm -r 150 -png -f <page> -l <page> "<file.pdf>" <outdir>/<name>
```

Name each file so it is self-describing: `05_Windstream_3rdAmd_p2_additional-rent.png`. Whoever opens the folder in six months should not need the conversation to know what they are looking at.

**Open every snip and read it before delivering.** This is not optional and it is not slow. Page numbers derived from OCR pagination can drift from true PDF pages, and a confident citation pointing at the wrong page is worse than no citation. Viewing the rendered page also catches OCR errors in exactly the figures that matter — during one review the OCR read a pro rata share as 4.19% where the page plainly showed 4.1%.

Anything you could not read from OCR — handwriting, a figure obscured by a confidentiality watermark, a blurred stamp — read off the rendered page instead. That is often the only way to recover it.

### 8. Report

Structure the answer around the question, not around the documents. For a cross-tenant question, lead with a comparison table so differences are visible at a glance, then give a paragraph per tenant with the details and citations.

Cite as: **document name → section or paragraph → PDF page**. Use the document's own numbering (§6(a)(4), ¶2(c)) and the PDF page number, since that is what someone opening the file will navigate by. Where the wording carries weight, quote it rather than paraphrasing — "for the Additional Premises only and not the Initial Premises" cannot be summarized without losing the point.

Close with what would change the answer: missing documents, internal contradictions, figures you could not read cleanly, and anywhere the documents support a narrower conclusion than the question assumed.

## What tends to go wrong

**Taking the base lease as the answer.** The base lease is the starting point. A 2025 amendment resetting the base year or fixing a monthly amount is what governs today.

**Assuming one tenant means one treatment.** Check every suite. Splits between original and expansion premises are common and easy to miss because they turn on a single phrase.

**Reading the inclusion list and stopping.** The exclusions, caps and provisos are usually where the commercially significant terms sit — a management fee cap, a gross-up floor, a carve-out limiting a service to common areas.

**Reporting a number the OCR produced.** Verify figures against the rendered page.

**Trusting file names.** A file called "Lease" frequently contains the lease plus several amendments. Search inside before concluding a document is absent, and before assuming a long PDF is one document.

**Silently dropping a document you could not read.** If a scan will not OCR usefully, say which one and what you could not determine from it.

## Reference files

- `references/ocr-notes.md` — OCR failure modes and the reasoning behind the bundled script. Read before writing your own extraction loop.
- `references/provision-map.md` — where common provisions tend to live in a lease, and the search terms that find them. Useful when starting on an unfamiliar provision.
