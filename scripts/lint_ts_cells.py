import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import re
from typing import NamedTuple

from utils import execute


class LintResult(NamedTuple):
    """Lint result for a TypeScript cell."""

    line: int
    column: int
    message: str
    rule_id: str


def parse_lint_output(line: str) -> LintResult:
    """Parse the output from ESLint to get the line and column numbers."""
    match = re.match(r"^\s*(\d+):(\d+)\s+error\s+(.*)", line)
    if match:
        row, col, message = match.groups()
        return LintResult(int(row), int(col), message, "")
    return LintResult(0, 0, "", "")


def lint_cells(codes: list[str], check: bool = False) -> tuple[list[str], int]:
    """Lint (and optionally fix) a list of TypeScript code cells using ESLint."""
    tmp_path = pathlib.Path.cwd() / ".temp"
    tmp_path.mkdir(parents=True, exist_ok=True)

    separator = "\n\n// --- CELL SPLIT ---\n\n"
    joined_code = separator.join(codes)
    code_lines = joined_code.splitlines()

    with tempfile.NamedTemporaryFile(
        suffix=".ts", mode="w+", encoding="utf-8", dir=tmp_path, delete=False
    ) as tmp:
        tmp.write(joined_code)
        tmp.flush()
        tmp_filepath = tmp.name

    args = ["npx", "eslint", tmp_filepath]
    if not check:
        args += ["--fix"]

    def find_cell_from_global_line(global_line: int) -> tuple[int, int]:
        """Find the cell index from the global line number."""
        line_count = 0
        for i, code in enumerate(codes):
            line_count += len(code.splitlines()) + 4
            if global_line < line_count:
                return i, line_count - len(code.splitlines()) - 4
        return -1, -1

    return_code = 0
    lines: list[LintResult] = []
    try:
        for line in execute(args):
            parsed_line = parse_lint_output(line)
            if parsed_line.line and parsed_line.column:
                lines.append(parsed_line)
                cell_index, start_row = find_cell_from_global_line(parsed_line.line)
                row, col = parsed_line.line - start_row, parsed_line.column
                print(
                    f"Cell {cell_index + 1}, Line {row}, Column {col}: {parsed_line.message}"
                )
                print(code_lines[parsed_line.line - 1])
            else:
                print(line.strip())
    except subprocess.CalledProcessError as e:
        return_code = e.returncode
        print(f"ESLint failed with return code: {return_code}", file=sys.stderr)

    with open(tmp_filepath, "r", encoding="utf-8") as f:
        fixed_code = f.read()

    fixed_cells = fixed_code.split(separator)
    return fixed_cells, return_code


def process_notebook(path: pathlib.Path, check: bool = False) -> bool:
    print(f"Processing notebook: {path}")

    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    if nb.get("metadata", {}).get("language_info", {}).get("name") != "typescript":
        print(f"Skipping non-TypeScript notebook: {path}")
        return False

    cell_indices = []
    code_cells = []

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            code = "".join(cell["source"])
            code_cells.append(code)
            cell_indices.append(i)
        else:
            print(f"Skipping non-code cell {i + 1} in {path}")

    if not code_cells:
        print(f"No code cells to lint in {path}")
        return False

    fixed_cells, return_code = lint_cells(code_cells, check=check)
    changed = False

    for idx, fixed_code in zip(cell_indices, fixed_cells):
        original_code = "".join(nb["cells"][idx]["source"])
        if fixed_code != original_code or return_code != 0:
            changed = True
            if not check:
                nb["cells"][idx]["source"] = fixed_code.splitlines(keepends=True)
                print(f"Linted cell {idx + 1} in {path}")
                continue
        else:
            print(f"Cell {idx + 1} in {path} is already linted.")

    if check:
        return changed

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1)
            f.write("\n")
        print(f"Linted and updated: {path}")
    else:
        print(f"No changes: {path}")

    return changed


def process_path(path: pathlib.Path, check: bool = False) -> bool:
    """Process a single path (file or directory) for linting TypeScript cells."""
    results: list[bool] = []
    if path.is_dir():
        notebooks = list(path.rglob("*.ipynb"))
        for notebook in notebooks:
            results.append(process_notebook(notebook, check=check))
    elif path.is_file() and path.suffix == ".ipynb":
        results.append(process_notebook(path, check=check))
    else:
        print(f"Invalid path: {path}", file=sys.stderr)
        return False
    return any(results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint TypeScript code in Jupyter notebooks using ESLint."
    )
    parser.add_argument(
        "paths",
        help="Path to a Jupyter notebook or directory containing notebooks.",
        type=pathlib.Path,
        nargs="*",
        default=[pathlib.Path.cwd()],
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for lint issues without modifying files.",
    )
    args = parser.parse_args()
    paths = args.paths

    results: list[bool] = []
    for path in paths:
        if not path.exists():
            print(f"Path does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        results.append(process_path(path, check=args.check))

    if any(results):
        print("Some notebooks were formatted.", file=sys.stderr)
        sys.exit(1)
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
