import io
import os
import sys
import time
import traceback
from contextlib import contextmanager
from typing import Any, Self

try:
    import curses

    HAVE_CURSES = True
except ImportError:
    HAVE_CURSES = False

import subprocess

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
        _enable_mouse(stdscr)
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
        _enable_mouse(stdscr)
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


def session_screen():
    """The persistent curses screen owned by an open interactive session, or
    None. Host apps publish it to their own widgets (progress boxes) so those
    render into the session's screen instead of starting one of their own."""
    return _SCREEN


def text_mode() -> bool:
    """True when the session runs without curses — no TTY, no curses module,
    or a mid-session degrade. Hosts use it to pick text-only affordances
    (e.g. printing an error line at a text menu instead of redrawing)."""
    return not _USE_CURSES


@contextmanager
def interactive_session():
    """Own the persistent session screen for a host's interactive menu loop.

    Opens the curses session (yielding None when the terminal can't support
    one, with the whole session degraded to the text fallback) and always
    closes it on exit. KeyboardInterrupt is re-raised after cleanup so hosts
    keep translating it into their own exit code (conventionally 130) without
    the terminal staying broken. Replaces the open_screen/try/finally/
    close_screen boilerplate CalibreQuarry and Lattice each carried.
    """
    stdscr = open_screen()
    if _USE_CURSES and stdscr is None:
        _degrade_to_text()
    try:
        try:
            yield stdscr
        except KeyboardInterrupt:
            if _SCREEN is None:
                print()
            raise
    finally:
        close_screen()


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


def out_note(path: str | None) -> str:
    """Public form of :func:`_out_note` — hosts used to copy this helper
    verbatim because only the underscored name existed."""
    return _out_note(path)


def prompt_int(label: str, default: int) -> int:
    prompt = label
    while True:
        s = ask(prompt, str(default)).strip()
        try:
            return int(s)
        except ValueError:
            prompt = f"{label} (not a number, try again)"


