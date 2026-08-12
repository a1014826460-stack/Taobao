# AGENTS.md

## Global Windows Shell Convention

- Use PowerShell 7 (`pwsh.exe`) for all terminal commands; do not use Windows PowerShell (`powershell.exe`) unless a task explicitly requires it.
- At the start of a PowerShell session, set console input/output and pipeline encodings to UTF-8 without a BOM before invoking native tools or reading and writing UTF-8 text files.
- For Python processes, set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.

## Fan-B API Cost-Control Rules

`api-gw.fan-b.com` is a metered/billable API. Every request to this host consumes paid quota, including search, detail, retry, failed, blocked, and probing requests.

Before any command or script may access `api-gw.fan-b.com`:

1. Prefer local data first: inspect SQLite databases, saved raw JSON, logs, and existing state tables before making network calls.
2. Do not probe casually: never send sample/test API requests unless they are necessary and explicitly justified.
3. Estimate request volume before bulk runs: calculate target keywords × sorts × pages × retries, and avoid unbounded loops.
4. Use resumable state: never re-fetch rows already marked `success`; do not use `--reset` unless explicitly approved.
5. Target only gaps: when补抓, limit work to keywords/items still below the requested target and prioritize never-tried candidates over retrying known failures.
6. Keep retries bounded: retry transient failures only a small fixed number of times; do not implement infinite or open-ended retry loops.
7. Stop on billing/auth errors: if the API returns billing/auth errors such as `error_code=4016`, stop API access immediately and report the condition.
8. Ask before expensive expansion: broad sort/page/price segmentation or large detail crawls require an explicit plan and confirmation when they would trigger many paid calls.
9. Record run boundaries: save timestamps/filters for crawl and upload runs so increments can be resumed without duplicate API calls or duplicate uploads.
10. Upload API is separate: these cost-control rules are specifically for `api-gw.fan-b.com`; still avoid duplicate uploads by using local state/timestamps.
