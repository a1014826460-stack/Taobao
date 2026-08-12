from __future__ import annotations

import re
from typing import Optional


def classify_risk(url: str, title: str, body_text: str, status_code: int | None) -> str | None:
    """Return a stable risk marker for an account-level pause, or ``None``.

    Matching is intentionally conservative and combines URL/title/body/status clues.
    """
    u = (url or "").lower(); t = (title or "").lower(); b = (body_text or "").lower()
    text = " ".join((u, t, b))
    if status_code in (401,):
        return "login_expired"
    if status_code == 403:
        return "forbidden"
    if status_code == 429:
        return "rate_limited"
    if any(k in text for k in ("login", "登录", "请先登录", "session expired", "登录已过期", "未登录")):
        return "login_expired"
    if any(k in text for k in ("captcha", "verify", "challenge", "滑块", "安全验证", "验证身份", "robot check", "人机验证")):
        return "challenge"
    if any(k in text for k in ("too many requests", "rate limit", "访问频繁", "请求过于频繁", "限流", "稍后再试")):
        return "rate_limited"
    if any(k in text for k in ("forbidden", "access denied", "无权访问", "访问被拒绝")):
        return "forbidden"
    return None


class RiskDecision:
    """Small helper to map a risk marker to account pause behavior."""
    PAUSE_MARKERS = {"login_expired", "challenge", "rate_limited", "forbidden"}

    @classmethod
    def should_pause(cls, marker: Optional[str]) -> bool:
        return marker in cls.PAUSE_MARKERS
