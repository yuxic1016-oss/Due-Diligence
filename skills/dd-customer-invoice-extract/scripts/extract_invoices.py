#!/usr/bin/env python3
"""
Extract line items from a folder of customer/tenant invoice PDFs, derive kW per
power line, categorize every charge, and reconcile against each invoice's printed
subtotal.

Usage:
    python extract_invoices.py <invoice_folder> -o extracted.json
    python extract_invoices.py <folder> -o out.json --derate 0.8 --redundancy 2N
    python extract_invoices.py <folder> -o out.json --report-only

The reconciliation report is the point. Do not build a workbook while any invoice
mismatches its printed Service Items subtotal.
"""
import argparse, glob, json, os, re, sys

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber required:  pip install pdfplumber --break-system-packages")

# ---------------------------------------------------------------- text helpers

def money(s):
    """'$ (1,234.56)' -> -1234.56 ; returns None if not parseable."""
    if s is None:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    neg = s.startswith("(") or s.startswith("-")
    s = s.strip("()-")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def normalize(desc):
    """Undo the stray-space artifacts PDF text extraction inserts.

    Extractors routinely split the first character of a cell ('P WR-120-30-P')
    and break voltages ('1 20V POWER'). Both destroy naive regexes.
    """
    d = re.sub(r"\bP\s+WR", "PWR", desc)
    d = re.sub(r"\b(\d)\s(\d\d)\s*(V\b|VOLT|Volt|volt|v\b)", r"\1\2 \3", d)
    return d


# Line-item row. Handles an optional Discount column (a second money value or a
# percentage between quantity and total) and thousands separators in quantity.
ROW = re.compile(
    r"^(\d{3,6})\s+"                                   # item id
    r"(.*?)"                                           # description (lazy)
    r"\$\s*(\(?-?[\d,]+\.\d\d\)?)\s+"                  # unit price
    r"(-?[\d,.]+)\s+"                                  # quantity
    r"(?:(\$\s*\(?-?[\d,]+\.\d\d\)?|[\d.]+%)\s+)?"     # optional discount
    r"\$\s*(\(?-?[\d,]+\.\d\d\)?)\s*$"                 # total due
)
DATE = re.compile(r"([A-Z][a-z]{2}/\d{2}/\d{4})")

HDR_PATTERNS = {
    "inv":        re.compile(r"Invoice\s*(?:Number|No\.?|#)\s*:?\s*(\S+)", re.I),
    "date":       re.compile(r"Invoice\s*Date\s*:?\s*(\S+)", re.I),
    "svc_total":  re.compile(r"Service Items\s*:?\s+\$\s*(\(?-?[\d,]+\.\d\d\)?)", re.I),
    "inv_total":  re.compile(r"Invoice Total\s*:?\s+\$\s*(\(?-?[\d,]+\.\d\d\)?)", re.I),
}
CUST = re.compile(
    r"^(?:Bill\s*To|Customer)\s*:\s*(.*?)\s+"
    r"(?:Prior Balance|Payments|Service Items|Taxes|Invoice Total|Amount)\s*\$", re.I)
TABLE_START = re.compile(r"^\s*ID\s*#", re.I)
TABLE_END = re.compile(r"^\s*(Invoice Total|Aging|Service Items:|Taxes\s*$)", re.I)


# ------------------------------------------------------------ kW / categories

CODE_VOLTS = {"PW120": 120, "PWR120": 120, "PW12P0": 120, "PWR110": 110,
              "PW208": 208, "PWR208": 208, "PWR2": 208, "PW48": 48, "PWRDC": 48}
POWER_CODES = set(CODE_VOLTS) | {"PWR"}
# Typical per-amp monthly rates, used only to back into amperage on flat-rate
# cabinet lines that state no amps. Override with --rate 208=39.50 if the folder
# shows a different rate.
DEFAULT_RATES = {48: 15.00, 110: 20.06, 120: 20.06, 208: 37.76}

