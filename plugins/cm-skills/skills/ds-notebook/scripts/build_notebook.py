#!/usr/bin/env python3
"""Deterministically (re)build a Jupyter notebook from per-cell source files.

Why: for structural edits, keep each cell's source in its own file and rebuild
the .ipynb by swapping cells into a base notebook, clearing all outputs, and
validating (JSON parses + every code cell compiles) BEFORE a kernel runs. This
keeps unchanged cells byte-identical across versions (clean diffs) and catches
syntax errors instantly. It's the workflow used to iterate a scoring notebook
across many versions without drift.

Two modes:

1. FROM A BASE (recommended for vN -> vN+1): copy an existing notebook, replace
   specific cells by index from files, clear outputs, write the new notebook.

2. FROM SCRATCH: build a notebook from an ordered list of (type, file) cells.

Edit the CONFIG block below, then run:  python build_notebook.py

Cell source files are plain text (.py for code, .md for markdown). Their content
becomes the cell verbatim — do NOT wrap code in ``` fences.
"""
import ast
import json
import sys

# ─── CONFIG — edit this ───────────────────────────────────────────────────────
MODE = "from_base"                       # "from_base" | "from_scratch"

# from_base:
BASE_NB = "notebooks/myproject_v1.ipynb"
OUT_NB  = "notebooks/myproject_v2.ipynb"
# index -> source file; the file's content replaces that cell's source
SWAPS = {
    # 0:  "cells/cell00_intro.md",
    # 4:  "cells/cell04_config.py",
}
# optional guards: assert a cell is what you think before replacing (substring)
GUARDS = {
    # 4: "TABLES = {",
}

# from_scratch: ordered list of (cell_type, source_file)
SCRATCH_CELLS = [
    # ("markdown", "cells/cell00_intro.md"),
    # ("code",     "cells/cell01_imports.py"),
]
# ──────────────────────────────────────────────────────────────────────────────


def load_lines(path):
    with open(path) as f:
        return f.read().splitlines(keepends=True)


def clear_and_validate(nb):
    bad = 0
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        cell["outputs"] = []
        cell["execution_count"] = None
        try:
            ast.parse("".join(cell["source"]))
        except SyntaxError as e:
            bad += 1
            print(f"  SYNTAX ERROR in cell {i}: {e}", file=sys.stderr)
    if bad:
        raise SystemExit(f"{bad} code cell(s) failed to compile — not writing.")


def build_from_base():
    nb = json.load(open(BASE_NB))
    for idx, sub in (GUARDS or {}).items():
        src = "".join(nb["cells"][idx]["source"])
        assert sub in src, f"guard failed: cell {idx} does not contain {sub!r}"
    for idx, path in SWAPS.items():
        nb["cells"][idx]["source"] = load_lines(path)
    clear_and_validate(nb)
    json.dump(nb, open(OUT_NB, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {OUT_NB} | {len(nb['cells'])} cells | swapped {len(SWAPS)} | all code compiles")


def build_from_scratch():
    nb = {
        "cells": [],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    for ctype, path in SCRATCH_CELLS:
        cell = {"cell_type": ctype, "metadata": {}, "source": load_lines(path)}
        if ctype == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        nb["cells"].append(cell)
    clear_and_validate(nb)
    json.dump(nb, open(OUT_NB, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {OUT_NB} | {len(nb['cells'])} cells | all code compiles")


if __name__ == "__main__":
    (build_from_base if MODE == "from_base" else build_from_scratch)()
