# Working with a data room on the user's machine

Applies when running in the cloud with the desktop bridge (`mcp__remote-devices__*`). Skip if the data room is attached to the chat or already local.

## Getting to it — after the user has named it

The user names the folder first (SKILL.md step 0). These tools are for reaching a folder they have already identified, not for hunting one down.

`get_device_info` gives connected folders. If the one they named is not connected, request it:

```
device_request_folder_access(paths=["~/Downloads"], reason="...")
```

Each request spends the user's attention, so ask once for the minimal set. VDR exports usually sit in Downloads as `OneDrive_<date>.zip`, `Data Room <date>`, or a dated folder carrying the project name — useful for recognising what they describe, not for picking on their behalf.

If a listing turns up several vintages of the same room, or several deals, **stop and ask which one** rather than defaulting to the newest.

`device_list_dir` on a large folder will blow the output limit. Use `device_bash` with `ls`/`find` instead, or narrow to a subdirectory.

## Reading the index without extracting

```bash
unzip -Z1 "OneDrive_2026-08-12.zip"          # flat path list, no extraction
unzip -Z1 archive.zip | wc -l
```

Write the listing to a file inside the connected folder, then `device_stage_files` it into the container to analyse. Far cheaper than extracting 1.6 GB to answer "what's in here".

Entries ending in `/` with no file under them are **empty folders** — record them.

## Extracting

The user usually wants clickable paths, so extract. Two constraints:

- **Background jobs are killed** when the `device_bash` call returns. `nohup … &`, `setsid`, `disown` — all die. Extraction must run in the foreground.
- **Each call is capped at 45 s.**

So extract in foreground chunks, using `-n` (never overwrite) so each call resumes where the last stopped:

```bash
cd "/sessions/<id>/mnt/Downloads" && \
  timeout 40 unzip -n -q "OneDrive_2026-08-12.zip" -x "*Facility Photos*" -d . ; \
  find "Data Room 8.12.26" -type f | wc -l
```

Exclude photo folders on the first passes so the documents that matter land first. Repeat until the count stops rising, then drop the `-x` for a final pass. Expect 5–15 calls for a large room.

Verify completeness by diffing the zip index against what is on disk — the difference should be exactly the empty directory entries:

```bash
unzip -Z1 a.zip | sed 's|^prefix/||' | sort > /tmp/inzip.txt
(cd "Data Room 8.12.26" && find . -type f | sed 's|^\./||' | sort) > /tmp/ondisk.txt
comm -23 /tmp/inzip.txt /tmp/ondisk.txt
```

## Reading documents

`device_bash` has no network and the container tools are richer, so stage the files you want to read:

```
device_stage_files(paths=[<absolute windows paths>])   # up to 50 per call
```

They appear under `/mnt/user-data/uploads/<folder>/…` for `Bash` and `Read` on the next turn. Stage the 15–25 documents that carry the judgement calls, not the whole room.

## Delivering

`SendUserFile` puts the workbook in the conversation and returns a `file_uuid`; `device_commit_files` writes it to their disk. Do both — they will want it next to the data room. Use `force: true` when overwriting a file you wrote earlier in the session.

## If the bridge drops

Tool list shrinking to only `get_device_info` means the MCP server reconnected without re-registering. `RefreshMcpTools(server="remote-devices")` brings the rest back. If it does not, say so plainly rather than retrying.
