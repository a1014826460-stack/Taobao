import asyncio, random, math
from dataclasses import dataclass
from typing import Callable

@dataclass
class DelayPolicy:
    min_seconds: float = 10.0
    max_seconds: float = 30.0
    seed: int | None = None
    sleep_func: Callable | None = None

    def __post_init__(self):
        self.validate()
        self._rng = random.Random(self.seed)

    def validate(self) -> None:
        if self.min_seconds < 0 or self.max_seconds < 0:
            raise ValueError("delay bounds must be non-negative")
        if self.min_seconds > self.max_seconds:
            raise ValueError("min_seconds cannot exceed max_seconds")

    def sample(self) -> float:
        return self._rng.uniform(self.min_seconds, self.max_seconds)

    async def wait(self, seconds: float | None = None) -> None:
        delay = self.sample() if seconds is None else float(seconds)
        if seconds is not None and (delay < 0 or delay > self.max_seconds):
            raise ValueError("wait seconds must be within 0..max_seconds")
        if self.sleep_func is not None:
            result = self.sleep_func(delay)
            if hasattr(result, "__await__"):
                await result
        else:
            await asyncio.sleep(delay)


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        return await value
    return value


async def humanize_page(page, policy: DelayPolicy, rng=None) -> None:
    """Add bounded human-like dwell, pointer movement, and scrolling.

    The page is never clicked; all coordinates are constrained to the viewport.
    Set ``policy.sleep_func`` to a no-op for tests.
    """
    await policy.wait()
    source_rng = rng or random.Random()
    vp = getattr(page, "viewport_size", None) or {}
    if callable(vp):
        vp = await _maybe_await(vp())
    width = max(1, int((vp or {}).get("width", 1280)))
    height = max(1, int((vp or {}).get("height", 720)))
    mouse = getattr(page, "mouse", None)
    if mouse is not None and hasattr(mouse, "move"):
        points = source_rng.randint(2, 5)
        for _ in range(points):
            x = source_rng.randint(0, max(0, width - 1)); y = source_rng.randint(0, max(0, height - 1))
            await _maybe_await(mouse.move(x, y, steps=source_rng.randint(3, 12)))
    # Determine whether scrolling is meaningful; short pages are not forced to scroll.
    total_height = None
    try:
        total_height = await _maybe_await(page.evaluate("() => document.documentElement.scrollHeight"))
    except Exception:
        total_height = None
    if total_height is None:
        return
    try:
        total_height = float(total_height)
    except (TypeError, ValueError, OverflowError):
        return
    if not math.isfinite(total_height) or total_height <= height * 1.15:
        return
    if mouse is None or not hasattr(mouse, "wheel"):
        return
    count = source_rng.randint(1, 4)
    max_delta = max(100, int(height * 0.85))
    for _ in range(count):
        delta = source_rng.randint(max(80, int(height * 0.35)), max_delta)
        await _maybe_await(mouse.wheel(0, delta))
        # Brief pause between natural scrolls, still injectable and bounded.
        await policy.wait(min(policy.max_seconds - policy.min_seconds, 0.25) if policy.max_seconds > policy.min_seconds else 0)
