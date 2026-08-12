"""Cookie and account discovery helpers for isolated browser contexts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CookieRecord:
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: int | float | None = None
    http_only: bool = False
    secure: bool = False
    same_site: str | None = None

    def as_playwright(self) -> dict[str, Any]:
        """Return a Playwright-compatible cookie dictionary."""
        result: dict[str, Any] = {"name": self.name, "value": self.value, "domain": self.domain, "path": self.path}
        if self.expires is not None:
            result["expires"] = self.expires
        if self.http_only:
            result["httpOnly"] = True
        if self.secure:
            result["secure"] = True
        if self.same_site:
            result["sameSite"] = self.same_site
        return result


@dataclass(frozen=True)
class AccountRecord:
    account_id: str
    cookie_source: str
    status: str = "active"
    pause_reason: str | None = None


def _default_domain(source: str) -> str:
    return ".tmall.com" if "tmall" in source.lower() else ".taobao.com"


def _cookie(name: Any, value: Any, source: str, **kwargs: Any) -> CookieRecord:
    if not isinstance(name, str) or not name.strip() or not isinstance(value, str):
        raise ValueError("cookie entries require non-empty string name and string value")
    domain = kwargs.get("domain") or _default_domain(source)
    if not isinstance(domain, str):
        raise ValueError("cookie domain must be a string")
    path = kwargs.get("path", "/") or "/"
    if not isinstance(path, str):
        raise ValueError("cookie path must be a string")
    expires = kwargs.get("expires")
    if expires is not None and (isinstance(expires, bool) or not isinstance(expires, (int, float))):
        raise ValueError("cookie expires must be numeric")
    same_site = kwargs.get("sameSite", kwargs.get("same_site"))
    if same_site is not None and same_site not in {"Strict", "Lax", "None"}:
        raise ValueError("invalid sameSite value")
    return CookieRecord(name=name.strip(), value=value, domain=domain, path=path, expires=expires,
                        http_only=bool(kwargs.get("httpOnly", kwargs.get("http_only", False))),
                        secure=bool(kwargs.get("secure", False)), same_site=same_site)


def _parse_json(data: Any, source: str) -> list[CookieRecord]:
    if isinstance(data, dict):
        data = data.get("cookies")
    if not isinstance(data, list):
        raise ValueError("JSON cookie input must be an array or an object with cookies array")
    result = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("cookie entry must be an object")
        params = dict(entry)
        name, value = params.pop("name", None), params.pop("value", None)
        result.append(_cookie(name, value, source, **params))
    return result


def parse_cookie_text(text: str, source: str) -> list[CookieRecord]:
    """Parse semicolon, Netscape, or browser-export JSON cookie text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = text.lstrip("\ufeff")
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            return _parse_json(json.loads(stripped), source)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON cookie input") from exc

    lines = [line.strip("\r") for line in text.splitlines() if line.strip()]
    # Netscape format is tab-delimited and has seven columns.
    if any("\t" in line for line in lines if not line.lstrip().startswith("#")):
        result: list[CookieRecord] = []
        for line in lines:
            if line.lstrip().startswith("#") and not line.startswith("#HttpOnly_"):
                continue
            fields = line.split("\t")
            if line.startswith("#HttpOnly_"):
                fields[0] = fields[0][1:]
            if len(fields) != 7:
                raise ValueError("malformed Netscape cookie entry")
            domain, _, path, secure, expires, name, value = fields
            try:
                exp = int(expires)
            except ValueError as exc:
                raise ValueError("invalid Netscape expiry") from exc
            result.append(_cookie(name, value, source, domain=domain, path=path, secure=secure.upper() == "TRUE", expires=exp,
                                  httpOnly=line.startswith("#HttpOnly_")))
        return result

    # Cookie header style: name=value; name2=value2
    result = []
    for item in stripped.split(";"):
        if "=" not in item:
            raise ValueError("malformed semicolon cookie entry")
        name, value = item.split("=", 1)
        result.append(_cookie(name.strip(), value.strip(), source))
    return result


def discover_accounts(cookie_dir: Path, single_cookie_file: Path | None = None) -> list[AccountRecord]:
    """Discover deterministic account IDs from cookie file stems."""
    if single_cookie_file is not None:
        paths = [Path(single_cookie_file)]
    else:
        directory = Path(cookie_dir)
        if not directory.is_dir():
            return []
        paths = sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".json", ".cookies"}), key=lambda p: p.name.lower())
    result = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        result.append(AccountRecord(account_id=path.stem, cookie_source=str(path)))
    return result


def redact_cookie_value(value: str) -> str:
    """Return a deterministic digest that cannot reveal the cookie value."""
    if not value:
        return "<redacted>"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"<redacted:{digest}>"

