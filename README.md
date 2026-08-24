# vir-tui

A lightweight, terminal UI primitive library for the VirInvictus CLI toolchain.

Provides a raw TTY event loop, a grid-based menu renderer, robust cross-platform ANSI colors, input prompt lifecycles, and a fallback progress bar wrapper for CLI applications that run headless but offer an interactive terminal interface.

Powers [CalibreQuarry](https://github.com/VirInvictus/CalibreQuarry) and [Lattice](https://github.com/VirInvictus/Lattice).

`Python · stdlib`

## Features

- **GridMenu**: A 2D navigable menu system that reads raw TTY keystrokes (no `curses` required).
- **Formatters**: Consistent `success`, `info`, `warn`, `error` styling across apps.
- **Prompts**: Interactive inputs with input clearing (`ask_yn`, `prompt_int`, `prompt_out`).
- **Capture**: `run_with_capture` wrapper for redirecting stdout/stderr into a temporary scrolling buffer while a background task runs, rendering a header/footer on top.

## License

GPL-3.0-or-later.
