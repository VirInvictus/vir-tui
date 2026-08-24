# Roadmap

- [x] Extract `GridMenu`, pagers, and prompts from existing CLI apps.
- [ ] Investigate Windows terminal support (`msvcrt`) for raw TTY.

### Consumer Updates
When a roadmap item is completed, ensure the following dependent applications are bumped or verified:
- [ ] `CalibreQuarry`
- [ ] `Lattice`

## Phase 2: Core Generalization & Integration Fixes
*Based on the post-extraction research report.*

- [ ] **Decouple Menus**: Remove hardcoded Lattice sections (`_MAIN_SECTIONS`, `_LIB_SECTIONS`) and aliases from `vir-tui`.
- [ ] **Dynamic Fallback**: Generalize `tui_select` to accept sections, aliases, and letter keys, and automatically build the text fallback menu if curses is unavailable, rather than relying on static Lattice maps.
- [ ] **Unicode Prompt Fix**: Revert `getch()` to `get_wch()` in `_tui_prompt_str` so multibyte characters work again (critical for CalibreQuarry search).
- [ ] **Narrow Pager Crash**: Enforce `visible_w = max(1, content_w - 4)` in `_tui_page` to prevent slicing errors on small windows.
- [ ] **API Standardization**: Clean up `__init__.py` to export public (non-underscored) methods, remove the shadowed `prompts.py` file or merge it cleanly, and ensure consumers aren't relying on private methods like `_Cancelled`.
- [ ] **Test Coverage**: Write `pytest` coverage for formatters, text fallback mapping logic, and pager geometry calculations in the currently empty `tests/` directory.

### Consumer Integration (Post-Phase 2)
- [ ] **Lattice**: Remove the duplicate ~1,267-line `tui.py` in Lattice's codebase and properly delegate to `vir-tui`'s generalized `tui_select`.
- [ ] **CalibreQuarry**: Update imports to use the public `vir-tui` API and pass its aliases/keys into the new generalized `tui_select` to restore its text fallback mode.
