"""End-to-end JD API caller — generates h5st via Playwright, then calls the API.

Usage:
  python src/tools/call_jd_api.py search --keyword "穿戴跳蛋" --page 2
  python src/tools/call_jd_api.py detail --sku 10147072608797
  python src/tools/call_jd_api.py search --keyword "穿戴跳蛋" --cookie-file cookies.txt
"""

import argparse
import json
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
H5ST_SCRIPT = PROJECT_ROOT / "tools" / "js-env-analyzer" / "generate-h5st-playwright.js"

# ---- API endpoint per function ----
API_PATH = "https://api.m.jd.com/api"


def load_cookie(cookie_arg: str | None, cookie_file: str | None) -> str | None:
    if cookie_arg:
        return cookie_arg
    if cookie_file:
        p = Path(cookie_file)
        if not p.exists():
            raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
        return p.read_text(encoding="utf-8").strip()
    # try default locations
    for default in [PROJECT_ROOT / "cookies.txt", PROJECT_ROOT / "password.env"]:
        if default.exists():
            content = default.read_text(encoding="utf-8").strip()
            if "=" in content and ";" in content:
                return content
    return None


def generate_h5st(
    appid: str,
    function_id: str,
    body: dict,
    cookie: str | None = None,
    extra_params: dict | None = None,
) -> dict:
    """Call generate-h5st-playwright.js and return the JSON result."""
    params = {
        "appid": appid,
        "functionId": function_id,
        "body": json.dumps(body, ensure_ascii=False, separators=(",", ":")),
        "client": "pc",
        "clientVersion": "1.0.0",
    }
    if extra_params:
        params.update(extra_params)

    cmd = ["node", str(H5ST_SCRIPT), "--params", json.dumps(params, ensure_ascii=False)]
    if cookie:
        cmd.insert(2, cookie)
        cmd.insert(2, "--cookie")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(PROJECT_ROOT),
    )

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        # Check stdout for JSON even on error exit
        for line in (proc.stdout or "").strip().split("\n"):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
        raise RuntimeError(f"h5st generation failed:\nSTDERR: {stderr}\nSTDOUT: {proc.stdout}")

    return json.loads(proc.stdout.strip())


def call_api(
    appid: str,
    function_id: str,
    body: dict,
    h5st_result: dict,
    cookie: str | None = None,
    extra_params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """Make the JD API call with the generated h5st."""
    h5st = h5st_result["h5st"]
    t = h5st_result["t"]

    url_params = {
        "appid": appid,
        "functionId": function_id,
        "body": json.dumps(body, ensure_ascii=False, separators=(",", ":")),
        "client": "pc",
        "clientVersion": "1.0.0",
        "t": str(t),
        "h5st": h5st,
    }
    if extra_params:
        url_params.update(extra_params)

    url = f"{API_PATH}?{urllib.parse.urlencode(url_params, quote_via=urllib.parse.quote)}"

    req_headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36",
        "Referer": "https://www.jd.com/",
        "Origin": "https://www.jd.com",
    }
    if cookie:
        req_headers["Cookie"] = cookie
    if headers:
        req_headers.update(headers)

    request = urllib.request.Request(url, headers=req_headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, timeout=30, context=ctx) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "body": body[:2000]}


def cmd_search(args):
    body = {
        "enc": "utf-8",
        "pvid": args.pvid or "bcd8e9b58b1e4b1fbf3092d226e060e1",
        "area": args.area or "19_1659_37264_37360",
        "page": args.page,
        "mode": "",
        "concise": False,
        "hoverPictures": True,
        "newAdvRepeat": True,
        "mixerParam": True,
        "new_interval": True,
        "s": 23,
    }
    extra_params = {
        "keyword": args.keyword,
        "uuid": args.uuid or "17854075363601606079882",
        "loginType": "3",
        "cthr": "1",
    }

    cookie = load_cookie(args.cookie, args.cookie_file)
    if not cookie:
        print("Warning: no cookie provided. API may trigger captcha.", file=sys.stderr)

    h5st = generate_h5st(
        appid="search-pc-java",
        function_id="pc_search_searchWare",
        body=body,
        cookie=cookie,
        extra_params=extra_params,
    )

    resp = call_api(
        appid="search-pc-java",
        function_id="pc_search_searchWare",
        body=body,
        h5st_result=h5st,
        cookie=cookie,
        extra_params=extra_params,
    )

    print(json.dumps(resp, ensure_ascii=False, indent=2))


def cmd_detail(args):
    body = {
        "skuId": args.sku,
        "area": args.area or "19_1659_0_0",
        "num": "1",
        "clientSource": "PC",
        "sfTime": "1,0,0",
    }

    cookie = load_cookie(args.cookie, args.cookie_file)
    if not cookie:
        print("Warning: no cookie provided. API may trigger captcha.", file=sys.stderr)

    h5st = generate_h5st(
        appid="pc-item-soa",
        function_id="pc_detailpage_wareBusiness",
        body=body,
        cookie=cookie,
        extra_params={"uuid": args.uuid or "17854075363601606079882", "loginType": "3"},
    )

    resp = call_api(
        appid="pc-item-soa",
        function_id="pc_detailpage_wareBusiness",
        body=body,
        h5st_result=h5st,
        cookie=cookie,
        extra_params={"uuid": args.uuid or "17854075363601606079882", "loginType": "3"},
    )

    print(json.dumps(resp, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="JD API caller with h5st generation")
    sub = parser.add_subparsers(dest="command")

    # ---- search ----
    sp = sub.add_parser("search", help="Call JD search API")
    sp.add_argument("--keyword", required=True, help="Search keyword")
    sp.add_argument("--page", type=int, default=1, help="Page number")
    sp.add_argument("--area", default="", help="Area code e.g. 19_1659_37264_37360")
    sp.add_argument("--pvid", default="", help="Page view ID")
    sp.add_argument("--uuid", default="", help="UUID")
    sp.add_argument("--cookie", default=None, help="Cookie string")
    sp.add_argument("--cookie-file", default=None, help="Path to cookie file")

    # ---- detail ----
    dp = sub.add_parser("detail", help="Call JD product detail API")
    dp.add_argument("--sku", required=True, help="SKU/Item ID")
    dp.add_argument("--area", default="19_1659_0_0", help="Area code")
    dp.add_argument("--uuid", default="", help="UUID")
    dp.add_argument("--cookie", default=None, help="Cookie string")
    dp.add_argument("--cookie-file", default=None, help="Path to cookie file")

    args = parser.parse_args()
    if args.command == "search":
        cmd_search(args)
    elif args.command == "detail":
        cmd_detail(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
