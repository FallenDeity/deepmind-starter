import argparse
import json
import pathlib
import sys
import tempfile

from utils import execute_with_error_handling


def lint_code(code: str, history: list[str], check: bool = False) -> tuple[str, int]:
    """Lint (and optionally fix) TypeScript code using ESLint."""
    tmp_path = pathlib.Path.cwd() / ".temp"
    tmp_path.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        suffix=".ts", mode="w+", encoding="utf-8", dir=tmp_path
    ) as tmp:
        previous_code = "\n".join(history) if history else ""
        tmp.write(previous_code)
        tmp.write(code)
        tmp.flush()

        args = ["npx", "eslint", tmp.name]
        if not check:
            args.append("--fix")
        return_code = 0
        for line in execute_with_error_handling(args, suppress_errors=True):
            if isinstance(line, int) and line:
                return_code = int(line)
                return code, return_code
            print(line, end="")

        with open(tmp.name, "r", encoding="utf-8") as f:
            fixed_code: str = f.read()
            if previous_code:
                fixed_code = fixed_code.replace(previous_code, "", 1)
            return fixed_code, return_code


def process_notebook(path: pathlib.Path, check: bool = False) -> bool:
    print(f"Processing notebook: {path}")

    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    changed = False

    if nb.get("metadata", {}).get("language_info", {}).get("name") != "typescript":
        print(f"Skipping non-TypeScript notebook: {path}")
        return False

    cell_history: list[str] = []

    for n, cell in enumerate(nb.get("cells", []), start=1):
        if cell.get("cell_type") == "code":
            original_code = "".join(cell["source"])
            fixed_code, return_code = lint_code(
                original_code, history=cell_history[:n], check=check
            )
            cell_history.append(fixed_code)
            if fixed_code != original_code:
                changed = True
                if check:
                    print(f"Cell {n} in {path} needs linting.")
                    continue
                cell["source"] = fixed_code.splitlines(keepends=True)
                print(f"Linted cell {n} in {path}")
            else:
                if return_code == 0:
                    print(f"Cell {n} in {path} is already linted.")
                else:
                    print(f"Cell {n} in {path} has lint issues.")
        else:
            print(f"Skipping non-code cell {n} in {path}")

    if check:
        return changed

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1)
        print(f"Linted and updated: {path}")
    else:
        print(f"No changes: {path}")

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint TypeScript code in Jupyter notebooks using ESLint."
    )
    parser.add_argument(
        "path",
        help="Path to a Jupyter notebook or directory containing notebooks.",
        type=pathlib.Path,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for lint issues without modifying files.",
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
        print("Some notebooks need linting.", file=sys.stderr)
        sys.exit(1)
    else:
        print("All notebooks are linted.")


if __name__ == "__main__":
    main()
