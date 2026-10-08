#!/usr/bin/env python3
"""Flat index of a data room, from a .zip export or an extracted folder.

Usage:
    python3 index_dataroom.py <zip-or-folder> [--out index.txt] [--tree] [--exclude PATTERN]

Prints a summary and writes the flat path list. Empty folders are reported
separately -- a folder the seller created and left empty is a finding.
"""
import argparse
import collections
import os
import sys
import zipfile


def _empty_dirs(dirs, files):
    """A directory is empty when no file anywhere beneath it exists."""
    return sorted(d for d in dirs if not any(f.startswith(d) for f in files))


def from_zip(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    files = [n for n in names if not n.endswith("/")]
    dirs = [n for n in names if n.endswith("/")]
    return files, _empty_dirs(dirs, files)


def from_folder(path):
    files, dirs = [], []
    for root, dirnames, filenames in os.walk(path):
        rel = os.path.relpath(root, path)
        rel = "" if rel == "." else rel.replace(os.sep, "/")
        if rel:
            dirs.append(rel + "/")
        for f in filenames:
            files.append((rel + "/" + f) if rel else f)
    return files, _empty_dirs(dirs, files)


def strip_prefix(files):
    """Drop a common leading directory so paths start at the VDR root."""
    if not files:
        return files, ""
    parts = [f.split("/") for f in files]
    prefix = []
    for i in range(min(len(p) for p in parts)):
        seg = parts[0][i]
        if all(p[i] == seg for p in parts) and any(len(p) > i + 1 for p in parts):
            prefix.append(seg)
        else:
            break
    if not prefix:
        return files, ""
    n = len("/".join(prefix)) + 1
    return [f[n:] for f in files], "/".join(prefix)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default="dataroom_index.txt")
    ap.add_argument("--tree", action="store_true", help="also print the folder tree to depth 3")
    ap.add_argument("--exclude", action="append", default=[],
                    help="substring to drop from the listing (repeatable), e.g. 'Facility Photos'")
    a = ap.parse_args()

    if not os.path.exists(a.source):
        sys.exit("not found: " + a.source)

    files, empty = (from_zip(a.source) if a.source.lower().endswith(".zip")
                    else from_folder(a.source))
    files, prefix = strip_prefix(files)
    kept = [f for f in files if not any(x in f for x in a.exclude)]
    dropped = len(files) - len(kept)

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(kept)))

    print("root prefix      :", prefix or "(none)")
    print("files            :", len(files))
    if dropped:
        print("excluded         :", dropped, "(" + ", ".join(a.exclude) + ")")
    print("index written to :", a.out)

    ext = collections.Counter(os.path.splitext(f)[1].lower() for f in kept)
    print("by type          :", ", ".join("%s %d" % (e or "(none)", n)
                                          for e, n in ext.most_common(8)))

    if empty:
        print("\nEMPTY FOLDERS (%d) -- flag these, they read as delivered:" % len(empty))
        for d in empty:
            print("  ", d[len(prefix) + 1:] if prefix and d.startswith(prefix) else d)

    if a.tree:
        seen = set()
        for f in sorted(kept):
            parts = f.split("/")
            for d in range(1, min(4, len(parts))):
                seen.add("/".join(parts[:d]))
        print("\nFOLDER TREE (depth 3):")
        for s in sorted(seen):
            print("  " * s.count("/") + "  " + s.split("/")[-1])


if __name__ == "__main__":
    main()
