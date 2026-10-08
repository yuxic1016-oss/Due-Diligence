# OCR notes

Why `scripts/ocr_pdfs.sh` is shaped the way it is, and the failure modes worth knowing before you write your own extraction loop. Every item here cost real time in an actual review.

## Contents

- [Detecting scans](#detecting-scans)
- [Filenames with spaces](#filenames-with-spaces)
- [Page markers and citation](#page-markers-and-citation)
- [Background jobs on a remote device shell](#background-jobs-on-a-remote-device-shell)
- [Killing a runaway job](#killing-a-runaway-job)
- [Home directory differs between tools](#home-directory-differs-between-tools)
- [Parallelism](#parallelism)
- [OCR quality and what to distrust](#ocr-quality-and-what-to-distrust)
- [Where to run OCR](#where-to-run-ocr)

## Detecting scans

Compare `pdftotext` output size to page count. Born-digital legal documents give 1,500–3,000 bytes per page. Scans give near zero, sometimes a Docusign envelope header of about 50 bytes. A threshold of 200 bytes per page separates them cleanly with no observed misclassification.

Do not OCR a document that already has a text layer. It is roughly 100× slower and less accurate than `pdftotext -layout`, and `-layout` preserves the column alignment that makes lease summary tables readable.

## Filenames with spaces

Lease filenames routinely contain spaces, ampersands, parentheses and commas: `Cable - Wireless L_ned by A.Sur Net).pdf`.

`for p in $(ls "$dir"/pg*.png)` splits on those spaces. Tesseract then receives fragments as arguments, writes nothing, and exits successfully. The output file contains page headers and no text — which looks exactly like a scan that failed to OCR, not like a bug. This can burn a lot of time before anyone suspects the loop rather than the scan.

Use `find -print0` piped into `while IFS= read -r -d ''`, and quote every expansion.

A quick sanity check after any OCR run: if a file contains page markers but almost no text between them, suspect the loop before you suspect the document.

## Page markers and citation

Emit `=== PAGE nn ===` before each page's text, on both the text-extraction and OCR paths. Everything downstream depends on it — mapping a search hit to a page for citation, and rendering the right page as a snip.

Make sure the marker holds the page number and nothing else. An earlier version used `printf '=== PAGE %s ===\n' "$(basename "$p" .png)"` where the basename carried the whole document path; printf reused the format string once per whitespace-separated word and produced three garbled markers per page. Page numbers then pointed nowhere.

The marker is the sole link between text and image. If it is wrong, every citation is wrong and it is not obvious from the text alone.

## Background jobs on a remote device shell

A shell on a user's machine reached through a device bridge typically terminates its process group when the call returns. `nohup ... &` does not survive it. The job appears to start, the call returns, and nothing is running.

Two ways around it:

- Split the work into chunks that each fit inside the call timeout (often about 45 seconds — roughly 4 or 5 OCR pages), and drive the loop across several calls.
- Or copy the PDFs into a persistent environment and run there. For anything over about 30 pages this is usually the better trade even counting transfer time.

In a persistent container, `setsid nohup script.sh >/dev/null 2>&1 </dev/null & disown` survives across calls.

## Killing a runaway job

`pkill -f 'ocr'` matches the shell running the `pkill` itself, because the pattern appears in that shell's own command line. The kill lands on your own process before it reaches the target, the rest of the command never runs, and the job you meant to stop keeps going.

Find the PIDs with `ps -ef | grep -v grep | grep <script>` and `kill -9` them by number.

Two OCR jobs writing the same output directory produce interleaved garbage that reads like an OCR quality problem. If output looks scrambled, check the process list before blaming the scan.

## Home directory differs between tools

In some setups a file-writing tool and the bash tool resolve `$HOME` differently — for example `/home/claude` for one and `/root` for the other. A script written to `~/x.sh` by one and executed as `~/x.sh` by the other silently runs a different file, including a stale earlier version.

Use absolute paths for anything written by one tool and read by another. If a script's behaviour does not match what you just wrote, `cat` it before debugging the logic.

## Parallelism

OCR is CPU-bound and parallelises cleanly. Two workers roughly halve wall time on a 2-core box; more workers than cores does not help.

Claim files with `mkdir "$lockdir/$name"` — atomic, so exactly one worker gets each file. Give each worker its own scratch directory for rendered images, or they overwrite each other's pages.

## OCR quality and what to distrust

Tesseract at 200 dpi grayscale with `--psm 6` handles 1990s fax-quality legal scans well enough for prose. Distrust:

- **Digits.** `4.1%` read as `4.19%`; `$149.99` and `$169.99` are one character apart and mean different things.
- **Section numbers.** `(c)` and `(e)`, `6` and `b` confuse regularly.
- **Anything under a watermark.** Confidentiality stamps and Docusign overlays scramble the text beneath them into character soup. The underlying text is usually perfectly legible to a human eye on the rendered page.
- **Handwriting.** Filled-in dates and initials rarely survive.

Every figure you intend to report should be confirmed against the rendered page. Render at 150 dpi or higher and read it; that is the same step that produces the backup snip, so it costs nothing extra.

## Where to run OCR

Prefer working on the user's own machine when the files live there — nothing is copied and their files stay current. Copy into a container when the shell there cannot do the job: no tesseract, no ability to keep a long job alive, or you need to view a rendered page as an image.

For a large scanned folder, copying to a persistent environment is usually right. Copy only what needs OCR, and copy back only finished output.