CATEGORY_MAP = {
    "Power": ["PW120", "PWR120", "PW12P0", "PWR110", "PW208", "PWR208",
              "PWR2", "PW48", "PWRDC", "PWR"],
    "Space / Cabinet": ["CSP", "SCSP", "USPACE", "UUSPACE", "COLO", "CS", "RTSPC"],
    "Cross Connect / Fiber": ["XCON", "XCONF", "XCONC", "XXCON", "JXIXXC",
                              "DEVL", "BPEN", "COND", "MISC"],
    "Bandwidth": ["BW", "IBW", "BW-OVER", "JXIX10G"],
    "Ports": ["SPORT", "PORT", "SWP", "SWITCHP"],
    "IP Addresses": ["IPAD", "IPADDR", "IPADDY"],
    "Rent / CAM / Utilities": ["WHLSLE-RNT", "WHLSLE-CAM", "WHLSLE-ACCESS",
                               "WHLSLE-GRGE", "WHLSLE-ELTC"],
    "Chilled Water": ["CHWCOMCHG", "CHWCONSCHG", "CHWDTPCHG", "CHWDMDCHG",
                      "CHW-COMCHG", "CHW-CONSCHG", "CHW-DTPCHG", "CHW-DMDCHG"],
    "Remote Hands": ["REMOTE-HANDS-KVM", "REMOTEHANDS"],
    "Hardware / PDU": ["HRDWARE", "HARDWARE"],
    "Master Service ($0)": ["MSVC", "MMSVC", "MSV"],
    "Setup Fee (one-time)": ["SETP", "INSTALL", "NRC"],
    "Late Fee (one-time)": ["LATE"],
}
CODE_TO_CAT = {c: cat for cat, codes in CATEGORY_MAP.items() for c in codes}
ONETIME = re.compile(r"(?i)late fee|\(LATE\)|setup fee|set-?up fee|\(setp\)|"
                     r"install(ation)? fee|\bNRC\b|one[- ]time charge")
POWERY = re.compile(r"(?i)(pwr|power|amp|volt|vac|\bkw\b)")
NON_CAPACITY = re.compile(r"(?i)plug access|rental|hrdware|hardware")


def code_of(desc):
    """Trailing parenthesized product code, e.g. '... (PW120)' -> 'PW120'.

    Ignores parentheticals that are pure digits/punctuation (invoice numbers
    referenced inside late-fee descriptions).
    """
    m = [x for x in re.findall(r"\(([A-Za-z0-9 -]{2,20})\)", desc)
         if re.search(r"[A-Za-z]", x)]
    return m[-1].upper().replace(" ", "") if m else ""


