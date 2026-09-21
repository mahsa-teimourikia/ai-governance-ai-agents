#!/usr/bin/env python3
"""Execute selected credential-free notebooks as plain Python code cells.

Audited notebooks avoid notebook-only magics, top-level await, and hidden state,
so this lightweight runner can validate their canonical offline path in CI.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).parents[1]


def execute_notebook(path: Path) -> int:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("nbformat") != 4 or not isinstance(document.get("cells"), list):
        raise ValueError(f"{path}: expected a valid nbformat 4 document")

    namespace = {"__name__": "__main__"}
    executed = 0
    for index, cell in enumerate(document["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        exec(compile(source, f"{path.name}:cell-{index}", "exec"), namespace)
        executed += 1
    return executed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="+", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)

    for requested in args.notebooks:
        path = requested if requested.is_absolute() else ROOT / requested
        count = execute_notebook(path.resolve())
        print(f"Executed {count} code cells: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
