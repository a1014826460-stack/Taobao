"""Isolated Camoufox/Playwright browser instances per account."""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .accounts import AccountRecord, CookieRecord


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


async def _default_browser_factory(**kwargs: Any) -> Any:
    """Launch Camoufox lazily, keeping imports optional for unit tests."""
    try:
        from camoufox.async_api import AsyncCamoufox
    except ImportError as exc:  # pragma: no cover - only exercised without optional dep
        raise RuntimeError("Camoufox is not installed; install camoufox[all]") from exc
    manager = AsyncCamoufox(**kwargs)
    if hasattr(manager, "__aenter__"):
        browser = await manager.__aenter__()
        try:
            setattr(browser, "_camoufox_manager", manager)
        except Exception:
            pass
        return browser
    return await _maybe_await(manager)


@dataclass
class AccountBrowser:
    account_id: str
    browser: Any
    context: Any
    page: Any

    async def install_cookies(self, cookies: Iterable[CookieRecord | dict[str, Any]]) -> None:
        values = []
        for cookie in cookies:
            if isinstance(cookie, CookieRecord):
                values.append(cookie.as_playwright())
            elif isinstance(cookie, dict):
                values.append(dict(cookie))
            else:
                raise TypeError("cookies must contain CookieRecord or mapping values")
        if values:
            await _maybe_await(self.context.add_cookies(values))

    async def close(self) -> None:
        # Context is account-specific; close it before browser/manager.
        close_context = getattr(self.context, "close", None)
        if close_context:
            try:
                await _maybe_await(close_context())
            except Exception:
                pass
        manager = getattr(self.browser, "_camoufox_manager", None)
        close_browser = getattr(self.browser, "close", None)
        if close_browser:
            try:
                await _maybe_await(close_browser())
            except Exception:
                pass
        if manager is not None and hasattr(manager, "__aexit__"):
            try:
                await manager.__aexit__(None, None, None)
            except Exception:
                pass


class BrowserPool:
    """Manage one isolated browser/context for each account.

    ``browser_factory`` is injectable for tests and should accept ``headless``,
    optional ``proxy`` and ``locale`` keyword arguments, returning a browser
    object exposing ``new_context``.
    """

    def __init__(self, accounts: Iterable[AccountRecord | dict[str, Any]], headless: bool = False,
                 proxy: Any = None, locale: str = "zh-CN", max_instances: int | None = None,
                 browser_factory: Callable[..., Any] | None = None) -> None:
        self.accounts: dict[str, AccountRecord | dict[str, Any]] = {
            (a.account_id if isinstance(a, AccountRecord) else str(a["account_id"])): a for a in accounts
        }
        self.headless = bool(headless)
        self.proxy, self.locale, self.max_instances = proxy, locale, max_instances
        self.browser_factory = browser_factory or _default_browser_factory
        self.instances: dict[str, AccountBrowser] = {}

    async def start_account(self, account_id: str) -> AccountBrowser:
        if account_id not in self.accounts:
            raise KeyError(f"unknown account: {account_id}")
        if account_id in self.instances:
            return self.instances[account_id]
        if self.max_instances is not None and len(self.instances) >= self.max_instances:
            raise RuntimeError("maximum browser instances reached")
        launch_kwargs: dict[str, Any] = {"headless": self.headless}
        if self.proxy is not None:
            launch_kwargs["proxy"] = self.proxy
        browser = await _maybe_await(self.browser_factory(**launch_kwargs))
        context_kwargs = {"locale": self.locale}
        context = await _maybe_await(browser.new_context(**context_kwargs))
        page = await _maybe_await(context.new_page())
        account_browser = AccountBrowser(account_id, browser, context, page)
        self.instances[account_id] = account_browser
        return account_browser

    async def get(self, account_id: str) -> AccountBrowser | None:
        return self.instances.get(account_id)

    async def stop_account(self, account_id: str) -> None:
        instance = self.instances.pop(account_id, None)
        if instance is not None:
            await instance.close()

    async def close_all(self) -> None:
        for account_id in list(self.instances):
            await self.stop_account(account_id)

