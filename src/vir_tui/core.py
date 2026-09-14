"""ANSI styling and the tqdm re-export: color gating (NO_COLOR and TTY
detection), the success/info/warn/error formatters, and tqdm imported from
the consumer's environment when available or a minimal stdlib stub when it
is not."""

import os
import sys

try:
    from tqdm import tqdm
except ImportError:
    # Minimal fallback if tqdm is missing
    class tqdm:
        """Minimal stand-in for the real tqdm: iteration counting, an
        optional description line, update()/close()/set_description(), and
        the write() classmethod. Deliberately not a context manager
        (consumers drive update()/close() directly) and unknown kwargs are
        absorbed, which covers every surface the consumers exercise."""

        def __init__(
            self,
            iterable=None,
            desc=None,
            disable=False,
            total=None,
            unit="it",
            leave=True,
            **kwargs,
        ):
            self.iterable = iterable
            self.desc = desc
            self.disable = disable
            self.total = total
            self.unit = unit
            self.leave = leave
            self.n = 0
            if not self.disable and self.desc:
                print(f"{self.desc}...", file=sys.stderr)

        def __iter__(self):
            if self.iterable is None:
                return self
            for item in self.iterable:
                yield item
                self.update(1)

        def update(self, n=1):
            self.n += n

        def close(self):
            if not self.disable and self.leave and self.total is not None:
                print(f"Finished {self.n}/{self.total} {self.unit}", file=sys.stderr)

        def set_description(self, desc):
            self.desc = desc

        def set_postfix(self, **kwargs):
            pass

        @staticmethod
        def write(s, file=None, end="\n"):
            print(s, file=file or sys.stdout, end=end)


# ANSI Colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _use_color() -> bool:
    return "NO_COLOR" not in os.environ and sys.stdout.isatty()


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if _use_color() else text


def info(msg: str) -> str:
    return color(f"ℹ {msg}", CYAN)


def success(msg: str) -> str:
    return color(f"✓ {msg}", GREEN)


def warn(msg: str) -> str:
    return color(f"⚠ {msg}", YELLOW)


def error(msg: str) -> str:
    return color(f"✗ {msg}", RED)


def dry_run(msg: str) -> str:
    return f"{color('[DRY]', YELLOW)} {msg}"


def print_header(title: str) -> None:
    tqdm.write(color(f"\n{'=' * 60}", BOLD))
    tqdm.write(color(f"{title}", BOLD + CYAN))
    tqdm.write(color(f"{'=' * 60}", BOLD))


def print_summary(stats: dict) -> None:
    tqdm.write(color("\n--- SUMMARY ---", BOLD))
    for k, v in stats.items():
        if isinstance(v, int) and v > 0:
            tqdm.write(f"  {k}: {color(str(v), GREEN)}")
        else:
            tqdm.write(f"  {k}: {v}")
    tqdm.write(color("===============\n", BOLD))