def derive_kw(desc, qty, derate, redundancy_mode, rates):
    """Return dict(kw, V, A, circ, ph, red, flag) or None if not a power line."""
    d = normalize(desc)
    code = code_of(desc)
    flags = []
    if not POWERY.search(d):
        return None

    # Some invoices state kW outright ("... includes 30KW 208v A+B"). Trust it.
    m = re.search(r"(?i)(\d+(?:\.\d+)?)\s*KW\b", d)
    if m:
        return {"kw": float(m.group(1)), "V": "", "A": "", "circ": "", "ph": "",
                "red": "", "flag": "kW stated on invoice"}

    if NON_CAPACITY.search(d):
        return None

    # A SKU like PWR-120-30-P is more reliable than the prose beside it, which
    # is hand-edited and sometimes disagrees.
    V = A = None
    sku = re.search(r"(?i)PWR?-(\d{2,3})-(\d{1,3})A?\b", d)
    if sku:
        V, A = int(sku.group(1)), float(sku.group(2))
        text_a = re.search(r"(?i)(\d{1,3}(?:\.\d+)?)\s*AMPS?\b", d)
        if text_a and abs(float(text_a.group(1)) - A) > 1e-6:
            flags.append(f"SKU says {A:g}A, description says {text_a.group(1)}A; SKU used")

    if V is None:
        mv = re.search(r"(?i)(\d{2,3})\s*(?:VOLTS?|VAC|V)\b", d)
        if mv:
            V = int(mv.group(1))
    if re.search(r"(?i)-?\s?48\s*(?:v)?\s?dc", d):
        V = 48
    if V is None or V not in rates:
        V = CODE_VOLTS.get(code, V)
    if V is None:
        return None

    if A is None:
        ma = (re.search(r"(?i)(\d{1,3}(?:\.\d+)?)\s*AMPS?\b", d)
              or re.search(r"(?i)(\d{1,3})A\b", d))
        if ma:
            A = float(ma.group(1))

    # A PDU line with no amperage is a device, not capacity.
    if A is None and re.search(r"(?i)\bPDU\b", d):
        return None

    red = 2 if re.search(r"(?i)a\s*[\+&]\s*b|\b2n\b|primary/secondary|\(a/b\)", d) else 1
    if redundancy_mode == "N":
        red_applied = 1
    else:
        red_applied = red

    if A is None:
        # No amperage stated anywhere. Per-amp billing puts amps in quantity.
        A, circ = qty, 1.0
        if qty == 1:
            flags.append("amps not stated")
    else:
        # When quantity equals the stated amperage the provider is billing per
        # amp, so it is one circuit -- not `qty` circuits.
        circ = 1.0 if abs(qty - A) < 1e-6 else qty

    ph = 1.7320508 if re.search(r"(?i)3\s*-?\s*(ph|phase)", d) else 1.0
    return {"kw": V * A * circ * derate * ph * red_applied / 1000.0,
            "V": V, "A": A, "circ": circ, "ph": round(ph, 7), "red": red_applied,
            "flag": "; ".join(flags)}


def estimate_amps_from_price(res, unit, rates):
    """Flat-rate cabinet lines state no amperage. Back into it from the
    provider's own per-amp rate, and say so on the line."""
    if res and res.get("flag") == "amps not stated" and unit and unit > 200:
        V = res["V"]
        rate = rates.get(V)
        if rate:
            est = round(unit / rate)
            if est >= 1:
                res["A"] = float(est)
                res["circ"] = 1.0
                res["kw"] = V * est * res["_derate"] * res["red"] / 1000.0
                res["flag"] = (f"amps not stated; estimated {est}A "
                               f"from ${rate:,.2f}/amp {V}V rate")
    return res


# ------------------------------------------------------------------- pipeline

