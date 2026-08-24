import io
import os
import sys
import traceback
from contextlib import contextmanager
from typing import Any

try:
    import curses

    HAVE_CURSES = True
except ImportError:
    HAVE_CURSES = False

import subprocess
from .core import info, warn, error, success

# =====================================
# Curses TUI / Fallbacks
# =====================================

_USE_CURSES = HAVE_CURSES and sys.stdin.isatty()

# T7: one persistent curses screen per interactive session. interactive_menu
# opens it once and every widget draws into it, so multi-prompt flows no
# longer flash to the shell between widgets (each widget used to be its own
# curses.wrapper init/teardown). None when no session owns a screen — widgets
# invoked directly then fall back to a one-shot wrapper session.
_SCREEN = None


def _with_screen(fn):
    """Run a widget body against the session's persistent screen, or in a
    one-shot curses.wrapper session when no session owns one. Colors are
    initialized here (or in _open_screen), not per widget."""
    if _SCREEN is not None:
        return fn(_SCREEN)

    def _boot(stdscr):
        _init_tui_colors()
        return fn(stdscr)

    return curses.wrapper(_boot)


def open_screen():
    """Start the session screen (initscr + the modes curses.wrapper would
    set). Returns the screen, or None when curses can't start on this
    terminal — the caller degrades the whole session to the text menu."""
    global _SCREEN, _USE_CURSES
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        _init_tui_colors()
        _SCREEN = stdscr
        _USE_CURSES = True
        return stdscr
    except curses.error:
        # initscr may have partially engaged the terminal; put it back.
        try:
            if not curses.isendwin():
                curses.endwin()
        except curses.error:
            pass
        return None


def close_screen() -> None:
    """End the session screen. Idempotent and guarded, so it is safe after a
    mid-session degrade already ended the screen."""
    global _SCREEN
    _SCREEN = None
    
    if not HAVE_CURSES:
        return
    try:
        if not curses.isendwin():
            try:
                curses.echo()
                curses.nocbreak()
            except curses.error:
                pass
            curses.endwin()
    except curses.error:
        pass


def _degrade_to_text() -> None:
    """A mid-session curses failure (terminal died, capability lost): suspend
    the screen and flip the whole session to the text fallback. endwin puts
    the terminal back in normal mode and nothing refreshes it afterwards, so
    plain print/input work from here on."""
    global _USE_CURSES
    _USE_CURSES = False
    
    close_screen()


class CancelledError(Exception):
    pass

_Cancelled = CancelledError
"""Raised when the user cancels a prompt (Esc in the TUI, Ctrl-C/EOF at a
text prompt); the active prompt chain unwinds back to the menu instead of
launching a mode with defaults."""


def _prompt_str(label: str, default: str | None) -> str | None:
    """One prompt. Returns the entered value (the default on bare Enter), or
    None when the user cancelled."""
    if _USE_CURSES:
        return _tui_prompt_str(label, default)
    display = default if default else ""
    try:
        raw = input(f"  {label} [{display}]: ").strip()
    except EOFError, KeyboardInterrupt:
        print()
        return None
    return raw or (default or "")


def ask(label: str, default: str | None) -> str:
    """_prompt_str that raises _Cancelled instead of returning None, so a
    multi-prompt handler aborts as one unit."""
    val = _prompt_str(label, default)
    if val is None:
        raise _Cancelled
    return val


def ask_yn(label: str, default: str = "N") -> bool:
    return ask(label, default).lower().startswith("y")


def prompt_out(label: str, default: str) -> str:
    """Output-path prompt: expands ~ (no shell is there to do it) but is not
    made absolute, so relative paths keep their current meaning."""
    return os.path.expanduser(ask(label, default) or default)


def _out_note(path: str | None) -> str:
    """Results-pager footer saying where a report landed, so 'where did my
    report go' answers itself."""
    return f"Report written to {os.path.abspath(path)}" if path else ""


def prompt_int(label: str, default: int) -> int:
    prompt = label
    while True:
        s = ask(prompt, str(default)).strip()
        try:
            return int(s)
        except ValueError:
            prompt = f"{label} (not a number, try again)"


def notify(msg: str) -> None:
    """A notice the user must see before the next menu redraw."""
    if _USE_CURSES:
        tui_page("Notice", msg)
    else:
        print(f"  {msg}")


