from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Mapping
from urllib.parse import quote_plus

from .human_behavior import DelayPolicy, humanize_page
from .network_capture import build_network_record
from .risk_control import classify_risk, RiskDecision


def _maybe(v):
    return v if not inspect.isawaitable(v) else v

async def _await(v):
    return await v if inspect.isawaitable(v) else v


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for x in value.values():
            yield from _walk(x)
    elif isinstance(value, list):
        for x in value:
            yield from _walk(x)


def _first(d: Mapping[str, Any], *keys):
    lower = {str(k).lower(): v for k, v in d.items()}
    for key in keys:
        if key.lower() in lower and lower[key.lower()] not in (None, ""):
            return lower[key.lower()]
    return None


def _item_id(d: Mapping[str, Any]):
    v = _first(d, "item_id", "itemid", "itemId", "auctionId", "auction_id", "id")
    if isinstance(v, (str, int)) and str(v):
        return str(v)
    return None


@dataclass
class CrawlerConfig:
    db_path: str = "data/taobao_browser_crawler.db"
    account_source: Any = None
    platforms: tuple[str, ...] = ("taobao", "tmall")
    page_limit: int = 3
    delay_policy: DelayPolicy = field(default_factory=DelayPolicy)
    headless: bool = False
    retry_limit: int = 2
    keywords: list[str] | None = None
    search_only: bool = False


