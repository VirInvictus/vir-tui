# vir-tui

A lightweight, terminal UI primitive library for the VirInvictus CLI toolchain.

Provides a raw TTY event loop, a grid-based menu renderer, robust cross-platform ANSI colors, input prompt lifecycles, and a fallback progress bar wrapper for CLI applications that run headless but offer an interactive terminal interface.

Powers [CalibreQuarry](https://github.com/VirInvictus/CalibreQuarry) and [Lattice](https://github.com/VirInvictus/Lattice).

`Python · stdlib`

## Features

- **Menus**: full-screen arrow-key `tui_select` (sections, aliases, letter keys) with an automatic numbered text fallback when curses is unavailable; a scrollable, pannable results pager (`tui_page`) with `/` search and `n`/`N` match jumping.
- **Filtering**: on menus of 15+ entries, typing narrows the view incrementally (case-insensitive; backspace edits, Esc clears); small menus keep the classic single-key semantics.
- **Mouse**: click moves the selection, double-click selects, and the wheel scrolls menus and pages — best-effort, degrading silently to keyboard-only.
- **Theming**: `configure_theme(color_pairs=..., glyphs=...)` lets a host remap the six semantic color pairs and the box glyphs per app, instead of mirroring ids or forking widgets.
- **Progress**: `progress_box()` — a session-screen-aware curses progress box with a tqdm-like API and a pipe-safe text fallback.
- **Sessions**: `interactive_session()` context manager owning the curses screen lifecycle (open, degrade, close, KeyboardInterrupt cleanup).
- **Formatters**: consistent `success`, `info`, `warn`, `error` styling across apps.
- **Prompts**: `ask`, `ask_yn`, `confirm`, `prompt_int`, `prompt_float`, `prompt_out`, `prompt_path`, plus `out_note` for "where did my report go" footers.
- **Capture**: `run_with_capture` wrapper for redirecting stdout/stderr into a temporary scrolling buffer while a background task runs, rendering a header/footer on top.

## Support

If vir-tui's useful to you and you'd like to chip in:

- liberapay · [liberapay.com/bdkl](https://liberapay.com/bdkl/)
- bitcoin
  ```
  bc1qkge6zr45tzqfwfmvma2ylumt6mg7wlwmhr05yv
  ```

## License

GPL-3.0-or-later.
