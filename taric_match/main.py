#!/usr/bin/env python3
"""taric-match CLI 入口"""

import sys

from taric_match.cli import main as cli_main


def main() -> int:
    """模块入口，供 `python -m taric_match.main` 使用。"""
    cli_main(standalone_mode=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
