# Parsing invoice PDFs reliably

The goal is not "extract most of the rows". It is a parse you can *prove* — every invoice's
extracted line items summing to the subtotal the PDF itself prints. Anything less and you
are shipping totals nobody can defend.

## Contents

- [The reconciliation gate](#the-reconciliation-gate)
- [Line-item row regex](#line-item-row-regex)
- [The four things that break the regex](#the-four-things-that-break-the-regex)
- [Table boundaries](#table-boundaries)
- [Wrapped descriptions](#wrapped-descriptions)
- [Header fields](#header-fields)
- [Adapting to a new provider](#adapting-to-a-new-provider)
- [Scanned invoices](#scanned-invoices)

## The reconciliation gate

Every invoice prints a pre-tax subtotal, usually labelled `Service Items`. Compare it to
the sum of extracted lines on every single invoice, and do not build a workbook until they
all match to the cent.

This one check catches essentially every parsing bug, because the failure modes are all
arithmetic: a dropped row, a duplicated row, a money column read from the wrong position.
Spot-checking three invoices by eye does not catch them; a row dropped on invoice 47 looks
exactly like a correct invoice 47.

`extract_invoices.py` prints this report and warns loudly if you write JSON anyway.

## Line-item row regex

Line items in a text-extracted invoice collapse to a single line whose money columns are
positionally stable even when the description is not:

```
9574 C OLO-CAB-FULL - FULL42U LOCKING CABINET (CSP) Aug/01/2026 - $ 405.10 5 $ 2,025.50
^id  ^description                                   ^period       ^unit  ^qty ^total
```

```python
ROW = re.compile(
    r"^(\d{3,6})\s+"                                   # item id
    r"(.*?)"                                           # description, lazy
    r"\$\s*(\(?-?[\d,]+\.\d\d\)?)\s+"                  # unit price
    r"(-?[\d,.]+)\s+"                                  # quantity
    r"(?:(\$\s*\(?-?[\d,]+\.\d\d\)?|[\d.]+%)\s+)?"     # OPTIONAL discount
    r"\$\s*(\(?-?[\d,]+\.\d\d\)?)\s*$"                 # total due
)
```

The lazy description plus anchored money columns is what makes this robust: the description
absorbs whatever junk the extractor produced, and the numbers are pinned to the end of the
line.

## The four things that break the regex

In roughly the order they bite:

**1. An optional Discount column.** Present on some invoices in a folder and absent on
others, so a fixed column count silently reads the discount as the total:

```
2682 Full Cabinet 42U (USPACE)   ... $ 400.00 1 $ 123.00 $ 277.00
                                              ^discount ^actual total
5921 SW 1 Gig Primary (SWP)      ... $   0.00 1  100.00%  $   0.00
                                              ^percentage discount
```

Handle both shapes with the optional non-capturing group above.

**2. Thousands separators in quantity.** `1,000` against a `(\d+)` quantity pattern fails
the whole row, dropping it:

```
7098 BGP Bandwidth (BW)   $ 0.50   1,000   $ 500.00
```

Allow commas, then strip them: `float(m.group(4).replace(",", ""))`.

**3. Repeated table headers on page 2.** Multi-page invoices restart the table. Treat the
header as "enter table mode" rather than a one-shot flag, or the second page is lost.

**4. Stray spaces from text extraction.** Extractors split the first character of a cell
(`C OLO-CAB-FULL`, `P WR-120-30-P`, `S ervice Items`) and break numbers (`1 20V`). The row
regex tolerates this because the description is lazy, but *semantic* parsing of the
description does not. Normalize before reading meaning out of a description; see
`kw-derivation.md`.

Note this also affects the table-header match: look for `^\s*ID\s*#` rather than the full
header string, since `Service Items` may render as `S ervice Items`.

## Table boundaries

```python
TABLE_START = re.compile(r"^\s*ID\s*#", re.I)
TABLE_END   = re.compile(r"^\s*(Invoice Total|Aging|Service Items:|Taxes\s*$)", re.I)
```

Enter on start, exit on end, re-enter on the next start. Skip `Page N of M` and
`Powered by ...` footers.

## Wrapped descriptions

A description longer than the column wraps, and the continuation looks like a data line:

```
9577 B DW-BLEND-MPBS - 1000 MBPS - 100TB MONTHLY  Aug/01/2026 - $ 463.50 1 $ 463.50
     TRANSFER - (Blue 1 & 2 ACC-B01 - Ports 21 & 22) (BW)      Aug/31/2026
```

Any in-table line that does not match ROW is a continuation: append it to the previous
item's description, and harvest a service-period date from it if the first line had none.
This matters beyond tidiness — the trailing `(BW)` product code that drives categorization
often lives on the continuation line.

Occasionally the extractor also glues an invoice's summary block onto the last description
(`... (PWR2) Service Items: $ 7,519.58 Taxes ...`). Harmless for totals; note it if a
description looks absurdly long.

## Header fields

```python
"Invoice Number: INV-1309-39284"   -> r"Invoice\s*(?:Number|No\.?|#)\s*:?\s*(\S+)"
"Invoice Date: Aug/01/2026"        -> r"Invoice\s*Date\s*:?\s*(\S+)"
"Service Items $ 6,965.89"         -> r"Service Items\s*:?\s+\$\s*([\d,]+\.\d\d)"
"Invoice Total $ 6,965.89"         -> r"Invoice Total\s*:?\s+\$\s*([\d,]+\.\d\d)"
```

Customer name is the awkward one: the bill-to block sits in a left column and the summary
box in a right column, so they collapse onto one line:

```
Bill To: CompassMSP                    Prior Balance $ 6,965.89
```

Capture up to the first summary keyword:

```python
CUST = re.compile(r"^(?:Bill\s*To|Customer)\s*:\s*(.*?)\s+"
                  r"(?:Prior Balance|Payments|Service Items|Taxes|Invoice Total|Amount)\s*\$", re.I)
```

Tax is usually cleanest as `Invoice Total - Service Items` rather than parsed directly,
since tax lines appear in their own sub-table with their own ID numbers.

## Adapting to a new provider

Work in this order:

1. Extract two or three PDFs to raw text and *read them*. Ten minutes here saves an hour of
   debugging a regex against invisible whitespace.
2. Identify the subtotal label — it may be `Subtotal`, `Total Charges`, `Recurring Charges`
   rather than `Service Items`. Update `HDR_PATTERNS`.
3. Identify the table header and terminator. Update `TABLE_START` / `TABLE_END`.
4. Check the money column order — some providers put quantity before unit price, some put
   the period at the end rather than mid-row.
5. Run with `--report-only` and iterate until reconciliation is 100%.
6. Check the unmapped-code list and extend `CATEGORY_MAP` (see `categories.md`).

If a provider's layout defeats line-based regex entirely, fall back to `pdfplumber`'s
word-level extraction and cluster words by x-coordinate into columns. Slower to write,
but position is unambiguous where whitespace is not.

## Scanned invoices

If `extract_text()` returns empty or near-empty, the PDF is an image. OCR it first
(`ocrmypdf` per the `pdf` skill), then re-run. Expect degraded accuracy on the amperage
digits specifically — `8` and `3`, `1` and `7` — so reconcile hard and spot-check every
power line by eye against the rendered page.
