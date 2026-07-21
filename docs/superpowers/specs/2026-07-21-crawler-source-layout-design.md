# Crawler Source Layout Design

## Goal

Move the Tmall MTop SKU-adjustment probe into a consistent source layout and
store its captured response separately from executable source code.

## Scope

- Create a site-first layout under `src/`.
- Separate direct platform requests from proxy-backed requests.
- Move the Tmall direct MTop probe from the project root into the new layout.
- Move its captured raw response to a site-specific raw-data directory.
- Preserve existing Taobao and JD crawler paths and behavior.

## Layout

```text
src/
  tmall/
    direct/
      pcdetail_adjust.py
    proxy/
      # Proxy-backed Tmall crawlers, including api-gw.fan-b.com, live here.
  taobao/
  jd/
  common/
  tools/
data/
  raw/
    tmall/
      pcdetail_adjust_1007839388129.json
```

`direct` contains scripts that call platform endpoints such as
`h5api.m.tmall.com` using a local authenticated session. `proxy` contains
scripts whose network route is an intermediary service such as
`api-gw.fan-b.com`; this makes the data source and authentication assumptions
visible from the module path.

## Script Contract

`src/tmall/direct/pcdetail_adjust.py` remains a standalone Python CLI:

- `TMALL_COOKIE` is required and supplies the current logged-in session.
- `TMALL_SKU_ID` optionally selects the SKU, defaulting to the captured SKU.
- It computes the MTop token-MD5 `sign` immediately before the request.
- It prints a concise JSON summary and writes the complete parsed response to
  a caller-configurable output path, defaulting to the Tmall raw-data folder.

The crawler remains a standard-library HTTP script. Scrapy is not introduced:
this endpoint requires session-bound MTop signing and performs one SKU request
per invocation, so a focused CLI has less lifecycle and middleware overhead.
Future paginated or queue-based crawlers may use Scrapy while retaining the
same `site/direct|proxy` module boundary and output conventions.

## Testing

Tests are placed under `tests/` and cover deterministic helpers only:

- extracting `_m_h5_tk` from a Cookie header;
- generating the expected token-MD5 signature for a fixed timestamp and data;
- producing the exact nested `exParams` schema;
- parsing both JSONP and JSON response bodies.

Network calls and real credentials are not used in automated tests.

## Error Handling

The CLI raises a clear error when `TMALL_COOKIE` or `_m_h5_tk` is absent. An
MTop response with a non-success `ret` is emitted in the JSON summary and
retained in the raw response file for investigation. Cookie expiry remains an
operational input: the user logs in again and updates `TMALL_COOKIE`.
