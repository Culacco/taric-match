#!/usr/bin/env python3
"""taric-match CLI 入口"""

import sys

import click

from taric_match.cli import main as cli_main


def main() -> int:
    """模块入口，供 `python -m taric_match.main` 使用。"""
    try:
        cli_main(standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.Abort:
        click.echo("Aborted!", err=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
