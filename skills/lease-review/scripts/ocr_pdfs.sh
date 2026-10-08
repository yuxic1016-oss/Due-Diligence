#!/bin/bash
# OCR every PDF under a source directory that pdftotext cannot already read.
#
#   ocr_pdfs.sh <source-dir> <output-dir> [workers]
#
# Writes one .txt per PDF into <output-dir>, named after the PDF's path with
# separators flattened to "__", with "=== PAGE nn ===" markers before each page
# so a search hit can be mapped back to a page number for citation and snipping.
#
# Documents that already yield text are extracted with pdftotext -layout, which
# is both faster and more accurate than OCR. Only the scans get rendered.
#
# Re-running is safe: a PDF whose output file already has content is skipped,
# so an interrupted run resumes where it stopped.

set -u

SRC="${1:?usage: ocr_pdfs.sh <source-dir> <output-dir> [workers]}"
OUT="${2:?usage: ocr_pdfs.sh <source-dir> <output-dir> [workers]}"
WORKERS="${3:-1}"

command -v pdftotext >/dev/null || { echo "need poppler-utils (pdftotext, pdftoppm)"; exit 1; }
command -v tesseract >/dev/null || { echo "need tesseract-ocr"; exit 1; }

mkdir -p "$OUT" "$OUT/.work" "$OUT/.lock"

# Bytes of extracted text per page below which we assume the PDF is a scan.
# Born-digital legal documents run 1500-3000; scans yield a Docusign header or
# nothing at all. 200 sits well clear of both.
THRESHOLD_PER_PAGE=200

flatten() { printf '%s' "$1" | sed 's|^\./||; s|/|__|g; s|\.pdf$||'; }

worker() {
  local id="$1"
  cd "$SRC" || exit 1
  # -print0 / read -d '' because lease filenames routinely contain spaces,
  # ampersands and parentheses. Word-splitting here produces empty OCR output
  # that looks like a failed scan rather than a bug, which is expensive to chase.
  find . -name '*.pdf' -print0 | sort -z | while IFS= read -r -d '' f; do
    local base out lock pages txt bytes perpage work
    base=$(flatten "$f")
    out="$OUT/$base.txt"
    lock="$OUT/.lock/$base"

    # mkdir is atomic, so it claims a file for exactly one worker.
    mkdir "$lock" 2>/dev/null || continue
    [ -s "$out" ] && continue

    pages=$(pdfinfo "$f" 2>/dev/null | awk '/^Pages:/{print $2}')
    [ -z "$pages" ] && { echo "SKIP (unreadable) $base" >&2; continue; }

    txt=$(pdftotext -layout "$f" - 2>/dev/null)
    bytes=${#txt}
    perpage=$(( bytes / pages ))

    if [ "$perpage" -ge "$THRESHOLD_PER_PAGE" ]; then
      : > "$out"
      local p=1
      while [ "$p" -le "$pages" ]; do
        echo "=== PAGE $p ===" >> "$out"
        # tr -d '\f': pdftotext terminates each page with a form feed, which
        # would otherwise prefix the NEXT page marker as "\f=== PAGE n ===".
        # Any regex anchored at ^ then fails to match, and line-to-page mapping
        # silently reports page 1 for every hit — a wrong citation that looks right.
        pdftotext -layout -f "$p" -l "$p" "$f" - 2>/dev/null | tr -d '\f' >> "$out"
        p=$((p + 1))
      done
      echo "TEXT $base ($pages pp)"
    else
      work="$OUT/.work/w$id"
      rm -rf "$work"; mkdir -p "$work"
      pdftoppm -r 200 -gray -png "$f" "$work/pg" 2>/dev/null
      : > "$out"
      find "$work" -name 'pg*.png' -print0 | sort -z | while IFS= read -r -d '' img; do
        local nm
        nm=$(basename "$img" .png)
        echo "=== PAGE ${nm#pg-} ===" >> "$out"
        tesseract "$img" stdout --psm 6 >> "$out" 2>/dev/null
      done
      rm -rf "$work"
      echo "OCR  $base ($pages pp)"
    fi
  done
}

for i in $(seq 1 "$WORKERS"); do
  worker "$i" &
done
wait

rm -rf "$OUT/.work" "$OUT/.lock"
echo "--- done: $(ls -1 "$OUT" | wc -l) files in $OUT"
