import argparse
import json
import pathlib
import subprocess
import sys

from utils import diff_strings


def format_code(code_cells: dict[int, str]) -> list[str]:
    results = [
        subprocess.Popen(
            ["npx", "prettier", "--parser", "typescript"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in code_cells
    ]
    formatted_code = []
    for (cell_idx, code), process in zip(code_cells.items(), results):
        stdout, stderr = process.communicate(input=code)
        if process.returncode != 0:
            print(f"Prettier error in cell {cell_idx + 1}: {stderr}", file=sys.stderr)
            formatted_code.append(code_cells[cell_idx])
            continue
        formatted_code.append(stdout)
    return formatted_code


def process_notebook(path: pathlib.Path, check: bool = False) -> bool:
    print(f"Processing notebook: {path}")

    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    changed = False

    if nb.get("metadata", {}).get("language_info", {}).get("name") != "typescript":
        print(f"Skipping non-TypeScript notebook: {path}")
        return False

    code_cells = {
        n: "".join(cell["source"])
        for n, cell in enumerate(nb.get("cells", []))
        if cell.get("cell_type") == "code"
    }
    if not code_cells:
        print(f"No code cells found in {path}")
        return False

    formatted_blocks = format_code(code_cells)
    for (cell_idx, orginal), formatted in zip(code_cells.items(), formatted_blocks):
        if formatted != orginal:
            if check:
                print(diff_strings(orginal, formatted), file=sys.stderr)
                print(f"Cell {cell_idx + 1} in {path} is not formatted correctly.")
                continue
            changed = True
            nb["cells"][cell_idx]["source"] = formatted.splitlines(keepends=True)
            print(f"Formatted cell {cell_idx + 1} in {path}")
        else:
            print(f"Cell {cell_idx + 1} in {path} is already formatted.")
            continue

    if check:
        return changed

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1)
            f.write("\n")
        print(f"Formatted: {path}")
    else:
        print(f"No changes: {path}")

    return changed


def process_path(path: pathlib.Path, check: bool = False) -> bool:
    results: list[bool] = []
    if path.is_dir():
        for notebook in path.rglob("*.ipynb"):
            result = process_notebook(notebook, check=check)
            results.append(result)
    elif path.is_file() and path.suffix == ".ipynb":
        result = process_notebook(path, check=check)
        results.append(result)
    else:
        print(f"Invalid path: {path}", file=sys.stderr)
        return False
    return any(results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Format TypeScript code in Jupyter notebooks using Prettier."
    )
    parser.add_argument(
        "paths",
        help="Paths to Jupyter notebook or directory containing notebooks.",
        type=pathlib.Path,
        nargs="*",
        default=[pathlib.Path.cwd()],
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if notebooks are formatted without modifying them.",
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
