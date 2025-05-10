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


def execute_with_error_handling(
    cmd: t.Sequence[str], suppress_errors: bool = False
) -> t.Generator[str, None, int]:
    try:
        yield from execute(cmd)
        return 0
    except subprocess.CalledProcessError as e:
        if suppress_errors:
            print(f"Command failed with error: {e}")
            return e.returncode
        else:
            raise e
