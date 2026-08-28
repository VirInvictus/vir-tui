# 2.2.0 (2026-08-27)
Phase 3 — consumer-driven primitives, from the cross-app TUI survey (CalibreQuarry, Lattice, Bindery).
- **Feature**: `text_mode()` — public curses-status accessor (True when running without curses), so hosts stop poking the private `_USE_CURSES` global.
- **Feature**: `progress_box()` / `ProgressBox` — first-class curses progress widget: session-screen-aware, throttled redraws, tqdm-like `update`/`set_description`/`close`, context-manager support, and a plain-text fallback (carriage-returned line on a tty; silent when piped) instead of starting a screen of its own. Replaces Lattice's hand-mirrored `_TUIPbar`. The `CP_*` color-pair constants are now public for hosts drawing their own widgets.
- **Feature**: `interactive_session()` context manager owning the open-screen / degrade-to-text / close-screen boilerplate; KeyboardInterrupt is re-raised after cleanup so hosts keep mapping it to exit code 130. Adopts the duplicated `interactive_menu()` scaffolding from CalibreQuarry and Lattice.
- **Feature**: Prompt primitives — `prompt_float(label, default, lo, hi)` with bounded re-asking, `prompt_path(label, default, must_exist)` with existence loops built in, `confirm(label, default, danger=True)` for destructive gates, and public `out_note(path)` (both consumers had copied the private `_out_note` verbatim).
- **Feature**: Results-pager search — `/` opens a query prompt, `n`/`N` jump to the next/previous case-insensitive match with wrap-around; hints line updated. Matching logic is the pure `_match_lines()` helper (unit-tested).
- **Tests**: Suite grew from 3 to 13 tests covering the new primitives (degrade path, KI re-raise, prompt validation loops, match wrap semantics, ProgressBox fallback safety).
- **Consumers**: `Lattice` 4.17.0 (drops its mirrored progress box), `CalibreQuarry` 3.22.0 (adopts the session CM + prompt primitives), `Bindery` 0.19.1 (vir-tui pin bumped deliberately per its policy).

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
