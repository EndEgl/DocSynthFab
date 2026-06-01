# src/ai1_gen/cli/cli.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# Direct-run launcher:
#   python src/ai1_gen/cli/cli.py --config configs/default.yaml --pages 100 --workers 4
#
# Package launcher:
#   python -m ai1_gen.cli --config configs/default.yaml --pages 100 --workers 4

from __future__ import annotations

import sys
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
_SRC_ROOT = _THIS_FILE.parents[2]

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from ai1_gen.cli.main import main


if __name__ == "__main__":
    main()