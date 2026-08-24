import os
import sys
import traceback
import readline

from vir_tui.core import info, warn, error, _use_color, BOLD, RESET

class _Cancelled(Exception):
    pass

def ask(prompt: str, default: str = "") -> str:
    print(info(prompt) + ("" if not default else f" [{default}]") + ": ", end="")
    if default:
        readline.set_startup_hook(lambda: readline.insert_text(default))
    try:
        line = input()
        return line.strip() or default
    except (EOFError, KeyboardInterrupt):
        print()
        raise _Cancelled()
    finally:
        readline.set_startup_hook()

def ask_yn(prompt: str) -> bool:
    while True:
        ans = ask(prompt, "").lower()
        if ans in ("y", "yes"): return True
        if ans in ("n", "no"): return False
        if not ans: return False
        print(warn("Please answer y or n."))

def prompt_int(prompt: str, default: int) -> int:
    while True:
        ans = ask(prompt, str(default))
        try:
            return int(ans)
        except ValueError:
            print(error(f"Not an integer: {ans}"))

def prompt_out(prompt: str, default: str) -> str:
    while True:
        ans = ask(prompt, default)
        if not ans:
            continue
        path = os.path.abspath(ans)
        if os.path.exists(path):
            if not ask_yn(warn(f"Overwrite {path}? (y/N)")):
                continue
        return path

def run_with_capture(title: str, func, *args, footer: str = "", **kwargs) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print("=" * 60)
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(error(f"Failed: {e}"), file=sys.stderr)
        traceback.print_exc()
    print("=" * 60)
    if footer:
        print(f"\n{info(footer)}")
    ask("\nPress Enter to continue...", "")