def prompt_float(
    label: str,
    default: float,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    """Float prompt with optional inclusive bounds; re-asks with a reason on
    non-numeric or out-of-range input. Esc still cancels (CancelledError)."""
    prompt = label
    while True:
        s = ask(prompt, f"{default:g}").strip()
        try:
            val = float(s)
        except ValueError:
            prompt = f"{label} (not a number, try again)"
            continue
        if lo is not None and hi is not None and not lo <= val <= hi:
            prompt = f"{label} (must be between {lo:g} and {hi:g})"
            continue
        if lo is not None and val < lo:
            prompt = f"{label} (must be >= {lo:g})"
            continue
        if hi is not None and val > hi:
            prompt = f"{label} (must be <= {hi:g})"
            continue
        return val


def prompt_path(label: str, default: str = "", *, must_exist: bool = True) -> str:
    """Path prompt: expands `~` and returns an absolute path. With
    ``must_exist`` it re-asks (with a notice) until the path exists, so
    hosts stop hand-rolling existence loops. Esc still cancels."""
    prompt = label
    while True:
        raw = ask(prompt, default)
        path = os.path.abspath(os.path.expanduser(raw))
        if not must_exist or os.path.exists(path):
            return path
        notify(f"Not found: {path}")


def confirm(label: str, default: bool = False, *, danger: bool = False) -> bool:
    """Yes/no gate worded for destructive actions: ``danger`` prefixes the
    label and defaults to No, so a bare Enter never destroys anything."""
    text = f"DANGER — {label}" if danger else label
    return ask_yn(text, "y" if default else "N")


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

# Public aliases: hosts rendering their own widgets into the session screen
# (progress boxes, custom panels) use these instead of hand-mirroring the
# private numeric ids, which would break silently if vir-tui restyled.
CP_FRAME = _CP_FRAME
CP_TITLE = _CP_TITLE
CP_HEADER = _CP_HEADER
CP_ITEM = _CP_ITEM
CP_SELECTED = _CP_SELECTED
CP_HINT = _CP_HINT

# Theme overrides: hosts remap color pairs and box glyphs per app via
# configure_theme() instead of hand-mirroring ids or forking widgets.

_PAIR_NAMES = ("frame", "title", "header", "item", "selected", "hint")
_PAIR_OVERRIDES: dict[str, tuple[int, int]] = {}

_GLYPH_DEFAULTS = {
    "tl": "╔",
    "tr": "╗",
    "bl": "╚",
    "br": "╝",
    "join_l": "╠",
    "join_r": "╣",
    "soft_l": "╟",
    "soft_r": "╢",
    "hline": "═",
    "hline_light": "─",
    "vline": "║",
    "pointer": "►",
    "block": "█",
    "block_light": "░",
}
_GLYPHS: dict[str, str] = {}


def configure_theme(
    *,
    color_pairs: dict[str, tuple[int, int]] | None = None,
    glyphs: dict[str, str] | None = None,
) -> None:
    """Host-level theme remapping; call once at startup, before the first
    widget runs.

    ``color_pairs`` maps semantic pair names — "frame", "title", "header",
    "item", "selected", "hint" — to ``(fg, bg)`` curses color constants
    (e.g. ``(curses.COLOR_CYAN, -1)``), applied at the next color
    initialization (the next screen open). ``glyphs`` maps glyph names —
    "tl", "tr", "bl", "br", "join_l", "join_r", "soft_l", "soft_r",
    "hline", "hline_light", "vline", "pointer", "block", "block_light" —
    to characters, effective immediately. Unknown names raise ValueError:
    a silent typo would leave a host's widgets half-restyled.
    """
    for name, pair in (color_pairs or {}).items():
        if name not in _PAIR_NAMES:
            raise ValueError(
                f"unknown color pair {name!r}; expected one of {_PAIR_NAMES}"
            )
        _PAIR_OVERRIDES[name] = pair
    for name, ch in (glyphs or {}).items():
        if name not in _GLYPH_DEFAULTS:
            raise ValueError(
                f"unknown glyph {name!r}; expected one of {sorted(_GLYPH_DEFAULTS)}"
            )
        _GLYPHS[name] = ch


def _glyph(name: str) -> str:
    return _GLYPHS.get(name) or _GLYPH_DEFAULTS[name]


def _init_tui_colors() -> None:
    """Set up curses color pairs for the TUI menus. Non-fatal: a terminal
    without color support gets a monochrome TUI instead of a dead one.
    configure_theme() overrides apply here."""
    defaults = {
        "frame": (curses.COLOR_CYAN, -1),
        "title": (curses.COLOR_WHITE, -1),
        "header": (curses.COLOR_YELLOW, -1),
        "item": (curses.COLOR_WHITE, -1),
        "selected": (curses.COLOR_BLACK, curses.COLOR_CYAN),
        "hint": (curses.COLOR_WHITE, -1),
    }
    try:
        curses.start_color()
        curses.use_default_colors()
        for cp, name in (
            (_CP_FRAME, "frame"),
            (_CP_TITLE, "title"),
            (_CP_HEADER, "header"),
            (_CP_ITEM, "item"),
            (_CP_SELECTED, "selected"),
            (_CP_HINT, "hint"),
        ):
            fg, bg = _PAIR_OVERRIDES.get(name, defaults[name])
            curses.init_pair(cp, fg, bg)
    except curses.error:
        pass


def _enable_mouse(stdscr) -> None:
    """Best-effort mouse activation (click-to-select, wheel events). A
    terminal or curses build without mouse support degrades to keyboard-only."""
    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    except curses.error:
        pass


_FILTER_MIN_ITEMS = 15
"""Type-to-filter arms at this many items: below it every key keeps its
simple meaning (``q`` quits, letters do nothing) and a filter would be
noise."""


def _filter_visible(
    flat: list[tuple[int, int, str]], query: str
) -> list[tuple[int, int, str]]:
    """The flat ``(si, ii, label)`` entries whose label casefold-contains
    ``query``. Pure so type-to-filter is testable without a curses session."""
    if not query:
        return list(flat)
    q = query.casefold()
    return [e for e in flat if q in e[2].casefold()]


def _curs_set(visibility: int) -> None:
    """curs_set raises on terminals without cursor-visibility support; the
    cursor is cosmetic, so never let it kill a widget."""
    try:
        curses.curs_set(visibility)
    except curses.error:
        pass


_TUI_BOX_W = 46
_TUI_INNER = _TUI_BOX_W - 2  # chars between the two ║ borders


class ProgressBox:
    """Curses progress box matching the TUI style, with a tqdm-like API.

    Draws into the persistent session screen when an interactive session owns
    one; without one it prints plain carriage-returned text lines instead of
    starting a screen of its own, so pipes and redirects stay clean. Redraws
    are throttled — a full-screen erase per item on a 100k-item scan is visible
    flicker and wasted work — and the final update always draws. Progress is
    cosmetic: every draw failure is swallowed, never fatal to the mode.
    """

    _MIN_REDRAW_S = 0.1

    def __init__(self, total: int, desc: str = ""):
        self.total = max(0, int(total))
        self.desc = desc
        self.current = 0
        self._last_draw = 0.0
        self._closed = False
        self.draw()

    def set_description(self, desc: str) -> None:
        """tqdm-parity alias for changing the header text mid-run."""
        self.desc = desc
        self.draw()

    def update(self, n: int = 1) -> None:
        if self._closed:
            return
        self.current += n
        if (
            self.current >= self.total
            or time.monotonic() - self._last_draw >= self._MIN_REDRAW_S
        ):
            self.draw()

    def close(self) -> None:
        """Release the display. The session screen is the session's to tear
        down (the next menu redraw erases the box); the text fallback just
        ends its in-place line."""
        if self._closed:
            return
        self._closed = True
        if _SCREEN is None and sys.stdout.isatty():
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except OSError:
                pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _text_line(self) -> str:
        percent = self.current / max(1, self.total)
        bar_len = 30
        filled = int(bar_len * percent)
        bar = "█" * filled + "░" * (bar_len - filled)
        return (
            f"{self.desc}: |{bar}| {self.current}/{self.total} ({percent * 100:.0f}%)"
        )

    def draw(self) -> None:
        self._last_draw = time.monotonic()
        scr = _SCREEN
        try:
            if scr is not None:
                self._draw_curses(scr)
            elif sys.stdout.isatty():
                end = "\n" if self.current >= self.total else ""
                sys.stdout.write("\r" + self._text_line() + end)
                sys.stdout.flush()
        except Exception:
            # curses.error, or curses missing entirely: progress is cosmetic.
            pass

    def _draw_curses(self, s) -> None:
        import curses

        box_w = _TUI_BOX_W
        inner = box_w - 2
        bx = max(0, (s.getmaxyx()[1] - box_w) // 2)
        y = max(0, (s.getmaxyx()[0] - 6) // 2)
        fa = curses.color_pair(_CP_FRAME)

        s.erase()
        _safe_addstr(
            s, y, bx, _glyph("tl") + _glyph("hline") * inner + _glyph("tr"), fa
        )
        _safe_addstr(s, y + 1, bx, _glyph("vline"), fa)
        _safe_addstr(
            s,
            y + 1,
            bx + 1,
            f" {self.desc}".ljust(inner),
            curses.color_pair(_CP_HEADER) | curses.A_BOLD,
        )
        _safe_addstr(s, y + 1, bx + box_w - 1, _glyph("vline"), fa)
        _safe_addstr(
            s,
            y + 2,
            bx,
            _glyph("join_l") + _glyph("hline") * inner + _glyph("join_r"),
            fa,
        )

        percent = self.current / max(1, self.total)
        bar_len = inner - 10
        filled = int(bar_len * percent)
        bar = "█" * filled + "░" * (bar_len - filled)
        pct_str = f"{int(percent * 100):3d}%"

        _safe_addstr(s, y + 3, bx, _glyph("vline"), fa)
        _safe_addstr(
            s,
            y + 3,
            bx + 1,
            f" {bar} {pct_str} ".ljust(inner),
            curses.color_pair(_CP_ITEM),
        )
        _safe_addstr(s, y + 3, bx + box_w - 1, _glyph("vline"), fa)
        info = f" {self.current}/{self.total} · Ctrl-C cancels"
        _safe_addstr(s, y + 4, bx, _glyph("vline"), fa)
        _safe_addstr(
            s,
            y + 4,
            bx + 1,
            info[:inner].ljust(inner),
            curses.color_pair(_CP_ITEM),
        )
        _safe_addstr(s, y + 4, bx + box_w - 1, _glyph("vline"), fa)
        _safe_addstr(
            s, y + 5, bx, _glyph("bl") + _glyph("hline") * inner + _glyph("br"), fa
        )
        s.refresh()


def progress_box(total: int, desc: str = "") -> ProgressBox:
    """Factory matching tqdm's ``(total, desc)`` shape for drop-in use::

    with vir_tui.progress_box(len(items), "Scanning") as bar:
        for item in items:
            ...
            bar.update()
    """
    return ProgressBox(total, desc)


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
    """Full-screen arrow-key menu using curses.

    On menus of ``_FILTER_MIN_ITEMS``+ entries, printable characters type a
    filter that narrows the view incrementally (Esc clears it, then Esc
    quits; Enter still selects from the narrowed view). With mouse support,
    a click moves the selection, a double-click selects, and the wheel
    scrolls."""
    BOX_W = _TUI_BOX_W
    INNER = _TUI_INNER

    flat: list[tuple[int, int, str]] = []
    for si, (_, items) in enumerate(sections):
        for ii, label in enumerate(items):
            flat.append((si, ii, label))
    filter_on = len(flat) >= _FILTER_MIN_ITEMS

    def _draw(stdscr, cur: int, visible, query: str) -> dict[int, int]:
        """Draw the (possibly narrowed) menu; returns {screen row: visible
        index} for mouse hit-testing."""
        row_map: dict[int, int] = {}
        vis_by_si: dict[int, list[int]] = {}
        for vi, (si, _ii, _label) in enumerate(visible):
            vis_by_si.setdefault(si, []).append(vi)

        stdscr.erase()
        h, w = stdscr.getmaxyx()
        bx = max(0, (w - BOX_W) // 2)
        fa = curses.color_pair(_CP_FRAME)

        box_h = 3
        sel_row = 3
        first = True
        for si, (hdr, _items) in enumerate(sections):
            vis = vis_by_si.get(si)
            if not vis:
                continue
            if not first:
                box_h += 1
            first = False
            if hdr:
                box_h += 1
            for vi in vis:
                if vi == cur:
                    sel_row = box_h
                box_h += 1
        box_h += 1

        y = max(0, (h - box_h - 2) // 2)
        if y + sel_row >= h - 1:
            # Terminal shorter than the menu: shift the box up so the selected
            # row stays visible (rows scrolled off the top just don't draw).
            y = (h - 2) - sel_row

        _safe_addstr(
            stdscr, y, bx, _glyph("tl") + _glyph("hline") * INNER + _glyph("tr"), fa
        )
        y += 1

        _safe_addstr(stdscr, y, bx, _glyph("vline"), fa)
        _safe_addstr(
            stdscr,
            y,
            bx + 1,
            f" {title:^{INNER - 2}} ",
            curses.color_pair(_CP_TITLE) | curses.A_BOLD,
        )
        _safe_addstr(stdscr, y, bx + BOX_W - 1, _glyph("vline"), fa)
        y += 1

        _safe_addstr(
            stdscr,
            y,
            bx,
            _glyph("join_l") + _glyph("hline") * INNER + _glyph("join_r"),
            fa,
        )
        y += 1

        idx = 0
        first = True
        for si, (hdr, _items) in enumerate(sections):
            vis = vis_by_si.get(si)
            if not vis:
                continue
            if not first:
                _safe_addstr(
                    stdscr,
                    y,
                    bx,
                    _glyph("soft_l") + _glyph("hline_light") * INNER + _glyph("soft_r"),
                    fa,
                )
                y += 1
            first = False

            if hdr:
                content = f"  {hdr}" + " " * (INNER - len(hdr) - 2)
                _safe_addstr(stdscr, y, bx, _glyph("vline"), fa)
                _safe_addstr(
                    stdscr,
                    y,
                    bx + 1,
                    content,
                    curses.color_pair(_CP_HEADER) | curses.A_BOLD,
                )
                _safe_addstr(stdscr, y, bx + BOX_W - 1, _glyph("vline"), fa)
                y += 1

            for vi in vis:
                _si, _ii, label = visible[vi]
                is_sel = vi == cur
                if is_sel:
                    text = f" {_glyph('pointer')} {label}"
                    attr = curses.color_pair(_CP_SELECTED) | curses.A_BOLD
                else:
                    text = f"   {label}"
                    attr = curses.color_pair(_CP_ITEM)
                padded = text + " " * max(0, INNER - len(text))
                _safe_addstr(stdscr, y, bx, _glyph("vline"), fa)
                _safe_addstr(stdscr, y, bx + 1, padded[:INNER], attr)
                _safe_addstr(stdscr, y, bx + BOX_W - 1, _glyph("vline"), fa)
                row_map[y] = vi
                y += 1
                idx += 1

        _safe_addstr(
            stdscr, y, bx, _glyph("bl") + _glyph("hline") * INNER + _glyph("br"), fa
        )
        y += 2

        if filter_on and query:
            hints_line = (
                f"/{query}  {len(visible)}/{len(flat)}  ⌫ Edit  Esc Clear  ⏎ Select"
            )
        elif filter_on:
            hints_line = f"{hints}  type to filter"
        else:
            hints_line = hints
        hx = max(0, (w - len(hints_line)) // 2)
        _safe_addstr(
            stdscr, y, hx, hints_line, curses.color_pair(_CP_HINT) | curses.A_DIM
        )

        stdscr.refresh()
        return row_map

    def _run(stdscr) -> tuple | None:
        _curs_set(0)
        cur = 0
        query = ""
        visible = _filter_visible(flat, query)
        while True:
            row_map = _draw(stdscr, cur, visible, query)
            key = stdscr.get_wch()
            if key == curses.KEY_MOUSE:
                try:
                    _mid, _mx, my, _z, bstate = curses.getmouse()
                except curses.error:
                    continue
                hit = row_map.get(my)
                if hit is None:
                    continue
                if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                    return visible[hit][:2]
                if bstate & curses.BUTTON1_CLICKED:
                    cur = hit
                elif bstate & curses.BUTTON4_PRESSED:
                    cur = (cur - 1) % max(1, len(visible))
                elif bstate & curses.BUTTON5_PRESSED:
                    cur = (cur + 1) % max(1, len(visible))
            elif key in (curses.KEY_UP, "k"):
                if visible:
                    cur = (cur - 1) % len(visible)
            elif key in (curses.KEY_DOWN, "j"):
                if visible:
                    cur = (cur + 1) % len(visible)
            elif key in (curses.KEY_ENTER, 10, 13, "\n", "\r"):
                if visible:
                    return visible[cur][:2]
            elif key in (27, "\x1b"):
                if query:
                    query = ""
                    cur = 0
                else:
                    return None
            elif key in (curses.KEY_BACKSPACE, 127, 8, "\x7f", "\x08"):
                if query:
                    query = query[:-1]
                    cur = 0
                    visible = _filter_visible(flat, query)
            elif key in ("q", "Q") and not query:
                return None
            elif key == curses.KEY_RESIZE:
                pass
            elif filter_on and isinstance(key, str) and key.isprintable():
                if key.isspace() and not query:
                    continue  # a leading space filters nothing
                query += key
                cur = 0
                visible = _filter_visible(flat, query)
            if visible and cur >= len(visible):
                cur = len(visible) - 1

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

            _safe_addstr(
                stdscr, y, bx, _glyph("tl") + _glyph("hline") * INNER + _glyph("tr"), fa
            )
            y += 1

            lbl = f"  {label}"
            padded_lbl = lbl + " " * max(0, INNER - len(lbl))
            _safe_addstr(stdscr, y, bx, _glyph("vline"), fa)
            _safe_addstr(
                stdscr,
                y,
                bx + 1,
                padded_lbl[:INNER],
                curses.color_pair(_CP_HEADER) | curses.A_BOLD,
            )
            _safe_addstr(stdscr, y, bx + BOX_W - 1, _glyph("vline"), fa)
            y += 1

            _safe_addstr(
                stdscr,
                y,
                bx,
                _glyph("soft_l") + _glyph("hline_light") * INNER + _glyph("soft_r"),
                fa,
            )
            y += 1

            display = "".join(buf)
            max_input = INNER - 4
            if len(display) > max_input:
                visible = "\u2026" + display[-(max_input - 1) :]
            else:
                visible = display
            input_text = f" > {visible}" + " " * max(0, INNER - len(visible) - 3)
            _safe_addstr(stdscr, y, bx, _glyph("vline"), fa)
            _safe_addstr(
                stdscr, y, bx + 1, input_text[:INNER], curses.color_pair(_CP_ITEM)
            )
            _safe_addstr(stdscr, y, bx + BOX_W - 1, _glyph("vline"), fa)
            input_y = y
            y += 1

            _safe_addstr(
                stdscr, y, bx, _glyph("bl") + _glyph("hline") * INNER + _glyph("br"), fa
            )
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

        _safe_addstr(
            stdscr, y, bx, _glyph("tl") + _glyph("hline") * INNER + _glyph("tr"), fa
        )
        y += 1

        msg = "Press Enter to continue\u2026"
        padded = f" {msg:^{INNER - 2}} "
        _safe_addstr(stdscr, y, bx, _glyph("vline"), fa)
        _safe_addstr(
            stdscr,
            y,
            bx + 1,
            padded[:INNER],
            curses.color_pair(_CP_TITLE) | curses.A_BOLD,
        )
        _safe_addstr(stdscr, y, bx + BOX_W - 1, _glyph("vline"), fa)
        y += 1

        _safe_addstr(
            stdscr, y, bx, _glyph("bl") + _glyph("hline") * INNER + _glyph("br"), fa
        )
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


def tui_select(
    title,
    sections,
    hints="↑↓ Navigate  ⏎ Select  q Quit",
    aliases=None,
    letter_keys=None,
):
    if _USE_CURSES:
        res = _tui_select(title, sections, hints=hints)
        if res != "fallback":
            return res
    # Fallback
    display, mapping, max_n = build_fallback(sections, aliases, letter_keys)
    box_menu(title, display)
    return fallback_input(f"  Select [1-{max_n}/q]: ", mapping)


def _match_lines(
    lines: list[str], query: str, start: int = 0, reverse: bool = False
) -> int | None:
    """Index of the first line containing ``query`` (case-insensitive),
    searching forward from ``start`` — or backward when ``reverse`` — and
    wrapping around once. None when there is no match. A pure helper so
    pager search is testable without a curses session."""
    q = query.casefold()
    if not q or not lines:
        return None
    n = len(lines)
    start = max(0, min(start, n - 1))
    if reverse:
        order = list(range(start, -1, -1)) + list(range(n - 1, start, -1))
    else:
        order = list(range(start, n)) + list(range(start))
    for i in order:
        if q in lines[i].casefold():
            return i
    return None


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
        query = ""
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
            _safe_addstr(
                stdscr,
                0,
                bx,
                _glyph("tl") + _glyph("hline") * (content_w - 2) + _glyph("tr"),
                fa,
            )
            _safe_addstr(
                stdscr,
                0,
                bx + 2,
                f" {title} ",
                curses.color_pair(_CP_TITLE) | curses.A_BOLD,
            )
            _safe_addstr(
                stdscr,
                h - 2,
                bx,
                _glyph("bl") + _glyph("hline") * (content_w - 2) + _glyph("br"),
                fa,
            )

            hints = (
                "↑↓ Scroll  ←→ Pan  / Search  n/N Match  g/G Top/Bottom  q/Esc Close"
            )
            _safe_addstr(
                stdscr,
                h - 1,
                max(0, (w - len(hints)) // 2),
                hints,
                curses.color_pair(_CP_HINT) | curses.A_DIM,
            )

            for i in range(max_lines):
                _safe_addstr(stdscr, i + 1, bx, _glyph("vline"), fa)
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
                _safe_addstr(stdscr, i + 1, bx + content_w - 1, _glyph("vline"), fa)

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
            elif key == "/":
                got = _tui_prompt_str("Search", query)
                if got is not None and got.strip():
                    query = got.strip()
                    hit = _match_lines(lines, query, top)
                    if hit is not None:
                        top = hit
            elif key == "n" and query:
                hit = _match_lines(lines, query, min(top + 1, len(lines) - 1))
                if hit is not None:
                    top = hit
            elif key == "N" and query:
                hit = _match_lines(lines, query, max(top - 1, 0), reverse=True)
                if hit is not None:
                    top = hit
            elif key == curses.KEY_MOUSE:
                try:
                    _mid, _mx, _my, _z, bstate = curses.getmouse()
                except curses.error:
                    bstate = 0
                if bstate & curses.BUTTON4_PRESSED:
                    top = max(0, top - 3)
                elif bstate & curses.BUTTON5_PRESSED:
                    top = min(last_top, top + 3)
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
