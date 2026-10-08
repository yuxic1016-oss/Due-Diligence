---
name: dd-customer-invoice-extract
description: Extract customer/tenant invoices from a folder of PDFs into a reconciled due-diligence workbook showing derived kW, total MRC, and every charging item broken out by category. Use whenever the user points at a folder, zip, or data-room path of colocation, data-center, wholesale, or telecom invoices and wants the numbers pulled into a spreadsheet — "extract the invoices", "pull kW and MRC from these invoices", "what's the monthly recurring revenue in this folder", "break out the charging items", "build me an invoice summary", "tie the invoices to the index". Applies to any provider's invoice format, not just one deal. Trigger even when the user does not say "due diligence", "kW", or "MRC" — a folder of invoices plus any request to summarize, total, tabulate, or reconcile them is enough.
---

# DD Customer Invoice Extract

Turns a folder of customer invoice PDFs into a reconciled workbook with three things a
diligence reader needs: **derived kW**, **total MRC**, and **every charging item with its
amount**, categorized.

The value of this skill is not the parsing — it is the discipline around it. Invoice PDFs
lie by omission, and the two numbers a buyer cares about most (kW and run-rate MRC) are
usually *not printed anywhere on the invoice*. They have to be derived, and a derivation
nobody can audit is worthless in a data room. So every number this skill produces either
ties to a printed subtotal or carries a visible assumption next to it.

## Workflow

### 1. Inventory the folder before parsing anything

List the folder recursively. Note the subfolder structure — in most data rooms subfolders
are the site, facility, or entity (e.g. `Jacksonville`, `JaxNAP`, `JXIX`), and that becomes
a Site column. Look for a spreadsheet sitting alongside the PDFs: sellers usually include an
index listing invoice number, customer, and amount. That index is the single best
reconciliation target available, so find it now rather than after building.

Stage everything into the working environment in one or two batches, then extract text.

### 2. Read one invoice end to end before writing any code

Open two or three PDFs from different subfolders and read the raw extracted text. You are
looking for:

- how the line-item table is delimited (a header row like `ID # Service Items ... Total Due`)
- whether a Discount column exists on some invoices but not others
- where the pre-tax **Service Items subtotal** and the **Invoice Total** are printed
- how descriptions wrap across lines
- whether text extraction inserts stray spaces (`P WR-120-30-P`, `1 20V`) — it usually does

Skipping this step is the single commonest way this task goes wrong. A regex written blind
will silently drop rows, and a dropped row looks exactly like a correct total.

### 3. Confirm the two conventions with the user

kW and MRC are judgment calls, not facts. Ask before building — the answers change every
number in the deliverable:

**kW basis** — how a billed circuit converts to kW:

| Option | 120V 30A A+B example |
|---|---|
| 80% derated, N (A only) — usual DD default for *usable/contracted* capacity | 2.88 kW |
| Nameplate, N (A only) | 3.60 kW |
| 80% derated, 2N (both feeds) — *installed breaker* capacity | 5.76 kW |
| Nameplate, 2N (both feeds) | 7.20 kW |

**MRC scope** — all service items pre-tax (ties cleanly to the PDF), recurring only
(excludes late fees, setup/install, NRC — better run-rate but requires judgment per line),
or invoice total including tax.

If the session is unattended, use *80% derated, N* and *all service items pre-tax*, and say
so plainly at the top of the response.

### 4. Parse, then prove the parse

Run `scripts/extract_invoices.py`. It walks the folder, extracts every line item, derives kW
per line, assigns a charge category, and writes a JSON intermediate.

```bash
python scripts/extract_invoices.py <invoice_folder> -o extracted.json \
    --derate 0.8 --redundancy 2N
```

The script's most important output is not the data — it is the **reconciliation report**:
for each invoice, the sum of extracted line items versus the Service Items subtotal printed
on the PDF. Do not proceed while any invoice mismatches. A mismatch means a row was dropped
or double-counted, and every downstream number inherits that error.

Common causes, in the order they usually bite:

