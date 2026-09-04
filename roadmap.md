# Roadmap

- [x] Extract `GridMenu`, pagers, and prompts from existing CLI apps.
- [x] Investigate Windows terminal support (`msvcrt`) for raw TTY.

### Consumer Updates
When a roadmap item is completed, ensure the following dependent applications are bumped or verified:
- [x] `CalibreQuarry`
- [x] `Lattice`
- [x] `Bindery` (pins vir-tui to an exact commit by policy — bump the pin deliberately)

## Phase 2: Core Generalization & Integration Fixes
*Based on the post-extraction research report.*

- [x] **Decouple Menus**: Remove hardcoded Lattice sections (`_MAIN_SECTIONS`, `_LIB_SECTIONS`) and aliases from `vir-tui`.
- [x] **Dynamic Fallback**: Generalize `tui_select` to accept sections, aliases, and letter keys, and automatically build the text fallback menu if curses is unavailable, rather than relying on static Lattice maps.
- [x] **Unicode Prompt Fix**: Revert `getch()` to `get_wch()` in `_tui_prompt_str` so multibyte characters work again (critical for CalibreQuarry search).
- [x] **Narrow Pager Crash**: Enforce `visible_w = max(1, content_w - 4)` in `_tui_page` to prevent slicing errors on small windows.
- [x] **API Standardization**: Clean up `__init__.py` to export public (non-underscored) methods, remove the shadowed `prompts.py` file or merge it cleanly, and ensure consumers aren't relying on private methods like `_Cancelled`.
- [x] **Test Coverage**: Write `pytest` coverage for formatters, text fallback mapping logic, and pager geometry calculations in the currently empty `tests/` directory.

### Consumer Integration (Post-Phase 2)
- [x] **Lattice**: Remove the duplicate ~1,267-line `tui.py` in Lattice's codebase and properly delegate to `vir-tui`'s generalized `tui_select`.
- [x] **CalibreQuarry**: Update imports to use the public `vir-tui` API and pass its aliases/keys into the new generalized `tui_select` to restore its text fallback mode.

## Phase 3: Consumer-Driven Primitives
*From the 2026-08 cross-app TUI survey (CalibreQuarry, Lattice, Bindery): what hosts still hand-roll, duplicate, or mirror.*

- [x] **ProgressBox**: First-class curses progress widget (`progress_box()` / `ProgressBox`) — session-screen-aware, throttled redraws, tqdm-like `update`/`set_description`/`close`, context-manager support, plain-text fallback without a session. Lattice was mirroring `_TUI_BOX_W` and the `_CP_FRAME`/`_CP_HEADER` pair ids by hand and reimplementing the whole box in `lattice/utils.py`, which breaks silently whenever vir-tui restyles. The `CP_*` color-pair constants are now public for advanced hosts.
- [x] **interactive_session()**: Context manager owning the open-screen / degrade-to-text / KeyboardInterrupt / close-screen boilerplate that CalibreQuarry and Lattice each duplicated in `interactive_menu()`.
- [x] **Prompt primitives**: `prompt_float(label, default, lo, hi)` (CalibreQuarry hand-rolled its rating loop; Lattice loops tool/threshold choices), `prompt_path(label, default, must_exist)` (both apps hand-rolled path-existence loops), `confirm(label, default, danger)` (CalibreQuarry's double `ask_yn` destructive gates), and public `out_note(path)` (both consumers duplicated vir-tui's private `_out_note` verbatim).
- [x] **Pager search**: `/` opens a query prompt and `n`/`N` jump to the next/previous match (case-insensitive, wrapping) in `tui_page` — long audit/catalog reports are the primary artifact of every host.
- [x] **Mouse support**: click-to-select in `tui_select`, scroll-wheel paging in `tui_page` (needs `getmask`/`BUTTON*` plumbing and fallback no-ops). *(Shipped 2.3.0: the session screen and one-shot boot activate `mousemask` best-effort; a click moves the selection, a double-click selects, the wheel pages `tui_page` three lines per notch and navigates `tui_select`. KEY_MOUSE events in prompts/pauses are inert by shape, so no fallback code was needed.)*
- [x] **Type-to-filter**: incremental narrowing in `tui_select` for menus with 15+ items (CalibreQuarry's main menu crossed that line in 3.21.0). *(Shipped 2.3.0: printable characters type a casefold containment filter, shown in the hints line with a visible/total count; backspace edits, Esc clears then quits, Enter selects from the narrowed view. Below `_FILTER_MIN_ITEMS` (15) every key keeps its simple meaning. Matching is the pure `_filter_visible()` helper, unit-tested.)*
- [x] **Theme overrides**: let hosts remap color pairs or box glyphs per app instead of mirroring ids (only needed once a host actually wants a distinct look). *(Shipped 2.3.0: `configure_theme(color_pairs=..., glyphs=...)` maps the six semantic pair names and fourteen glyph names; unknown names raise ValueError instead of silently half-restyling. All five widgets draw through `_glyph()`, and pair overrides apply at color init.)*

