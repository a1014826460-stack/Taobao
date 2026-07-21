# Tmall Crawlers

- `direct/`: signed requests sent directly to Tmall/Taobao platform endpoints.
- `proxy/`: crawlers routed through an intermediary, including `api-gw.fan-b.com`.

## Direct SKU Adjustment

```powershell
$env:TMALL_COOKIE = '<logged-in Cookie>'
$env:TMALL_SKU_ID = '6277426546603' # Optional.
python .\src\tmall\direct\pcdetail_adjust.py
```

The script writes the complete response to
`data/raw/tmall/pcdetail_adjust_1007839388129.json`. Set `TMALL_OUTPUT_PATH`
to write it elsewhere.
