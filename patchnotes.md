# 2.4.0 (2026-09-14)
Terminal-safety release from THE FINAL AUDIT: the three HIGHs (a nested-curses corruption, the j/k filter hijack, the curses-less NameError), the terminal-safety fixes, the honesty batch, and the PyPI storefront. Additive to consumers; no API breaks (the retired `_Cancelled` export now warns instead of vanishing, removal at 3.0).

- **Fix: nested curses calls no longer tear down the live session (HIGH).** Any nested widget call while a one-shot `_with_screen` boot was active (the pager's `/` search prompt, a notice inside `prompt_path`) re-entered `curses.wrapper`, whose teardown ran `endwin()` on the live outer widget and left the terminal in cooked/echo mode. The one-shot boot now publishes its screen into `_SCREEN` for the wrapper's duration, so nested widgets reuse it and `session_screen()`/`ProgressBox` see it mid-run.
- **Fix: j/k type the filter on 15+ menus (HIGH).** The documented contract is "printable characters type a filter", but j/k hit the navigation branches first: typing "jazz" moved the cursor on the j and narrowed to "azz". On filter-capable menus j/k are filter text and the arrows carry navigation; below the threshold j/k keep their classic meaning, and q/Q keep their quit guard.
- **Fix: `open_screen` degrades on curses-less interpreters (HIGH).** The documented "returns None" path used to crash first: its `except` clause evaluated the unbound `curses` name. It now mirrors `close_screen`'s guard.
- **Fix: `configure_theme` validates values before applying anything.** A wrong-shaped pair value used to raise `TypeError` past `open_screen`'s catch (terminal left initscr'd in cbreak/noecho), and a typed-but-wrong value aborted the apply loop half-way. Pairs must be `(fg, bg)` int tuples and glyphs single characters; one pair a terminal cannot render no longer aborts the rest at color init.
- **Fixes: the small filter/terminal batch.** Esc clearing the filter widens the menu again; the pager strips `\r` (tqdm frames) alongside `\x00`; terminals shorter than the menu clamp the box at the top edge instead of going negative and blanking; `text_mode()` is `True` again after `close_screen` (prompts were being steered at a dead screen); `ProgressBox.close()` forces the final draw on runs that ended short of total.
- **Fix: widths are measured in display cells, not code points.** New `unicodedata`-backed helpers back every width site, so CJK labels pad, center, pan, and truncate to what the terminal actually shows, and the prompt cursor no longer desyncs. Border rows moved to a single shared helper (they were hand-rolled in four widgets).
- **Honesty.** The `block`/`block_light` glyphs are wired into both progress-bar renders, so the documented fourteen-glyph contract is real (Brandon's call: wire, not drop); `vir_tui._Cancelled` still resolves but emits `DeprecationWarning` (removal at 3.0); the unexported, unreferenced `MAGENTA`/`DIM` ANSI constants are gone; `reset_terminal` gained its docstring and a curses-engagement gate (pure-text sessions no longer get an unconditional `stty sane`); `build_fallback` rejects digit letter keys with `ValueError` instead of colliding silently with the auto numbers; `confirm(danger=True)` renders "DANGER: "; `letter_keys`/`aliases` are documented as text-fallback-only; color pairs 1-6 are documented as reserved.
- **Packaging/presentation.** README rebuilt as the real PyPI storefront (Install section with the load-bearing Python 3.14+ floor, a usage example, an accurate consumer line); pyproject gained keywords, non-license classifiers, and `[project.urls]` (decision 62's republish rides this release); publish.yml SHA-pins all three actions (the mutable `release/v1` branch was pinning the `id-token: write` job), adds `twine check --strict`, a wheel smoke-install, and a create-release job minting GitHub Releases from the tag's verbatim message; GitHub description/topics/homepage set; the v2.3.0 Release backfilled; API.md added (the full exported surface, including the seven exports previously documented nowhere).
- **Tests:** suite grew from 18 to 38 (one-shot screen publish/restore and pager-search reuse, j/k dispatch plus small-menu and q/Q guards, curses-less degrade, theme value validation and per-pair color init, Esc recompute, `\r` strip, short-terminal clamp, text_mode reset, close force-draw, cell-width helpers and CJK rendering, the deprecation warning, digit-key rejection, block-glyph wiring, the reset_terminal gate). Test-story reminder: `PYTHONPATH=src python -m pytest tests/` from the repo root.
- **Consumers:** additive release; CalibreQuarry, lattice-music, and bindery-cli hold `>=2.3.0` floors and adopt at their own releases. The only removed names (`MAGENTA`, `DIM`) were unexported and referenced by no consumer (verified); no other surface changed shape.

# 2.3.0 (2026-09-04)
Phase 3 tail: the three consumer-driven affordances, plus a test-story trap documented.

- **Feature: mouse support.** The session screen (and the one-shot boot) activates the curses mouse mask best-effort; a terminal without mouse support degrades silently to keyboard-only. In `tui_select` a click moves the selection, a double-click selects, and the wheel navigates; in `tui_page` the wheel scrolls three lines per notch. KEY_MOUSE events reaching prompts/pauses are inert by shape, so no per-widget fallback code was needed.
- **Feature: type-to-filter in `tui_select`.** On menus of `_FILTER_MIN_ITEMS` (15)+ entries, printable characters type a casefold containment filter that narrows the view incrementally; the hints line shows the query and a visible/total count. Backspace edits, Esc clears the filter (then quits), Enter selects from the narrowed view, and the wheel navigates it. Below the threshold every key keeps its simple meaning: small menus are unchanged. Matching is the pure `_filter_visible()` helper (unit-tested).
- **Feature: theme overrides.** `configure_theme(color_pairs=..., glyphs=...)` lets hosts remap the six semantic color pairs (frame/title/header/item/selected/hint, applied at the next color init) and the fourteen box/pointer glyphs (effective immediately) instead of mirroring private ids or forking widgets. Unknown names raise ValueError: a silent typo would leave widgets half-restyled. All five widgets draw through the new `_glyph()` lookup.
- **Tests:** suite grew from 13 to 18 (override application + validation, glyph-default coverage, filter narrowing, threshold guarantee). Test-story note: run the suite as `PYTHONPATH=src python -m pytest tests/`: a bare pytest from the repo root silently imports the stale ambient site-packages install and tests nothing that changed (the lattice-music trap, now documented here too).

# 2.2.0 (2026-08-27)
Phase 3, consumer-driven primitives, from the cross-app TUI survey (CalibreQuarry, Lattice, Bindery).
- **Feature**: `text_mode()`, a public curses-status accessor (True when running without curses), so hosts stop poking the private `_USE_CURSES` global.
- **Feature**: `progress_box()` / `ProgressBox`, a curses progress widget: session-screen-aware, throttled redraws, tqdm-like `update`/`set_description`/`close`, context-manager support, and a plain-text fallback (carriage-returned line on a tty; silent when piped) instead of starting a screen of its own. Replaces Lattice's hand-mirrored `_TUIPbar`. The `CP_*` color-pair constants are now public for hosts drawing their own widgets.
- **Feature**: `interactive_session()` context manager owning the open-screen / degrade-to-text / close-screen boilerplate; KeyboardInterrupt is re-raised after cleanup so hosts keep translating it into their own exit code (conventionally 130). Adopts the duplicated `interactive_menu()` scaffolding from CalibreQuarry and Lattice.
- **Feature**: Prompt primitives: `prompt_float(label, default, lo, hi)` with bounded re-asking, `prompt_path(label, default, must_exist)` with existence loops built in, `confirm(label, default, danger=True)` for destructive gates, and public `out_note(path)` (both consumers had copied the private `_out_note` verbatim).
- **Feature**: Results-pager search: `/` opens a query prompt, `n`/`N` jump to the next/previous case-insensitive match with wrap-around; hints line updated. Matching logic is the pure `_match_lines()` helper (unit-tested).
- **Tests**: Suite grew from 3 to 13 tests covering the new primitives (degrade path, KI re-raise, prompt validation loops, match wrap semantics, ProgressBox fallback safety).
- **Consumers**: `Lattice` 4.17.0 (drops its mirrored progress box), `CalibreQuarry` 3.22.0 (adopts the session CM + prompt primitives), `Bindery` 0.19.1 (vir-tui pin bumped deliberately per its policy).

# 2.1.0 (2026-08-25)
- **Feature**: Added `session_screen()` accessor exposing the persistent curses screen, so host apps can route their own progress widgets into the session screen instead of starting their own.

# 2.0.1 (2026-08-25)
- **Chore**: packaging-only bump (VERSION + pyproject), no behavior change. Recorded late so the version chain here is complete: the bump shipped without an entry, which is the drift this note repairs.

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
