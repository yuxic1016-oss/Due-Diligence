# Verifying by opening documents

Filename matching gets you a first pass. Roughly one call in five changes once the file is open, and it moves in both directions — documents that under-promise in their filename, and documents whose filename promises something they do not contain.

## Which documents repay opening

Open these before finalising status on any material line:

- **Site / infrastructure overview** — usually a seller Q&A response in PDF form. Frequently answers eight or ten checklist lines at once: security systems, fire suppression, PUE history, carrier and IP-transit lists, power capacity and utilisation, network hardware inventory, expansion ROM costs.
- **IT overview** — names the actual software stack, licence costs and renewal dates, and (critically) which systems are shared with the seller's other sites or corporate IT. This is the TSA question.
- **Infrastructure upgrades / capex summary** — names BMS platform, switchgear and generator makes, commissioning dates.
- **Floor-by-floor / capacity summary** — SF, rack count, installed vs **booked/sold** vs **actually drawn** kW. The booked-versus-drawn gap is a real finding.
- **Client database / rent roll** — check the column headers before calling it a "customer ID key". These often carry MRR, ARR, term, expiry and escalator, which resolves several separate checklist lines.
- **Employee census** — check for a pay/taxes/bonus column and a business-line split before calling compensation missing.
- **Title commitment and policy** — check the *date*, the *insured*, the *amount of insurance*, and whether the estate is fee or includes leasehold parcels.
- **Any file whose name is a summary** — "Key Vendor Summary", "Overview", "Analysis". Open it.
- **SOC 1 / SOC 2 reports** — see the trick below.

Skip: photo folders, individual unit leases, monthly utility bills, repetitive inspection reports. Sample one and move on.

## Extraction recipes

```bash
# text PDFs — preserves table layout
pdftotext -layout "file.pdf" out.txt

# scanned PDFs (no text layer) — render and read as images
pdfinfo file.pdf | grep Pages
pdftoppm -png -r 130 -f 7 -l 8 file.pdf page   # then Read the .png
```

A PDF whose `pdftotext` output is near-empty and whose Producer is a copier model (Ricoh, Xerox) is a scan. Render the pages that matter — Schedule A of a title policy, the signature page — rather than OCRing the whole thing.

```python
# spreadsheets — headers first, then a sample of rows
import openpyxl
wb = openpyxl.load_workbook(path, data_only=True)
for ws in wb.worksheets:
    print(ws.title, ws.max_row, ws.max_column)
    for r in ws.iter_rows(min_row=1, max_row=6, max_col=20):
        print([c.value for c in r])
```

Always read every tab. Notes rows at the bottom of a sheet often carry the caveat that changes the answer (e.g. "Personnel expenses exclude HSA and 401K match; estimate 8.6% medical and 1.2% workers comp").

## The SOC report trick

A SOC 1 or SOC 2 Type 2 report lists the controls the auditor tested. If it contains a control like *"business continuity and disaster recovery plans are developed and updated on an annual basis"* and *"tested on an annual basis"* with **no exceptions noted**, then the plan **exists and has been inspected by a third party** — it simply was not posted.

That converts a weak ask ("do you have a BCP?") into a strong one ("your SOC 1 control 3.2 references a BCP the auditor inspected — please post it"). Grep the SOC reports for `business continuity`, `disaster recovery`, `preventive maintenance`, `subservice organization`, `complementary user entity`.

The same report also tells you whether any function is outsourced to a subservice organisation, and which controls the buyer is expected to run itself.

## Traps seen in the wild

| Looked like | Actually was |
|---|---|
| "Key Vendor Summary.xlsx" | Utility invoice totals and one software cost note. No vendors. |
| "Certificate of Occupancy" (per seller) | A building-permit **Certificate of Completion** for an alterations permit. |
| Title commitment and policy | Dated six years earlier, insuring the seller's own acquisition, at a nominal amount, fee estate only — while the commitment referenced leasehold parcels the policy did not cover. |
| "Risk Management Overview" | A one-paragraph corporate insurance philosophy memo. No claims data, nothing about site risk. |
| "Evidence of coverage" folder | Contained the actual policy — premium, period, layered limits, carrier participation table. Better than the name suggested. |
| "Client Database (customer ID key)" | A full rent roll with MRR, ARR, term, expiry and per-customer escalator. |
| KPMG Quality of Earnings | Only the **release letter** was posted. The report itself was absent, while two seller answers leaned on it. |

## Cross-checking within the room

Documents contradict each other. Note it rather than picking a side:

- rack counts in a narrative overview vs a capacity spreadsheet
- utilised power quoted as total facility load in one place and UPS load in another
- floors described as residential in one document and as white space in another

And read narrative answers for facts the checklist never asked for but the deal cares about — no fixed utility rate, no active roof warranties, a shared NOC manager in another city, a fuel cleanup invoice sitting in the environmental supporting docs.
