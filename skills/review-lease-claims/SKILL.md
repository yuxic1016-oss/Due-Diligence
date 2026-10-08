---
name: review-lease-claims
description: "Check every statement in a lease or document review against the snip offered as its evidence — read the snip first, then the claim, and flag anything the image doesn't actually say."
---

# Review lease claims against their snips

Verifies that every statement in a lease or document review is supported by the
cropped page image offered as its evidence.

## The one rule that makes this work

**Read the snip before reading the statement.**

Open each snip image, transcribe what it says, and only then look at the claim it is
attached to. Reversing that order turns the review into confirmation: a reviewer
holding "base rent is $42.50/SF" in mind will find that number in a blurry crop
whether or not it is there.

Work claim by claim. Do not batch-read all the snips and then all the statements.

## Step 0 — Locate the pairs

Snips may be: image files in a folder keyed by row or claim ID; images embedded in a
workbook beside each row; images inline in a memo; or images in a chat response.
Establish which before starting and state the mapping — "row 14 →
`snips/14_base_rent.png`". A claim whose snip cannot be located is a finding (No
snip), not a claim to skip.

Coverage is **every claim, not a sample.** A lease abstract drives decisions about
money; sampling defeats the point.

## Step 1 — Read each snip cold

Open the image with the Read tool and look at it. Never verify from a filename, a
caption, alt text, or a cached transcription — those are artifacts of the process
being reviewed, so trusting them reviews nothing.

Record per snip:
- **Verbatim text** of the operative language.
- **Which document** it came from — read the header, footer, title, or exhibit label
  visible in the crop.
- **Page / section**, if visible.
- **Legibility** — anything cut off, blurred, or mid-sentence at the crop edge.

## Step 2 — Compare and assign a verdict

| Verdict | Meaning |
|---|---|
| Supported | The snip states the claim plainly. |
| Partially supported | Supports part of it — the number but not the date, the right but not its conditions. |
| Not supported | The snip does not say this. Includes the adjacent-clause error: a real clause that is not the one claimed. |
| No snip | The claim carries no evidence at all. |
| Superseded | The snip is genuine but from a document later amended on this point. |
| Illegible | The crop is unreadable or cut off, so it cannot support anything. |

### Check on every claim

- **Exact figures.** Dollar amounts, dates, square footage, percentages, month counts —
  digit by digit. Transposition (`$4,250` vs `$4,520`) survives a casual read.
- **Units and period.** $/SF/year vs $/SF/month; annual vs monthly rent; gross vs net.
  The most common silent error in lease abstracts, and always material.
- **Direction and party.** Who owes, who may terminate, who must give notice. A right
  attributed to the wrong party is a total inversion that reads fine.
- **Conditions and carve-outs.** "Tenant may terminate" is not the claim if the clause
  reads "provided no Event of Default and upon 12 months' notice and payment of a
  termination fee." Dropped conditions are the most dangerous category, because the
  statement is *almost* right.
- **Dates and windows.** Commencement, expiration, notice windows, option exercise
  periods — including whether a window runs from commencement or from expiration.
- **Derived numbers.** If the statement computes something (annual = monthly × 12,
  total = rate × SF), recompute it from the snip's own figures.
- **Defined terms.** When the snip uses a capitalized defined term ("Operating
  Expenses", "Rentable Area"), the claim's plain-English gloss must match the lease's
  definition, not the ordinary meaning. Flag when the definition wasn't checked.

### The amendment trap

A snip from the original lease can be genuine and still wrong, because a later
amendment changed the term. For any claim sourced to an original lease, confirm
whether amendments exist in the document set and whether any touch this term. An
unchecked amendment chain is a caveat on every claim — say so rather than reporting
clean.

## Step 3 — Report

Terse. One row per claim that isn't clean, most severe first (Not supported → No snip
→ Superseded → Partially supported → Illegible).

| # | Verdict | Claim | Snip reads | Correction |
|---|---|---|---|---|
| 1 | Not supported | "Tenant has a 5-year renewal option at market" | *"...one (1) option to extend for sixty (60) months at the greater of Fair Market Rent or the Rent payable in the final month of the Initial Term."* | Renewal rent is the **greater of** FMR or final-month rent — floors the renewal |
| 2 | Partially supported | "Base rent $42.50/SF" | *"...annual Base Rent of $42.50 per rentable square foot, subject to 3% annual escalation..."* | True for year 1 only; add the 3% escalator |

On mismatch: flag with the correct reading and a proposed corrected statement. **Do
not rewrite the source output** — the user approves every change.

Close with:
- **Claims reviewed:** n of n.
- **Clean:** n Supported.
- **Amendment chain:** checked / not checked, against which documents.
- **Not checked:** anything skipped, and why.

## Verification

Done when: every claim has a verdict; every verdict traces to a snip actually opened
and viewed; each mismatch quotes the snip verbatim; the amendment-chain status is
stated explicitly.

## Notes

- Supported means the snip says it — not that the claim is true of the lease as a
  whole. That needs the full document, and this skill does not claim it.
- "Probably says X, it's a bit blurry" is Illegible, not Supported. Resolve by opening
  the source PDF at that page, or report it unresolved.
- A claim that is right but carries the wrong crop is still a finding — the next person
  to check the file hits the same wall.
- Never let the source output's confidence carry a claim. Assertive phrasing is not
  evidence.