# Deriving kW from colocation invoices

Read this before touching any power line. kW is almost never printed on a colo invoice —
it has to be reconstructed from the billed circuits — and the reconstruction is where a
diligence workbook either earns trust or loses it.

## Contents

- [The formula](#the-formula)
- [Choosing a convention](#choosing-a-convention)
- [Where amps and circuits hide](#where-amps-and-circuits-hide)
- [Voltage detection](#voltage-detection)
- [Redundancy](#redundancy)
- [Three-phase](#three-phase)
- [DC power](#dc-power)
- [What to exclude](#what-to-exclude)
- [Tenants with no derivable kW](#tenants-with-no-derivable-kw)
- [Flagging estimates](#flagging-estimates)

## The formula

```
kW = Volts x Amps x Circuits x Derate x PhaseFactor x Redundancy / 1000
```

Only Volts is reliably printed. Everything else has to be inferred, and each inference has
a failure mode described below.

## Choosing a convention

Two independent choices, four combinations. Confirm with the user before building — the
spread between the smallest and largest is 2.5x.

| Convention | 120V 30A A+B | Reads as |
|---|---|---|
| 80% derate, N | 2.88 kW | Usable/contracted capacity. Usual DD default. |
| Nameplate, N | 3.60 kW | Contracted amperage without NEC derate. |
| 80% derate, 2N | 5.76 kW | Installed breaker capacity across both feeds. |
| Nameplate, 2N | 7.20 kW | Total installed amperage. Largest, least meaningful as load. |

The 80% factor is the NEC continuous-load rule: a breaker may carry only 80% of its rating
continuously. Buyers modelling *sellable* capacity generally want it. Buyers modelling
*installed* infrastructure generally do not.

N vs 2N matters more than it looks. A+B is redundant, not additive — a cabinet with A+B
30A feeds can draw 30A total, not 60A. Counting 2N describes what the facility built;
counting N describes what the tenant can actually use. Put whichever was chosen in the
Assumptions tab in words, not just as a number.

## Where amps and circuits hide

This is the part that produces wrong answers quietly. The same provider bills three
different ways, sometimes on the same invoice.

**Per-circuit billing.** Quantity is a count of circuits.

```
PWR-120-30-P 120 VOLT 30 AMP SINGLE PHASE POWER CIRCUIT A+B   $706.97 x 4 = $2,827.88
-> 4 circuits x 30A at 120V
```

**Per-amp billing.** Quantity is amperage; there is one circuit.

```
208V POWER (PWR208)                                            $37.76 x 6 = $226.56
30 Amps of 120v Power (A+B) (PWR120)                           $17.00 x 30 = $510.00
```

**The tell:** when quantity equals the amperage stated in the description, quantity is
amps and circuits is 1. When they differ, quantity is a circuit count. Getting this
backwards on a single line can move a portfolio total by tens of kW.

```python
circ = 1.0 if abs(qty - amps_from_description) < 1e-6 else qty
```

**Flat-rate cabinets.** No amperage anywhere; a single monthly price per cabinet.

```
208V Power (A+B) CAB#1 (PWR2)                                  $1,136.96 x 1
```

Back into amperage using the provider's own per-amp rate elsewhere in the same folder —
here $37.76/amp at 208V gives 30A, which matches the 30A cabinets other tenants buy. Label
the line `amps not stated; estimated 30A from $37.76/amp 208V rate`. Never let a
price-derived number pass as a read number.

**SKU vs prose.** Product codes are machine-generated; the description beside them is
hand-edited and drifts. When they disagree, trust the SKU and flag the line:

```
PWR-120-20-P  120 VOLT 30 AMP SINGLE PHASE POWER CIRCUIT A+B
              ^^^ SKU says 20A            ^^^ text says 30A
```

## Voltage detection

Priority order, because each source fails differently:

1. **SKU pattern** `PWR-120-30-P` → 120V. Most reliable.
2. **Description text** `120 VOLT`, `208 VAC`, `110v`, `208V`.
3. **Trailing product code** `(PW120)`, `(PWR208)`, `(PWR2)`, `(PW48)`, `(PWRDC)`.

Beware text-extraction artifacts. Extractors split the first character of a cell and break
numbers across spaces:

```
"P WR-120-30-P ..."   ->  normalize to "PWR-120-30-P"
"1 20V POWER (A) 20AMP" -> normalize to "120 V POWER (A) 20AMP"
```

Without normalization, `1 20V` reads as 20 volts and the line comes out 6x too small.
`extract_invoices.py:normalize()` handles both. Do not strip *all* whitespace as a
shortcut — it destroys the word boundaries the amp regex depends on and silently
mis-parses `110v Power` as unmatched.

## Redundancy

Treat as 2N when the line itself says so: `A+B`, `A + B`, `A & B`, `2N`, `(A/B)`,
`PRIMARY/SECONDARY`.

Do **not** double when primary and secondary are billed as separate line items:

```
PWR-208-20-P ... PRIMARY (A)      $602.39     <- one feed
PWR-208-20-S ... SECONDARY (B)    $301.19     <- the other feed
```

Each of these is already a single feed. Counting each as 2N double-counts twice over.
Secondary feeds are typically priced at half of primary — a useful sanity check that a
pair really is a pair.

## Three-phase

`kVA = sqrt(3) x V x A` for a three-phase circuit. Detect on `3-PHASE`, `3PH`, `3 PHASE`.
Rare on retail colo invoices, common on wholesale.

## DC power

Telecom tenants buy -48VDC by the amp:

```
400A -48DC power (A+B) (PWRDC)     $15.00 x 400 = $6,000.00
-> 48V x 400A x 0.8 x 2 = 30.72 kW
```

Apply the same derate for consistency with the AC lines and note it. Telecom plant is
often rated for continuous draw, so if the user is modelling actual load rather than
breaker capacity, a DC line may deserve nameplate treatment — ask if it is material.

## What to exclude

Not billed capacity, so not kW:

- **Plug access** — a socket, not a circuit
- **PDU rental / hardware** — a device; `120V POWER PDU RENTAL 30A 120V (HRDWARE)` names an
  amperage but rents equipment
- **Master service lines** — $0.00 header rows
- **Bare `PDU` lines with no amperage**

## Tenants with no derivable kW

Wholesale rent/CAM tenants routinely have zero derivable kW because power arrives as an
estimated electric charge folded into rent:

```
Rent - Switch Room Space (WHLSLE-RNT)                    $18,383.44
Electric Charges (estimate, trued-up monthly)            $10,656.00
```

Report zero with a note. These are frequently the *largest* MRC lines in a folder, so a
reader seeing $0 kW beside $47k MRC will assume the extraction broke unless told
otherwise. Say it in the response, not only in the workbook.

## Flagging estimates

Every one of these gets a Note on the line and a bullet on the Assumptions tab:

- amperage estimated from price
- SKU/description conflict and which won
- kW stated explicitly on the invoice (trust it, but say it came from the invoice)
- kW that could not be derived at all

Then, in the response, name the largest estimate by size. "Seabras-1 is 39.94 of the 430 kW
and rests on a price-derived amperage" tells a reader how much of the total is judgment.
"Some values were estimated" tells them nothing.
