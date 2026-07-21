# Crawler Source Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Place the Tmall direct MTop SKU-adjustment crawler and its captured data in the agreed site-first source layout.

**Architecture:** The crawler stays a standard-library Python CLI because it performs one session-bound, MTop-signed SKU request. Site path conveys both target platform and network route: `tmall/direct` calls the platform endpoint, while `tmall/proxy` is reserved for proxy services such as `api-gw.fan-b.com`.

**Tech Stack:** Python 3 standard library, pytest.

---

### Task 1: Add deterministic parser and signature coverage

**Files:**
- Create: `tests/test_tmall_pcdetail_adjust.py`
- Source under test: `_tmall_probe.py`

- [ ] **Step 1: Write failing helper tests**

```python
import importlib.util
from pathlib import Path


def load_module():
    path = Path(__file__).parents[1] / "_tmall_probe.py"
    spec = importlib.util.spec_from_file_location("pcdetail_adjust", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mtop_sign_uses_token_prefix_and_exact_data():
    module = load_module()
    assert module.mtop_sign("token_123", "1700000000000", "{\"id\":\"1\"}") == "EXPECTED"


def test_parse_jsonp_and_json_return_payloads():
    module = load_module()
    assert module.parse_jsonp('cb({"ret":["SUCCESS"]})') == {"ret": ["SUCCESS"]}
    assert module.parse_jsonp('{"ret":["SUCCESS"]}') == {"ret": ["SUCCESS"]}


def test_build_data_contains_sku_click_context():
    module = load_module()
    data = module.build_data("6277426546603", "1700000000000")
    outer = __import__("json").loads(data)
    inner = __import__("json").loads(outer["exParams"])
    assert outer["id"] == "1007839388129"
    assert outer["detail_v"] == "3.3.2"
    assert inner["skuId"] == "6277426546603"
    assert inner["uniqueId"] == "6277426546603_quantity1_1700000000000"
    assert inner["modules"] == "skuClick"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tmall_pcdetail_adjust.py -q`

Expected: FAIL because `EXPECTED` is not the computed signature.

- [ ] **Step 3: Replace `EXPECTED` with the computed MD5 fixture**

```python
assert module.mtop_sign("token_123", "1700000000000", "{\"id\":\"1\"}") == "4e492a4c7d8bc38bc0f619e1e84b7ce8"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tmall_pcdetail_adjust.py -q`

Expected: `3 passed`.

### Task 2: Move the direct crawler and captured response

**Files:**
- Create: `src/tmall/__init__.py`
- Create: `src/tmall/direct/__init__.py`
- Create: `src/tmall/proxy/__init__.py`
- Move: `_tmall_probe.py` to `src/tmall/direct/pcdetail_adjust.py`
- Move: `tmall_adjust_response.json` to `data/raw/tmall/pcdetail_adjust_1007839388129.json`
- Modify: `src/tmall/direct/pcdetail_adjust.py`

- [ ] **Step 1: Move files into the site-first layout**

Run:

```powershell
New-Item -ItemType Directory -Force src/tmall/direct, src/tmall/proxy, data/raw/tmall
Move-Item _tmall_probe.py src/tmall/direct/pcdetail_adjust.py
Move-Item tmall_adjust_response.json data/raw/tmall/pcdetail_adjust_1007839388129.json
New-Item -ItemType File -Force src/tmall/__init__.py, src/tmall/direct/__init__.py, src/tmall/proxy/__init__.py
```

- [ ] **Step 2: Make raw output site-specific by default**

```python
from pathlib import Path

RAW_OUTPUT = Path(__file__).resolve().parents[3] / "data" / "raw" / "tmall" / "pcdetail_adjust_1007839388129.json"

# In main(), allow an explicit caller override while keeping the agreed default.
output_path = Path(os.getenv("TMALL_OUTPUT_PATH", RAW_OUTPUT))
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as output:
    json.dump(payload, output, ensure_ascii=False, indent=2)
```

- [ ] **Step 3: Update tests to load the moved source path**

```python
path = Path(__file__).parents[1] / "src" / "tmall" / "direct" / "pcdetail_adjust.py"
```

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_tmall_pcdetail_adjust.py -q`

Expected: `3 passed`.

### Task 3: Document execution and the direct/proxy boundary

**Files:**
- Create: `src/tmall/README.md`

- [ ] **Step 1: Add concise operational documentation**

```markdown
# Tmall Crawlers

- `direct/`: signed requests sent directly to Tmall/Taobao platform endpoints.
- `proxy/`: crawlers routed through an intermediary, including `api-gw.fan-b.com`.

## Direct SKU Adjustment

```powershell
$env:TMALL_COOKIE = '<logged-in Cookie>'
$env:TMALL_SKU_ID = '6277426546603' # optional
python .\src\tmall\direct\pcdetail_adjust.py
```

The script writes the full response to `data/raw/tmall/pcdetail_adjust_1007839388129.json`, unless `TMALL_OUTPUT_PATH` is set.
```

- [ ] **Step 2: Verify source layout and focused tests**

Run:

```powershell
Get-ChildItem src/tmall -Recurse -File
python -m pytest tests/test_tmall_pcdetail_adjust.py -q
```

Expected: direct, proxy, and README files exist; focused tests pass.

- [ ] **Step 3: Commit only migration-owned files**

```powershell
git add src/tmall tests/test_tmall_pcdetail_adjust.py data/raw/tmall/pcdetail_adjust_1007839388129.json docs/superpowers/plans/2026-07-21-crawler-source-layout.md
git commit -m "refactor: organize Tmall direct crawler"
```