def box_menu(title: str, sections: list, width: int = 44) -> None:
    """Fallback text menu for environments without curses."""
    iw = width - 4
    print(f"\n  ╔{'═' * (width - 2)}╗")
    print(f"  ║ {title:^{iw}} ║")
    print(f"  ╠{'═' * (width - 2)}╣")
    first = True
    for header, items in sections:
        if not first:
            print(f"  ╟{'─' * (width - 2)}╢")
        first = False
        if header:
            print(f"  ║  {header:<{iw - 1}} ║")
        for item in items:
            print(f"  ║    {item:<{iw - 3}} ║")
    print(f"  ╚{'═' * (width - 2)}╝")


def _pause() -> None:
    """Wait for user acknowledgement before redrawing."""
    if _USE_CURSES:
        _tui_pause()
        return
    try:
        input("\n  Press Enter to continue...")
    except EOFError, KeyboardInterrupt:
        pass


_CP_FRAME = 1
_CP_TITLE = 2
_CP_HEADER = 3
_CP_ITEM = 4
_CP_SELECTED = 5
_CP_HINT = 6


def _init_tui_colors() -> None:
    """Set up curses color pairs for the TUI menus. Non-fatal: a terminal
    without color support gets a monochrome TUI instead of a dead one."""
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(_CP_FRAME, curses.COLOR_CYAN, -1)
        curses.init_pair(_CP_TITLE, curses.COLOR_WHITE, -1)
        curses.init_pair(_CP_HEADER, curses.COLOR_YELLOW, -1)
        curses.init_pair(_CP_ITEM, curses.COLOR_WHITE, -1)
        curses.init_pair(_CP_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(_CP_HINT, curses.COLOR_WHITE, -1)
    except curses.error:
        pass


def _curs_set(visibility: int) -> None:
    """curs_set raises on terminals without cursor-visibility support; the
    cursor is cosmetic, so never let it kill a widget."""
    try:
        curses.curs_set(visibility)
    except curses.error:
        pass


_TUI_BOX_W = 46
_TUI_INNER = _TUI_BOX_W - 2  # chars between the two ║ borders


def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int) -> None:
    """Write to curses screen, silently ignoring out-of-bounds errors."""
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _tui_select(
    title: str,
    sections: list,
    hints: str = "\u2191\u2193 Navigate  \u23ce Select  q Quit",
) -> tuple | None:
    """Full-screen arrow-key menu using curses."""
    BOX_W = _TUI_BOX_W
    INNER = _TUI_INNER

    flat: list[tuple[int, int]] = []
    for si, (_, items) in enumerate(sections):
        for ii in range(len(items)):
            flat.append((si, ii))

    def _draw(stdscr, cur: int) -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        bx = max(0, (w - BOX_W) // 2)
        fa = curses.color_pair(_CP_FRAME)

        box_h = 3
        sel_row = 3  # offset of the selected item from the box top
        idx0 = 0
        for si, (hdr, items) in enumerate(sections):
            if si > 0:
                box_h += 1
            if hdr:
                box_h += 1
            if idx0 <= cur < idx0 + len(items):
                sel_row = box_h + (cur - idx0)
            idx0 += len(items)
            box_h += len(items)
        box_h += 1

        y = max(0, (h - box_h - 2) // 2)
        if y + sel_row >= h - 1:
            # Terminal shorter than the menu: shift the box up so the selected
            # row stays visible (rows scrolled off the top just don't draw).
            y = (h - 2) - sel_row

        _safe_addstr(stdscr, y, bx, "\u2554" + "\u2550" * INNER + "\u2557", fa)
        y += 1

        _safe_addstr(stdscr, y, bx, "\u2551", fa)
        _safe_addstr(
            stdscr,
            y,
            bx + 1,
            f" {title:^{INNER - 2}} ",
            curses.color_pair(_CP_TITLE) | curses.A_BOLD,
        )
        _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
        y += 1

        _safe_addstr(stdscr, y, bx, "\u2560" + "\u2550" * INNER + "\u2563", fa)
        y += 1

        idx = 0
        for si, (hdr, items) in enumerate(sections):
            if si > 0:
                _safe_addstr(stdscr, y, bx, "\u255f" + "\u2500" * INNER + "\u2562", fa)
                y += 1

            if hdr:
                content = f"  {hdr}" + " " * (INNER - len(hdr) - 2)
                _safe_addstr(stdscr, y, bx, "\u2551", fa)
                _safe_addstr(
                    stdscr,
                    y,
                    bx + 1,
                    content,
                    curses.color_pair(_CP_HEADER) | curses.A_BOLD,
                )
                _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
                y += 1

            for _ii, label in enumerate(items):
                is_sel = idx == cur
                if is_sel:
                    text = f" \u25ba {label}"
                    attr = curses.color_pair(_CP_SELECTED) | curses.A_BOLD
                else:
                    text = f"   {label}"
                    attr = curses.color_pair(_CP_ITEM)
                padded = text + " " * max(0, INNER - len(text))
                _safe_addstr(stdscr, y, bx, "\u2551", fa)
                _safe_addstr(stdscr, y, bx + 1, padded[:INNER], attr)
                _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
                y += 1
                idx += 1

        _safe_addstr(stdscr, y, bx, "\u255a" + "\u2550" * INNER + "\u255d", fa)
        y += 2

        hx = max(0, (w - len(hints)) // 2)
        _safe_addstr(stdscr, y, hx, hints, curses.color_pair(_CP_HINT) | curses.A_DIM)

        stdscr.refresh()

    def _run(stdscr) -> tuple | None:
        _curs_set(0)
        cur = 0
        while True:
            _draw(stdscr, cur)
            key = stdscr.get_wch()
            if key in (curses.KEY_UP, "k"):
                cur = (cur - 1) % len(flat)
            elif key in (curses.KEY_DOWN, "j"):
                cur = (cur + 1) % len(flat)
            elif key in (curses.KEY_ENTER, 10, 13, "\n", "\r"):
                return flat[cur]
            elif key in ("q", "Q", 27, "\x1b"):
                return None
            elif key == curses.KEY_RESIZE:
                pass

    try:
        return _with_screen(_run)
    except curses.error:
        # A real curses failure (dumb terminal, TERM=vt100), not a user Quit:
        # degrade the whole session to the text fallback and hand the menu
        # loop a sentinel it re-enters on, instead of silently exiting 0.
        _degrade_to_text()
        return "fallback"


def _tui_prompt_str(label: str, default: str | None) -> str | None:
    """Boxed single-line prompt. Enter accepts (bare Enter = the default);
    Esc cancels and returns None; Ctrl-U clears the field."""
    BOX_W = _TUI_BOX_W
    INNER = _TUI_INNER

    def _run(stdscr) -> str | None:
        _curs_set(1)
        buf = list(default or "")

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            bx = max(0, (w - BOX_W) // 2)
            fa = curses.color_pair(_CP_FRAME)

            y = max(0, (h - 8) // 2)

            _safe_addstr(stdscr, y, bx, "\u2554" + "\u2550" * INNER + "\u2557", fa)
            y += 1

            lbl = f"  {label}"
            padded_lbl = lbl + " " * max(0, INNER - len(lbl))
            _safe_addstr(stdscr, y, bx, "\u2551", fa)
            _safe_addstr(
                stdscr,
                y,
                bx + 1,
                padded_lbl[:INNER],
                curses.color_pair(_CP_HEADER) | curses.A_BOLD,
            )
            _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
            y += 1

            _safe_addstr(stdscr, y, bx, "\u255f" + "\u2500" * INNER + "\u2562", fa)
            y += 1

            display = "".join(buf)
            max_input = INNER - 4
            if len(display) > max_input:
                visible = "\u2026" + display[-(max_input - 1) :]
            else:
                visible = display
            input_text = f" > {visible}" + " " * max(0, INNER - len(visible) - 3)
            _safe_addstr(stdscr, y, bx, "\u2551", fa)
            _safe_addstr(
                stdscr, y, bx + 1, input_text[:INNER], curses.color_pair(_CP_ITEM)
            )
            _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
            input_y = y
            y += 1

            _safe_addstr(stdscr, y, bx, "\u255a" + "\u2550" * INNER + "\u255d", fa)
            y += 2

            hints = "\u23ce Accept  Esc Cancel  Ctrl-U Clear"
            hx = max(0, (w - len(hints)) // 2)
            _safe_addstr(
                stdscr, y, hx, hints, curses.color_pair(_CP_HINT) | curses.A_DIM
            )

            cursor_x = bx + 4 + min(len(display), max_input)
            try:
                stdscr.move(input_y, min(cursor_x, bx + BOX_W - 2))
            except curses.error:
                pass
            stdscr.refresh()

            key = stdscr.get_wch()
            if key in (curses.KEY_ENTER, 10, 13, "\n", "\r"):
                result = "".join(buf).strip()
                return result if result else (default or "")
            elif key in (27, "\x1b"):
                return None  # Esc cancels; it must never launch with defaults
            elif key in (curses.KEY_BACKSPACE, 127, 8, "\x7f", "\x08"):
                if buf:
                    buf.pop()
            elif key in (21, "\x15"):  # Ctrl-U: clear the field (pre-filled defaults)
                buf.clear()
            elif key == curses.KEY_RESIZE:
                pass
            elif isinstance(key, str) and key.isprintable():
                buf.append(key)

    try:
        return _with_screen(_run)
    except KeyboardInterrupt:
        return None  # Ctrl-C at a prompt cancels, exactly like Esc
    except curses.error:
        # _USE_CURSES is now False, so this re-asks via the text prompt.
        _degrade_to_text()
        return _prompt_str(label, default)


def _tui_pause() -> None:
    BOX_W = _TUI_BOX_W
    INNER = _TUI_INNER

    def _run(stdscr) -> None:
        _curs_set(0)

        stdscr.erase()
        h, w = stdscr.getmaxyx()
        bx = max(0, (w - BOX_W) // 2)
        fa = curses.color_pair(_CP_FRAME)

        y = max(0, (h - 5) // 2)

        _safe_addstr(stdscr, y, bx, "\u2554" + "\u2550" * INNER + "\u2557", fa)
        y += 1

        msg = "Press Enter to continue\u2026"
        padded = f" {msg:^{INNER - 2}} "
        _safe_addstr(stdscr, y, bx, "\u2551", fa)
        _safe_addstr(
            stdscr,
            y,
            bx + 1,
            padded[:INNER],
            curses.color_pair(_CP_TITLE) | curses.A_BOLD,
        )
        _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
        y += 1

        _safe_addstr(stdscr, y, bx, "\u255a" + "\u2550" * INNER + "\u255d", fa)
        stdscr.refresh()

        while True:
            key = stdscr.get_wch()
            if key in (curses.KEY_ENTER, 10, 13, "\n", "\r", "q", "Q", 27, "\x1b"):
                return

    try:
        _with_screen(_run)
    except KeyboardInterrupt:
        pass
    except curses.error:
        # _USE_CURSES is now False, so this re-runs as the text pause.
        _degrade_to_text()
        _pause()


def fallback_input(prompt: str, mapping: dict) -> Any:
    # KeyboardInterrupt propagates on purpose: Ctrl-C at the menu must exit
    # 130 like the curses menu does, not read as a clean Quit.
    try:
        ch = input(prompt).strip().lower()
    except EOFError:
        print()
        return None  # input exhausted: treat as Quit
    return mapping.get(ch, "invalid")


def build_fallback(sections, aliases=None, letter_keys=None):
    aliases = aliases or {}
    letter_keys = letter_keys or {}
    mapping = dict(aliases)
    display = []
    n = 0
    for si, (hdr, items) in enumerate(sections):
        rows = []
        for ii, label in enumerate(items):
            clean = " ".join(label.split())
            letter = letter_keys.get(clean)
            if letter is not None:
                key, target = letter
                rows.append(f"{key}) {clean}")
                mapping[key] = (si, ii) if target == "self" else target
            else:
                n += 1
                rows.append(f"{n}) {clean}")
                mapping[str(n)] = (si, ii)
        display.append((hdr, rows))
    return display, mapping, n

def tui_select(title, sections, hints="↑↓ Navigate  ⏎ Select  q Quit", aliases=None, letter_keys=None):
    if _USE_CURSES:
        res = _tui_select(title, sections, hints=hints)
        if res != "fallback":
            return res
    # Fallback
    display, mapping, max_n = build_fallback(sections, aliases, letter_keys)
    box_menu(title, display)
    return fallback_input(f"  Select [1-{max_n}/q]: ", mapping)

def tui_page(title: str, content: str) -> None:
    if not _USE_CURSES:
        print(content)
        _pause()
        return

    lines = content.replace("\x00", "").expandtabs(4).split("\n")
    # Computed once, not per keypress: the content never changes while paging.
    max_line_len = max((len(ln) for ln in lines), default=0)

    def _run(stdscr):
        _curs_set(0)
        top = 0
        left = 0
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            fa = curses.color_pair(_CP_FRAME)

            # Width follows the longest line (up to the terminal width) so wide
            # reports — long duplicate paths, say — are not chopped at 80 columns.
            content_w = min(w, max(_TUI_BOX_W, max_line_len + 4))
            bx = max(0, (w - content_w) // 2)
            max_lines = max(1, h - 3)
            last_top = max(0, len(lines) - max_lines)
            top = min(top, last_top)  # keep the view valid across resizes
            visible_w = max(1, content_w - 4)
            max_left = max(0, max_line_len - visible_w)
            left = min(left, max_left)

            # Title on the top border, hints on the last row; content fills the
            # full height between them.
            _safe_addstr(stdscr, 0, bx, "╔" + "═" * (content_w - 2) + "╗", fa)
            _safe_addstr(
                stdscr,
                0,
                bx + 2,
                f" {title} ",
                curses.color_pair(_CP_TITLE) | curses.A_BOLD,
            )
            _safe_addstr(stdscr, h - 2, bx, "╚" + "═" * (content_w - 2) + "╝", fa)

            hints = "↑↓ Scroll  ←→ Pan  PgUp/Dn  g/G Top/Bottom  q/Esc Close"
            _safe_addstr(
                stdscr,
                h - 1,
                max(0, (w - len(hints)) // 2),
                hints,
                curses.color_pair(_CP_HINT) | curses.A_DIM,
            )

            for i in range(max_lines):
                _safe_addstr(stdscr, i + 1, bx, "║", fa)
                if top + i < len(lines):
                    ln = lines[top + i]
                    seg = ln[left : left + visible_w]
                    # Ellipsis markers show that a line continues off-screen.
                    if len(ln) - left > visible_w and seg:
                        seg = seg[:-1] + "…"
                    if left and seg:
                        seg = "…" + seg[1:]
                    _safe_addstr(
                        stdscr,
                        i + 1,
                        bx + 2,
                        seg,
                        curses.color_pair(_CP_ITEM),
                    )
                _safe_addstr(stdscr, i + 1, bx + content_w - 1, "║", fa)

            stdscr.refresh()

            key = stdscr.get_wch()
            if key in (curses.KEY_UP, "k"):
                top = max(0, top - 1)
            elif key in (curses.KEY_DOWN, "j"):
                top = min(last_top, top + 1)
            elif key in (curses.KEY_LEFT, "h"):
                left = max(0, left - 8)
            elif key in (curses.KEY_RIGHT, "l"):
                left = min(max_left, left + 8)
            elif key == curses.KEY_PPAGE:
                top = max(0, top - max_lines)
            elif key == curses.KEY_NPAGE:
                top = min(last_top, top + max_lines)
            elif key in (curses.KEY_HOME, "g"):
                top = 0
                left = 0
            elif key in (curses.KEY_END, "G"):
                top = last_top
            elif key in ("q", "Q", 27, "\x1b", curses.KEY_ENTER, 10, 13, "\n", "\r"):
                break
            elif key == curses.KEY_RESIZE:
                pass

    try:
        _with_screen(_run)
    except KeyboardInterrupt:
        pass  # Ctrl-C just closes the pager
    except curses.error:
        _degrade_to_text()
        print(content)
        _pause()


@contextmanager
def capture_output():
    old_out, old_err = sys.stdout, sys.stderr
    out, err = io.StringIO(), io.StringIO()
    sys.stdout, sys.stderr = out, err
    try:
        yield out, err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def run_with_capture(title: str, func, *args, footer: str = "", **kwargs):
    result = None
    note = ""
    with capture_output() as (out, err):
        try:
            result = func(*args, **kwargs)
        except KeyboardInterrupt:
            note = "[Cancelled]"
        except Exception:
            # A mode error must not escape as a raw traceback with the screen
            # stuck in curses mode; page it (plus whatever was captured).
            note = "[Error]\n" + traceback.format_exc().rstrip()
    # With a session screen the mode's _TUIPbar drew into it and nothing needs
    # tearing down. Without one (direct invocation) the pbar initscr()'d a
    # screen of its own; end it before paging, even (especially) when the mode
    # died mid-run.
    if _SCREEN is None:
        if _USE_CURSES:
            try:
                if not curses.isendwin():
                    curses.endwin()
            except curses.error:
                pass
        reset_terminal()

    text = ""
    if note:
        text += note + "\n"
    if isinstance(result, str) and result:
        text += result + "\n"

    out_text = out.getvalue().strip()
    if out_text:
        text += out_text + "\n"

    err_text = err.getvalue().strip()
    if err_text:
        text += "\n[Errors/Warnings]:\n" + err_text + "\n"

    if footer and not note:
        # The "Report written to ..." footer must not assert a file exists
        # when the mode died or was cancelled before finishing.
        text += "\n" + footer + "\n"

    text = text.strip()
    if text:
        tui_page(title, text)
    else:
        _pause()


def reset_terminal() -> None:
    if _SCREEN is not None:
        return
    if not sys.stdin.isatty():
        return
    try:
        subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
    except Exception:
        pass
