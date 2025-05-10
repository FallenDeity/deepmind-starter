import argparse
import json
import pathlib
import subprocess
import sys


def format_code(code: str) -> str:
    """Format a TypeScript code string using Prettier via subprocess."""
    result = subprocess.run(
        ["npx", "prettier", "--parser", "typescript"],
        input=code.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        print("Prettier error:", result.stderr.decode(), file=sys.stderr)
        return code
    return result.stdout.decode()


def process_notebook(path: pathlib.Path, check: bool = False) -> bool:
    print(f"Processing notebook: {path}")

    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    changed = False

    if nb.get("metadata", {}).get("language_info", {}).get("name") != "typescript":
        print(f"Skipping non-TypeScript notebook: {path}")
        return False

    for n, cell in enumerate(nb.get("cells", []), start=1):
        if cell.get("cell_type") == "code":
            original_code = "".join(cell["source"])
            formatted = format_code(original_code)
            if formatted != original_code:
                if check:
                    print(f"Cell {n} in {path} needs formatting.")
                    continue
                cell["source"] = formatted.splitlines(keepends=True)
                changed = True
                print(f"Formatted cell {n} in {path}")
            else:
                print(f"Cell {n} in {path} is already formatted.")
                continue
        else:
            print(f"Skipping non-code cell {n} in {path}")
            continue

    if check:
        return changed

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1)
        print(f"Formatted: {path}")
    else:
        print(f"No changes: {path}")

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Format TypeScript code in Jupyter notebooks using Prettier."
    )
    parser.add_argument(
        "path",
        help="Path to a Jupyter notebook or directory containing notebooks.",
        type=pathlib.Path,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if notebooks are formatted without modifying them.",
    )
    args = parser.parse_args()
    path = args.path.resolve()

    results: list[bool] = []
    if not path.exists():
        print(f"Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)
    if path.is_dir():
        for notebook in path.rglob("*.ipynb"):
            result = process_notebook(notebook, check=args.check)
            results.append(result)
    elif path.is_file() and path.suffix == ".ipynb":
        result = process_notebook(path, check=args.check)
        results.append(result)
    else:
        print(f"Invalid path: {path}", file=sys.stderr)
        sys.exit(1)

    if any(results):
        print("Some notebooks need formatting.", file=sys.stderr)
        if args.check:
            sys.exit(1)
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