- a Discount column present on some invoices shifts the money columns
- thousands separators in the quantity column (`1,000`) break a `\d+` quantity pattern
- a second page repeats the table header
- the description wraps and the continuation line looks like a new row

`references/parsing-recipes.md` has the working regex, the column-shift handling, and the
text-normalization fixes for stray-space artifacts.

### 5. Derive kW — and flag every place you guessed

kW derivation is where this skill earns its keep. Read `references/kw-derivation.md` before
touching the power lines. The short version:

`kW = Volts x Amps x Circuits x Derate x PhaseFactor x Redundancy / 1000`

The hard part is that amps and circuits hide in different places depending on how the
provider bills:

- **Per-circuit billing** — `PWR-120-30-P 120 VOLT 30 AMP ... A+B`, qty 4 → 4 circuits of 30A
- **Per-amp billing** — `208V POWER`, qty 6, unit $37.76 → 1 circuit of 6A
- The tell: when qty equals the amperage stated in the description, qty is amps, not circuits
- **Flat-rate cabinets** — `208V Power (A+B) CAB#1`, qty 1, unit $1,136.96, no amperage
  anywhere. Back into amps from the provider's own per-amp rate elsewhere in the same
  folder, and label the line as estimated.

Exclude plug-access, PDU rental, and hardware lines — they are not billed capacity.

Wholesale rent/CAM tenants frequently have **no derivable kW at all** because power reaches
them as an estimated electric charge inside the rent. Report those as zero kW with a note
rather than forcing a number; they are often the largest MRC lines in the folder, and a
reader who sees $0 kW next to $47k MRC needs to know why.

Every estimate, every conflict between a SKU code and its description text, and every
explicitly-stated kW goes in a Note column on the line and a bullet on the Assumptions tab.

### 6. Build the workbook

Run `scripts/build_workbook.py extracted.json -o "<Deal> Invoice Extract.xlsx"`.

Four tabs, in this order:

- **Summary** — one row per invoice: Site, Date, Customer, Invoice #, Derived kW, Total MRC,
  One-Time Charges, Service Items Subtotal, Tax, Invoice Total, then one column per charge
  category. Category columns sum across to the subtotal, which is a live self-check.
- **Line Items** — every line, with volts/amps/circuits/phase/redundancy exposed so the kW
  formula is visible and editable, plus a Note column.
- **Charge Categories** — rollup by category: count, amount, % of total, kW.
- **Assumptions & Notes** — kW method, derate in a single referenced cell, MRC scope,
  every estimate, and the reconciliation result.

Put the derate in one cell and reference it from every kW formula, so a reviewer who
disagrees with 80% can change one number and see the whole book reprice. Follow the user's
spreadsheet conventions if a `format` skill is present: gridlines off, black/white header,
blue for extracted values, black for same-sheet formulas, green for cross-sheet links.

### 7. Verify before delivering

Non-negotiable, and cheap:

1. Every invoice's line items sum to its printed Service Items subtotal.
2. Recalculate the workbook and confirm zero formula errors.
3. Read the calculated values back and check Summary rows against the parsed data.
4. Category columns sum to the subtotal on every row.
5. Diff against the seller's index spreadsheet — every PDF present in the index, every index
   row backed by a PDF, amounts agreeing. **Report the exceptions.** A $10 discrepancy or a
   missing invoice is exactly the kind of thing this exercise exists to surface, and it is
   more valuable to the reader than any total in the file.

## Reporting back

Lead with the portfolio totals — kW, MRC, invoice total — then the category breakdown, then
the things that need a human. Name the largest estimate in the file by size, not just by
existence, so the reader knows how much of the total rests on judgment. Call out the
reconciliation exceptions explicitly; they are findings, not footnotes.

Do not re-describe the workbook's contents at length. The reader can open it.

## References

- `references/kw-derivation.md` — full kW conventions, billing patterns, SKU parsing, edge cases
- `references/parsing-recipes.md` — working regexes, column-shift handling, text normalization
- `references/categories.md` — charge category taxonomy and how to extend it
