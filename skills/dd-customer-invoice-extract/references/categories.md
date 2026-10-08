# Charge categories

The category breakdown is often the most-read part of the deliverable: it answers "what is
this revenue actually made of" in one glance. Getting the taxonomy right matters more than
getting it granular.

## The default taxonomy

| Category | Typical product codes | What it captures |
|---|---|---|
| Power | `PW120` `PWR120` `PW208` `PWR208` `PWR2` `PW48` `PWRDC` `PWR` | Billed circuits, plug access, per-amp charges |
| Space / Cabinet | `CSP` `SCSP` `USPACE` `COLO` `CS` `RTSPC` | Cabinets, cages, shared colo, rack units |
| Cross Connect / Fiber | `XCON` `XCONF` `XCONC` `BPEN` `COND` `MISC` | Cross connects, fiber entry, conduit, tie cables |
| Bandwidth | `BW` `IBW` `BW-OVER` | IP transit, blended bandwidth, 95th-percentile overage |
| Ports | `SPORT` `PORT` `SWP` | Switch ports, network drops |
| IP Addresses | `IPAD` `IPADDR` `IPADDY` | IPv4/IPv6 blocks |
| Rent / CAM / Utilities | `WHLSLE-RNT` `WHLSLE-CAM` `WHLSLE-ELTC` `WHLSLE-ACCESS` | Wholesale rent, CAM, electric, access fobs, garage |
| Chilled Water | `CHW-COMCHG` `CHW-CONSCHG` `CHW-DMDCHG` `CHW-DTPCHG` | Commodity, consumption, demand, delta-T penalty |
| Remote Hands | `REMOTE-HANDS-KVM` | Time-billed hands and eyes |
| Hardware / PDU | `HRDWARE` | PDU and equipment rental |
| Master Service ($0) | `MSVC` `MMSVC` | $0.00 service header rows |
| Setup Fee (one-time) | `SETP` `INSTALL` `NRC` | Non-recurring install and setup |
| Late Fee (one-time) | `LATE` | Late payment charges |

## Extending it

`extract_invoices.py` prints every unmapped code with a sample description at the end of
its run. Work that list to zero before building — an "Other" bucket with real money in it
is a question a reader will ask and you will not be able to answer.

Add to `CATEGORY_MAP` in `extract_invoices.py`, and add the display name to `CATS` in
`build_workbook.py`. The two lists must agree or the Summary category columns will not sum
to the subtotal.

## Extracting the code

The code is the last parenthesized token in the description:

```
PWR-120-30-P 120 VOLT 30 AMP SINGLE PHASE POWER CIRCUIT A+B (PW120)   -> PW120
```

Two traps:

**Numeric parentheticals.** Late-fee descriptions embed the invoice they reference:
`Initial late fee charge for invoice (1584-39156) (LATE)`. Filter to parentheticals
containing at least one letter, or the code becomes `1584-39156`.

**Hyphens and spaces.** Codes like `WHLSLE-RNT` and `CHW - DMD CHG` need `-` and space in
the character class, then spaces stripped. Widening the class is safe because `(A+B)` and
`(A/B)` contain characters that stay excluded.

## Category design notes

**Keep Master Service visible.** These are $0.00 header rows, but they carry the tenant's
cabinet or suite identifier and there are usually one per service. Folding them into
"Other" loses a useful line count; hiding them entirely makes the line-item count disagree
with the PDFs.

**Split one-time out by category, not just by flag.** `Setup Fee (one-time)` and
`Late Fee (one-time)` as their own categories let a reader see the one-time amount in the
category rollup without cross-referencing the MRC column.

**Wholesale rent is not "Other".** It is frequently the single largest category by dollars
— on a mixed retail/wholesale portfolio it can exceed 40% of MRC — and it behaves nothing
like colo revenue. It always deserves its own line.

**Resist over-splitting.** Separate categories for `XCON` (copper) and `XCONF` (fiber) look
precise but produce a rollup nobody reads. Combine into Cross Connect / Fiber and leave the
distinction in the Line Items tab where someone can filter for it.
