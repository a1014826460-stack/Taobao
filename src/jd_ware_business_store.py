"""Compatibility entry point for the relocated JD wareBusiness crawler."""

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.jd.direct.ware_business import *  # noqa: F403
from src.jd.direct.ware_business import main


if __name__ == "__main__":
    raise SystemExit(main())
