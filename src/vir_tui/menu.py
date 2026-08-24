import curses
import os
import subprocess
import sys

HAVE_CURSES = True
_USE_CURSES = HAVE_CURSES and sys.stdin.isatty()
_SCREEN = None

def _reset_terminal() -> None:
    if _SCREEN is not None:
        return
    if not sys.stdin.isatty():
        return
    try:
        subprocess.run(["stty", "sane"], stdin=sys.stdin, check=False)
    except Exception:
        pass

_CP_FRAME = 1
_CP_TITLE = 2
_CP_HEADER = 3
_CP_ITEM = 4
_CP_SELECTED = 5
_CP_HINT = 6
_TUI_BOX_W = 46
_TUI_INNER = _TUI_BOX_W - 2

def _init_tui_colors() -> None:
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
    try:
        curses.curs_set(visibility)
    except curses.error:
        pass

def _safe_addstr(stdscr, y: int, x: int, text: str, attr: int) -> None:
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass

def _with_screen(fn):
    if _SCREEN is not None:
        return fn(_SCREEN)
    def _boot(stdscr):
        _init_tui_colors()
        return fn(stdscr)
    return curses.wrapper(_boot)

def _open_screen():
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        _init_tui_colors()
        return stdscr
    except curses.error:
        try:
            if not curses.isendwin():
                curses.endwin()
        except curses.error:
            pass
        return None

def _close_screen() -> None:
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
    global _USE_CURSES
    _USE_CURSES = False
    _close_screen()

def tui_select(title: str, sections: list, hints: str = "\u2191\u2193 Navigate  \u23ce Select  q Quit") -> tuple | None:
    BOX_W = _TUI_BOX_W
    INNER = _TUI_INNER
    flat = []
    for si, (_, items) in enumerate(sections):
        for ii in range(len(items)):
            flat.append((si, ii))
    def _draw(stdscr, cur: int) -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        bx = max(0, (w - BOX_W) // 2)
        fa = curses.color_pair(_CP_FRAME)
        box_h = 3
        sel_row = 3
        idx0 = 0
        for si, (hdr, items) in enumerate(sections):
            if si > 0: box_h += 1
            if hdr: box_h += 1
            if idx0 <= cur < idx0 + len(items):
                sel_row = box_h + (cur - idx0)
            idx0 += len(items)
            box_h += len(items)
        box_h += 1
        y = max(0, (h - box_h - 2) // 2)
        if y + sel_row >= h - 1:
            y = (h - 2) - sel_row
        _safe_addstr(stdscr, y, bx, "\u2554" + "\u2550" * INNER + "\u2557", fa)
        y += 1
        _safe_addstr(stdscr, y, bx, "\u2551", fa)
        _safe_addstr(stdscr, y, bx + 1, f" {title:^{INNER - 2}} ", curses.color_pair(_CP_TITLE) | curses.A_BOLD)
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
                _safe_addstr(stdscr, y, bx + 1, content, curses.color_pair(_CP_HEADER) | curses.A_BOLD)
                _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
                y += 1
            for ii, item in enumerate(items):
                if idx == cur:
                    content = f"  > {item}"
                    content += " " * (INNER - len(content))
                    attr = curses.color_pair(_CP_SELECTED) | curses.A_BOLD
                else:
                    content = f"    {item}"
                    content += " " * (INNER - len(content))
                    attr = curses.color_pair(_CP_ITEM)
                _safe_addstr(stdscr, y, bx, "\u2551", fa)
                _safe_addstr(stdscr, y, bx + 1, content, attr)
                _safe_addstr(stdscr, y, bx + BOX_W - 1, "\u2551", fa)
                y += 1
                idx += 1
        _safe_addstr(stdscr, y, bx, "\u255a" + "\u2550" * INNER + "\u255d", fa)
        y += 2
        hint_y = min(y, h - 1)
        _safe_addstr(stdscr, hint_y, bx, f" {hints:^{INNER - 2}} ", curses.color_pair(_CP_HINT) | curses.A_DIM)
        stdscr.refresh()
    def _run(stdscr) -> tuple | None:
        _curs_set(0)
        cur = 0
        while True:
            _draw(stdscr, cur)
            try:
                k = stdscr.getch()
            except curses.error:
                _degrade_to_text()
                return "fallback"
            if k == curses.KEY_RESIZE:
                continue
            if k in (ord("q"), ord("Q"), 27):
                return None
            if k in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif k in (curses.KEY_DOWN, ord("j")):
                cur = min(len(flat) - 1, cur + 1)
            elif k in (10, 13, curses.KEY_ENTER):
                return flat[cur]
    try:
        return _with_screen(_run)
    except curses.error:
        _degrade_to_text()
        return "fallback"
