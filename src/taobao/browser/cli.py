"""Command-line entry point for the browser crawler."""
from __future__ import annotations
import argparse, asyncio
from pathlib import Path
from typing import Sequence
from .accounts import discover_accounts
from .human_behavior import DelayPolicy
from .crawler import CrawlerConfig, BrowserCrawler
from .repository import BrowserCrawlerRepository
from .browser_pool import BrowserPool


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="taobao-browser-crawler", description="Capture Taobao/Tmall search and detail JSON")
    mode = p.add_argument_group("input")
    mode.add_argument("--keyword", action="append", default=[], help="search keyword (repeatable)")
    mode.add_argument("--from-tasks", action="store_true", help="consume pending tasks from SQLite")
    p.add_argument("--pages", type=int, default=3, help="search pages per keyword (default: 3, max: 3)")
    cookies = p.add_mutually_exclusive_group()
    cookies.add_argument("--cookie-file", type=Path, help="single cookie file/account")
    cookies.add_argument("--cookie-dir", type=Path, help="directory containing cookie files")
    p.add_argument("--db", type=Path, default=Path("data/taobao_browser_crawler.db"), help="SQLite database path")
    p.add_argument("--headless", action="store_true", help="run browsers headlessly (visible by default)")
    p.add_argument("--min-delay", type=float, default=10.0)
    p.add_argument("--max-delay", type=float, default=30.0)
    p.add_argument("--search-only", action="store_true", help="do not process detail tasks")
    p.add_argument("--retry-limit", type=int, default=2)
    p.add_argument("--version", action="version", version="taobao-browser-crawler 0.1")
    return p


def config_from_args(args: argparse.Namespace) -> CrawlerConfig:
    pages = int(args.pages)
    if pages < 1 or pages > 3:
        raise ValueError("--pages must be between 1 and 3")
    retry = int(args.retry_limit)
    if retry < 1:
        raise ValueError("--retry-limit must be positive")
    policy = DelayPolicy(float(args.min_delay), float(args.max_delay))
    source = None
    if getattr(args, "cookie_file", None):
        source = args.cookie_file
    elif getattr(args, "cookie_dir", None):
        source = args.cookie_dir
    return CrawlerConfig(db_path=str(args.db), account_source=source,
        platforms=("taobao", "tmall"), page_limit=pages, delay_policy=policy,
        headless=bool(args.headless), retry_limit=retry,
        keywords=list(args.keyword or []), search_only=bool(args.search_only))


def _accounts_from_args(args):
    if args.cookie_file:
        return discover_accounts(Path("."), single_cookie_file=args.cookie_file)
    if args.cookie_dir:
        return discover_accounts(args.cookie_dir)
    # A conventional accounts directory is optional; caller gets a clear error
    # if it does not exist or contains no cookie files.
    default = Path("accounts")
    return discover_accounts(default) if default.exists() else []


async def _run(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    repo = BrowserCrawlerRepository(config.db_path)
    accounts = _accounts_from_args(args)
    if not accounts:
        repo.close()
        raise ValueError("no cookie accounts found; provide --cookie-file or --cookie-dir")
    pool = BrowserPool(accounts, headless=config.headless)
    crawler = BrowserCrawler(repo, pool, config)
    try:
        if args.from_tasks:
            summary = await crawler.run_pending_tasks()
        elif args.keyword:
            summary = await crawler.run_keywords(args.keyword)
        else:
            raise ValueError("provide at least one --keyword or use --from-tasks")
        # Failed or paused work is an uncompleted run; callers can resume later.
        return 1 if summary.get("failed", 0) else 0
    finally:
        await pool.close_all()
        repo.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
        return asyncio.run(_run(args))
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
