import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import NamedTuple

from utils import execute


class CompileResult(NamedTuple):
    line: int
    column: int
    message: str
    rule_id: str


def parse_lint_output(line: str) -> CompileResult:
    match = re.match(r"^\s*(\S+)\((\d+),(\d+)\):\s+error\s+(.*?):\s+(.*)", line)
    if match:
        _, row, col, rule_id, message = match.groups()
        return CompileResult(int(row), int(col), message, rule_id)
    return CompileResult(0, 0, "", "")


def compile_cells(codes: list[str]) -> int:
    tmp_path = pathlib.Path.cwd() / ".temp"
    tmp_path.mkdir(parents=True, exist_ok=True)

    separator = "\n\n// --- CELL SPLIT ---\n\n"
    joined_code = separator.join(codes)
    code_lines = joined_code.splitlines()

    def find_cell_from_global_line(global_line: int) -> tuple[int, int]:
        line_count = 0
        for i, code in enumerate(codes):
            line_count += len(code.splitlines()) + 4
            if global_line < line_count:
                return i, line_count - len(code.splitlines()) - 4
        return -1, -1

    with tempfile.NamedTemporaryFile(
        suffix=".ts", mode="w+", encoding="utf-8", dir=tmp_path, delete=True
    ) as tmp:
        tmp.write(joined_code)
        tmp.flush()
        tmp_filepath = tmp.name

        args = [
            "tsc",
            tmp_filepath,
            "--noEmit",
            "--target",
            "es2017",
            "--module",
            "nodenext",
        ]

        return_code = 0
        lines: list[CompileResult] = []
        try:
            for line in execute(args):
                parsed_line = parse_lint_output(line.strip())
                if parsed_line.line and parsed_line.column:
                    lines.append(parsed_line)
                    cell_index, start_row = find_cell_from_global_line(parsed_line.line)
                    row, col = parsed_line.line - start_row, parsed_line.column
                    print(parsed_line)
                    print(
                        f"Cell {cell_index + 1}, Line {row}, Column {col}: {parsed_line.message}"
                    )
                    print(f"{code_lines[parsed_line.line - 1]}\n")
        except subprocess.CalledProcessError as e:
            return_code = e.returncode
            print(f"tsc failed with return code: {return_code}", file=sys.stderr)

    return return_code


def process_notebook(path: pathlib.Path) -> bool:
    print(f"Processing notebook: {path}")

    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    if nb.get("metadata", {}).get("language_info", {}).get("name") != "typescript":
        print(f"Skipping non-TypeScript notebook: {path}")
        return False

    code_cells = {
        n: "".join(cell["source"])
        for n, cell in enumerate(nb.get("cells", []))
        if cell.get("cell_type") == "code"
    }

    if not code_cells:
        print(f"No code cells to compile in {path}")
        return False

    return_code = compile_cells(list(code_cells.values()))
    changed = return_code != 0

    if changed:
        print(f"Changes detected in {path}.")

    return changed


def process_path(path: pathlib.Path) -> bool:
    """Process a single path (file or directory) for linting TypeScript cells."""
    results: list[bool] = []
    if path.is_dir():
        notebooks = list(path.rglob("*.ipynb"))
        for notebook in notebooks:
            results.append(process_notebook(notebook))
    elif path.is_file() and path.suffix == ".ipynb":
        results.append(process_notebook(path))
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
    args = parser.parse_args()
    paths = args.paths

    results: list[bool] = []
    for path in paths:
        if not path.exists():
            print(f"Path does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        results.append(process_path(path))

    if any(results):
        print("Some notebooks were formatted.", file=sys.stderr)
        sys.exit(1)
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
