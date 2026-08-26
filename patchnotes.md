# 2.1.0 (2026-08-25)
- **Feature**: Added `session_screen()` accessor exposing the persistent curses screen, so host apps can route their own progress widgets into the session screen instead of starting their own.

# 2.0.0 (2026-08-24)
- **Breaking**: Gutted hardcoded Lattice/CalibreQuarry domains (`_MAIN_SECTIONS`, `_LIB_SECTIONS`). Consumers must now provide their own tuples to `tui_select`.
- **Breaking**: Exported public API clean without underscores (e.g. `tui_select`, `ask`, `notify`, `reset_terminal`).
- **Feature**: `tui_select` now automatically builds text-mode fallback menus dynamically using `aliases` and `letter_keys` kwargs.
- **Fix**: Reverted `getch()` to `get_wch()` to fix a multibyte character search crash.
- **Fix**: Enforced `visible_w = max(1, content_w - 4)` in `_tui_page` to prevent slicing crashes on narrow terminals.
- **Maintenance**: Added `tests/` directory with `pytest` suite for core formatters.

# Patch Notes

## v1.0.0 (2026-08-23)

- **Feature:** Initial extraction from `CalibreQuarry` and `Lattice`.
- **Feature:** Standalone `GridMenu`, prompt wrappers, and ANSI formatters.
