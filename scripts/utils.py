import subprocess
import typing as t


def execute(cmd: t.Sequence[str]) -> t.Generator[str, None, None]:
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    if popen.stdout is None:
        raise ValueError("stdout is None")
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def diff_strings(a: str, b: str) -> str:
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    diff = []
    for line_num, line in enumerate(a_lines):
        if line not in b_lines:
            diff.append(f"[{line_num + 1}] - {line}")
    diff.append("\n")
    for line_num, line in enumerate(b_lines):
        if line not in a_lines:
            diff.append(f"[{line_num + 1}] + {line}")
    return "".join(diff).strip()
