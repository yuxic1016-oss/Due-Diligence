# Reconciling the seller's tracker

A seller diligence tracker (or Q&A log) has one row per request with a status — Closed, Partial, Open — and usually a free-text response citing a VDR reference. It is a claim, not evidence.

Check every Closed item against the data room. The tracker is also dated: anything posted after its date will be stale in it.

## What to check, in order

1. **Does the cited VDR reference exist?** Search the file index for the exact number. This is the most common failure — a reference like `5.3.6.2.10` or `5.3.1.2.3` that was never posted, on an item marked Closed.
2. **Is it the right reference?** A response citing `5.3.1.7.11` for a Phase I ESA when `.11` is a structural package summary and the ESA is `.16`. The document exists; the pointer is wrong. Lower severity, still worth naming.
3. **Does the cited file actually answer the request?** A facility vendor list request closed with a file of utility invoices. A Certificate of Occupancy request closed with a permit close-out. A budget request closed with the banker's model. A general ledger request closed by declining and pointing at a report that is not in the room.
4. **Was a multi-part request only partly delivered?** "Structural Assessment, PCA, ESA" closed with two of the three.
5. **Was the question actually answered, or deflected?** Watch for responses that end by asking the buyer to confirm the folder covers what they wanted. That is an open item wearing a Closed label.
6. **What has landed since the tracker date?** Items still marked Open or Partial that are now in the room. Tell the user what they can close.

## Verdict vocabulary for the comparison tab

- `Agree` — closed and delivered
- `Agree — now in the VDR` — delivered by email at the time, since posted
- `Closed on a substitute` — something arrived, but not what was asked for
- `Dispute — cited file does not exist`
- `Dispute — wrong reference`
- `Dispute — closed but not delivered`
- `Should now be Closed` — tracker is stale in the seller's disfavour
- `Still open — confirmed`

On the Checklist tab all of these collapse to **Partial** with the explanation in the note. The full verdicts live on the Tracker vs Data Room tab.

## Scope

Trackers are final-round or exclusivity lists — often 30-odd items against a checklist of 150+. Say so explicitly in the report: the majority of checklist gaps have never been put to the seller at all, and will not close by themselves. List the ones that were never raised.

## Note wording on the Checklist tab

Quote the seller so the note survives forwarding:

- `From seller: Cash basis is not available; The greatest detail is the KMPG QoE`
- `From seller: Please refer to the financial model`

Where the dispute is factual, state it flatly and give the evidence:

- `Tracker cites VDR 5.3.6.2.10 — no such file. Most recent AR aging is 12/31/2025`