class BrowserCrawler:
    def __init__(self, repository, browser_pool, config: CrawlerConfig | None = None):
        self.repository = repository
        self.browser_pool = browser_pool
        self.config = config or CrawlerConfig()
        self._capture_tasks: list[asyncio.Task] = []
        # Register supplied accounts in repository when possible.
        for account in getattr(browser_pool, "accounts", {}).values():
            try:
                self.repository.upsert_account(account)
            except Exception:
                pass

    async def run_keywords(self, keywords: list[str]) -> dict:
        run_id = self.repository.create_run("keywords", {"keywords": keywords, "platforms": self.config.platforms, "page_limit": self.config.page_limit})
        for keyword in keywords:
            for platform in self.config.platforms:
                self.repository.enqueue_keyword(keyword, platform, self.config.page_limit, run_id)
        summary = await self.run_pending_tasks()
        self.repository.finish_run(run_id, summary)
        return summary

    async def run_pending_tasks(self) -> dict:
        completed = failed = paused = 0
        # Round-robin available account IDs; stop when no runnable task remains.
        account_ids = [str(a.get("account_id")) for a in self.repository.available_accounts()]
        if not account_ids:
            account_ids = list(getattr(self.browser_pool, "accounts", {}).keys())
        cursor = 0
        while account_ids:
            progressed = False
            for _ in range(len(account_ids)):
                account_id = account_ids[cursor % len(account_ids)]; cursor += 1
                task = self.repository.claim_next_task(account_id, datetime.now(timezone.utc).isoformat())
                if not task:
                    continue
                progressed = True
                try:
                    browser = await self.browser_pool.start_account(account_id)
                    if task.get("task_type") == "keyword":
                        await self.crawl_search_page(task, browser)
                    else:
                        await self.crawl_detail(task, browser)
                    self.repository.complete_task(task["task_id"])
                    completed += 1
                except _RiskDetected as exc:
                    self.repository.pause_account(account_id, exc.reason)
                    paused += 1
                    account_ids = [a for a in account_ids if a != account_id]
                    try:
                        await self.browser_pool.stop_account(account_id)
                    except Exception:
                        pass
                    if not account_ids:
                        break
                except Exception as exc:
                    attempts = int(task.get("attempts") or 1)
                    msg = f"{type(exc).__name__}: {exc}"[:500]
                    if attempts < self.config.retry_limit:
                        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
                        self.repository.fail_task(task["task_id"], msg, retry_at)
                    else:
                        self.repository.fail_task(task["task_id"], msg, None)
                        failed += 1
            if not progressed:
                break
        return {"completed": completed, "failed": failed, "paused_accounts": paused}

    def _search_url(self, platform: str, keyword: str, page_no: int) -> str:
        q = quote_plus(str(keyword))
        if platform.lower() == "tmall":
            return f"https://list.tmall.com/search_product.htm?q={q}&pageNo={page_no}"
        return f"https://s.taobao.com/search?q={q}&page={page_no}"

    def _detail_url(self, task: Mapping[str, Any]) -> str:
        if task.get("source_url"):
            return str(task["source_url"])
        item = quote_plus(str(task.get("item_id")))
        if str(task.get("platform", "taobao")).lower() == "tmall":
            return f"https://detail.tmall.com/item.htm?id={item}"
        return f"https://item.taobao.com/item.htm?id={item}"

    async def _navigate_capture(self, task: Mapping[str, Any], account_browser, url: str) -> list[dict]:
        page = account_browser.page
        records: list[dict] = []
        callbacks: list[Any] = []
        async def handle_response(response):
            try:
                req = getattr(response, "request", None)
                headers = await _await(response.headers() if callable(getattr(response, "headers", None)) else getattr(response, "headers", {}))
                body_attr = getattr(response, "body", None)
                body = await _await(body_attr() if callable(body_attr) else body_attr)
                if body is None and hasattr(response, "json"):
                    try:
                        body = json.dumps(await _await(response.json()), ensure_ascii=False)
                    except Exception:
                        body = None
                if isinstance(body, bytes): body = body.decode("utf-8", "replace")
                meta = {"run_id": task.get("run_id"), "account_id": account_browser.account_id,
                        "page_type": task.get("task_type"), "url": getattr(response, "url", ""),
                        "method": getattr(req, "method", "GET"), "status_code": getattr(response, "status", None),
                        "resource_type": getattr(req, "resource_type", "xhr"), "response_headers": headers}
                rec = build_network_record(meta, body)
                if rec.get("json_payload") is not None:
                    records.append(rec)
                    self.repository.save_network_record(rec)
                    self._persist_payload(task, rec["json_payload"], rec.get("json_type"))
            except Exception:
                return
        def callback(response):
            coro = handle_response(response)
            if inspect.isawaitable(coro):
                try:
                    loop = asyncio.get_running_loop(); self._capture_tasks.append(loop.create_task(coro))
                except RuntimeError:
                    pass
        if hasattr(page, "on"):
            page.on("response", callback); callbacks.append(callback)
        try:
            await _await(page.goto(url))
            await _await(page.wait_for_load_state("domcontentloaded")) if hasattr(page, "wait_for_load_state") else None
            await humanize_page(page, self.config.delay_policy)
            if self._capture_tasks:
                await asyncio.gather(*self._capture_tasks, return_exceptions=True); self._capture_tasks.clear()
            marker = await self._page_risk(page)
            if marker and RiskDecision.should_pause(marker):
                raise _RiskDetected(marker)
        finally:
            if hasattr(page, "off"):
                try: page.off("response", callback)
                except Exception: pass
        return records

    async def _page_risk(self, page):
        try: title = await _await(page.title()) if hasattr(page, "title") else ""
        except Exception: title = ""
        try: body = await _await(page.locator("body").inner_text()) if hasattr(page, "locator") else ""
        except Exception:
            try: body = await _await(page.inner_text("body")) if hasattr(page, "inner_text") else ""
            except Exception: body = ""
        return classify_risk(getattr(page, "url", ""), title, body, None)

    async def crawl_search_page(self, task, account_browser) -> None:
        await self._navigate_capture(task, account_browser, self._search_url(task["platform"], task["keyword"], int(task.get("page_no") or 1)))

    async def crawl_detail(self, task, account_browser) -> None:
        await self._navigate_capture(task, account_browser, self._detail_url(task))

    def _persist_payload(self, task: Mapping[str, Any], payload: Any, kind: str | None):
        platform = task.get("platform", "taobao"); keyword = task.get("keyword") or ""; page_no = int(task.get("page_no") or 1)
        item_task = task.get("item_id")
        # Search records: accept top-level or nested item arrays.
        dicts = list(_walk(payload))
        if kind == "search" or task.get("task_type") == "keyword":
            for d in dicts:
                iid = _item_id(d)
                if not iid: continue
                # Avoid treating a bare detail object as a search result.
                if not any(k in {str(x).lower() for x in d} for k in ("title", "price", "sales", "shop", "shopname", "rawtitle")): continue
                self.repository.upsert_search_product({"platform": platform, "keyword": keyword, "page_no": page_no, "item_id": iid,
                    "title": _first(d,"title","raw_title","name"), "price": _first(d,"price","viewprice"), "sales": _first(d,"sales","sold"),
                    "shop": _first(d,"shop","shopname","sellername"), "url": _first(d,"url","itemurl","detailurl"), "raw_json": d})
                try: self.repository.enqueue_detail(platform, iid, _first(d,"url","itemurl","detailurl"), task.get("run_id"))
                except Exception: pass
        # Detail payload and nested comment/seller data.
        if task.get("task_type") == "detail" or kind in ("product_detail", "comments", "seller"):
            iid = str(item_task or next((_item_id(d) for d in dicts if _item_id(d)), ""))
            if iid:
                if kind in ("product_detail", None, "unknown_json"):
                    self.repository.upsert_product_detail({"platform": platform, "item_id": iid, "title": _first(dicts[0],"title","name") if dicts else None, "description": payload, "raw_json": payload})
                for d in dicts:
                    cid = _first(d,"comment_id","commentid","id")
                    content = _first(d,"content","ratecontent","comment")
                    if cid and content is not None:
                        self.repository.upsert_comment({"platform": platform,"item_id": iid,"comment_id":str(cid),"rating":_first(d,"rating","score","rate"),"content":content,"author_redacted":_first(d,"author_redacted","author","usernick"),"raw_json":d})
                    sid = _first(d,"seller_id","sellerid","shopid")
                    if sid or _first(d,"shopname","shop_name"):
                        self.repository.upsert_seller({"platform": platform,"item_id":iid,"seller_id":sid,"shop_name":_first(d,"shopname","shop_name"),"level":_first(d,"level","sellerlevel"),"ratings":_first(d,"ratings","rating"),"raw_json":d})


class _RiskDetected(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)
