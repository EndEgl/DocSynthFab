# src/ai1_gen/__main__.py
from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) > 1:
        from ai1_gen.cli import main as cli_main
        cli_main()
    else:
        from ai1_gen.gui import launch_gui
        raise SystemExit(launch_gui())


if __name__ == "__main__":
    main()