def parse_pdf(path, site):
    with pdfplumber.open(path) as pdf:
        lines = []
        for page in pdf.pages:
            lines += (page.extract_text() or "").split("\n")

    rec = {"file": os.path.basename(path), "site": site, "items": []}
    for L in lines:
        for key, pat in HDR_PATTERNS.items():
            m = pat.search(L)
            if m and key not in rec:
                rec[key] = m.group(1) if key in ("inv", "date") else money(m.group(1))
        m = CUST.search(L)
        if m and "cust" not in rec:
            rec["cust"] = m.group(1).strip()
    if "cust" not in rec:
        for L in lines:
            if re.match(r"(?i)^\s*(Bill\s*To|Customer)\s*:", L):
                rec["cust"] = re.sub(r"(?i)^\s*(Bill\s*To|Customer)\s*:", "", L).strip()
                break

    items, inside = [], False
    for L in lines:
        s = L.strip()
        if TABLE_START.match(s):
            inside = True
            continue
        if not inside:
            continue
        if TABLE_END.match(s):
            inside = False
            continue
        m = ROW.match(s)
        if m:
            desc = m.group(2)
            dates = DATE.findall(desc)
            desc = " ".join(DATE.sub("", desc).replace(" - ", "  ").strip(" -").split())
            items.append({"id": m.group(1), "desc": desc,
                          "range_start": dates[0] if dates else None,
                          "unit": money(m.group(3)),
                          "qty": float(m.group(4).replace(",", "")),
                          "disc": m.group(5),
                          "total": money(m.group(6))})
        elif items and s and not s.startswith("Page ") and not s.startswith("Powered by"):
            # Continuation of a wrapped description.
            dates = DATE.findall(s)
            s2 = DATE.sub("", s).strip(" -")
            if dates and not items[-1]["range_start"]:
                items[-1]["range_start"] = dates[0]
            if s2:
                items[-1]["desc"] = " ".join((items[-1]["desc"] + " " + s2).split())

    rec["items"] = items
    rec["items_sum"] = round(sum(i["total"] or 0 for i in items), 2)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("-o", "--output", default="extracted.json")
    ap.add_argument("--derate", type=float, default=0.8,
                    help="breaker derate factor (0.8 = NEC continuous load; 1.0 = nameplate)")
    ap.add_argument("--redundancy", choices=["N", "2N"], default="N",
                    help="N counts one feed of an A+B pair; 2N counts both")
    ap.add_argument("--rate", action="append", default=[], metavar="V=RATE",
                    help="override per-amp rate used to estimate unstated amps, e.g. 208=39.50")
    ap.add_argument("--report-only", action="store_true",
                    help="print the reconciliation report and exit without writing JSON")
    args = ap.parse_args()

    rates = dict(DEFAULT_RATES)
    for r in args.rate:
        v, _, x = r.partition("=")
        rates[int(v)] = float(x)

    pdfs = sorted(glob.glob(os.path.join(args.folder, "**", "*.pdf"), recursive=True))
    if not pdfs:
        sys.exit(f"no PDFs found under {args.folder}")

    recs = []
    for p in pdfs:
        parent = os.path.basename(os.path.dirname(p))
        site = re.sub(r"^[\d.]+_", "", parent) or "(root)"
        rec = parse_pdf(p, site)
        for it in rec["items"]:
            res = derive_kw(it["desc"], it["qty"], args.derate, args.redundancy, rates)
            if res:
                res["_derate"] = args.derate
                res = estimate_amps_from_price(res, it["unit"], rates)
                res.pop("_derate", None)
            it["kwd"] = res or {}
            it["kw"] = round(res["kw"], 3) if res else 0.0
            it["code"] = code_of(it["desc"])
            it["cat"] = CODE_TO_CAT.get(it["code"], "Other")
            it["onetime"] = bool(ONETIME.search(it["desc"]))
        recs.append(rec)

    # ------------------------------------------------------ reconciliation
    bad = [r for r in recs
           if r.get("svc_total") is None
           or abs(r["items_sum"] - r["svc_total"]) > 0.02]
    print(f"invoices: {len(recs)}   line items: {sum(len(r['items']) for r in recs)}")
    print(f"reconciled to printed subtotal: {len(recs) - len(bad)}/{len(recs)}")
    for r in bad:
        print(f"  MISMATCH {r['file']}: printed {r.get('svc_total')} "
              f"vs extracted {r['items_sum']} ({len(r['items'])} rows)")

    unmapped = sorted({(i["code"], i["desc"][:60]) for r in recs for i in r["items"]
                       if i["cat"] == "Other"})
    if unmapped:
        print("\nunmapped charge codes (extend CATEGORY_MAP):")
        for c, d in unmapped:
            print(f"  {c or '(none)':20s} {d}")

    flagged = [(r["inv"], i["desc"][:60], i["kwd"]["flag"])
               for r in recs for i in r["items"]
               if i.get("kwd", {}).get("flag")]
    if flagged:
        print(f"\nkW lines needing a human ({len(flagged)}):")
        for inv, d, f in flagged:
            print(f"  {inv}  {d}\n      -> {f}")

    print(f"\ntotal derived kW: {sum(i['kw'] for r in recs for i in r['items']):,.2f}")

    if args.report_only:
        return
    if bad:
        print("\nWARNING: writing JSON despite mismatches. Fix the parse before "
              "building a workbook -- downstream totals inherit the error.",
              file=sys.stderr)
    with open(args.output, "w") as fh:
        json.dump({"meta": {"folder": os.path.abspath(args.folder),
                            "derate": args.derate,
                            "redundancy": args.redundancy,
                            "rates": rates,
                            "reconciled": len(recs) - len(bad),
                            "invoice_count": len(recs)},
                   "invoices": recs}, fh, indent=1)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
