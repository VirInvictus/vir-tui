# vir-tui

A lightweight, terminal UI primitive library for the VirInvictus CLI toolchain.

Provides a curses-based interactive menu with type-to-filter and mouse support, a scrollable results pager, ANSI colors with `NO_COLOR` and TTY gating, boxed input prompt lifecycles, theme overrides, and a session-aware progress box for CLI applications that run headless but offer an interactive terminal interface.

Used by [CalibreQuarry](https://github.com/VirInvictus/CalibreQuarry) and [lattice-music](https://github.com/VirInvictus/lattice-music) for their full interactive sessions, and by [bindery-cli](https://github.com/VirInvictus/bindery-cli) for its formatters and the `tqdm` re-export.

`Python · stdlib`

## Install

```
pip install vir-tui
```

Requires **Python 3.14+**: the package uses PEP 758 unparenthesized exception groups, which are a `SyntaxError` on older interpreters. There are no dependencies; when `tqdm` is installed it is re-exported, otherwise a minimal stub is provided. The package is fully type-annotated and ships a `py.typed` marker.

## Usage

```python
import vir_tui

with vir_tui.interactive_session():  # owns the curses screen, or degrades to text
    while (choice := vir_tui.tui_select(
        "Library",
        [("Books", ["By title", "By author"]), ("Tools", ["Scan library", "Quit"])],
    )) not in ((1, 1), None):  # Quit, or q / Esc
        if choice == (1, 0):  # Tools > Scan library
            with vir_tui.progress_box(100, "Scanning") as bar:
                for _ in range(100):
                    bar.update()
        elif choice is not None:
            vir_tui.info(f"Picked {choice}")
```

Every widget degrades to plain text without curses or a TTY: menus become numbered typed lists, the pager prints, prompts read from stdin, and progress stays silent when piped.

## Features

- **Menus**: full-screen arrow-key `tui_select` (sections, aliases, letter keys) with an automatic numbered text fallback when curses is unavailable; tall menus scroll in a viewport that follows the selection, with an i/N counter; a scrollable, pannable results pager (`tui_page`) with `/` search, `n`/`N` match jumping, match highlighting, and a position indicator. `aliases` and `letter_keys` steer the numbered text fallback; inside curses, navigation is arrows, mouse, and the filter.
- **Filtering**: on menus of 15+ entries, typing narrows the view incrementally (case-insensitive; backspace edits, Esc clears); small menus keep the classic single-key semantics.
- **Mouse**: click moves the selection, double-click selects, and the wheel scrolls menus and pages; best-effort, degrading silently to keyboard-only.
- **Theming**: `configure_theme(color_pairs=..., glyphs=...)` lets a host remap the six semantic color pairs and the box glyphs per app, instead of mirroring ids or forking widgets. Color pairs 1-6 are reserved: hosts drawing their own widgets use the public `CP_*` constants or ids 7+ (with the published `safe_addstr` for out-of-bounds-safe writes).
- **Progress**: `progress(total, desc)` is session-aware (a curses progress box during a session, the tqdm re-export in text mode); `progress_box()` is the curses box by itself, with a tqdm-like API and a pipe-safe text fallback.
- **Sessions**: `interactive_session()` context manager owning the curses screen lifecycle (open, degrade, close, KeyboardInterrupt cleanup); `tui_active()` and `text_mode()` report the state, and the formatters drop ANSI while a session owns the terminal.
- **Formatters**: consistent `success`, `info`, `warn`, `error` styling across apps.
- **Prompts**: `ask`, `ask_yn`, `confirm`, `prompt_int`, `prompt_float`, `prompt_out`, `prompt_path`, plus `out_note` for "where did my report go" footers and `flash()` for one-line notices.
- **Capture**: `run_with_capture` wrapper for redirecting stdout/stderr into a temporary scrolling buffer while a background task runs, rendering a header/footer on top.

See [API.md](API.md) for the full exported surface and [spec.md](spec.md) for the contract.

## Support

If vir-tui's useful to you and you'd like to chip in:

- liberapay · [liberapay.com/bdkl](https://liberapay.com/bdkl/)
- bitcoin
  ```
  bc1qkge6zr45tzqfwfmvma2ylumt6mg7wlwmhr05yv
  ```

## License

GPL-3.0-or-later.
