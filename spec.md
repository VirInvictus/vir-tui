# vir-tui Specification

1. **Domain**: Terminal UI rendering and input capturing for VirInvictus Python CLI applications.
2. **Dependencies**: `stdlib` only. If `tqdm` is available in the consumer's environment, `vir_tui` re-exports it; otherwise, it exports a minimal stub.
3. **Architecture**:
   - `core.py`: ANSI state logic, color formats, `tqdm` handling (the real tqdm is re-exported when installed, a styled fallback otherwise).
   - `menu.py`: everything interactive —
     - the curses arrow-key menu (`tui_select`, sections/aliases/letter keys, auto-generated typed-input fallback via `build_fallback`),
     - the scrollable, pannable results pager (`tui_page`) with `/` search and `n`/`N` match jumping (pure `_match_lines` helper),
     - boxed prompts (`ask`, `ask_yn`, `confirm`, `prompt_int`, `prompt_float`, `prompt_out`, `prompt_path`) and the `out_note` report footer,
     - the progress widget (`progress_box()` / `ProgressBox`) drawing into the session screen with a pipe-safe text fallback,
     - the session lifecycle (`open_screen`/`close_screen`, `interactive_session`, `session_screen`, `text_mode`),
     - theme overrides (`configure_theme(color_pairs=..., glyphs=...)`): hosts remap the six semantic color pairs (applied at the next color init) and the fourteen glyphs (immediate) instead of mirroring private ids; unknown names raise `ValueError`,
     - best-effort mouse support: the session activates the curses mouse mask when the terminal offers it (click moves/selects in `tui_select`, wheel navigates and scrolls the pager); without it, everything degrades silently to keyboard-only,
     - type-to-filter in `tui_select` on menus of `_FILTER_MIN_ITEMS` (15)+ entries: printable keys narrow the view incrementally; below the threshold keys keep their plain meanings,
     - `run_with_capture` for paging a mode's captured stdout/stderr.
   - Public style constants (`CP_FRAME` … `CP_HINT`) let hosts render their own widgets into the session screen without mirroring private ids.

4. **Guarantees**:
   - Must fail gracefully and degrade if `sys.stdout` is not a TTY: every widget has a plain-text fallback (menus become numbered typed lists, the pager prints, progress stays silent when piped).
   - Generic by contract: no host-domain menus or strings; hosts pass their own sections/aliases/letter keys to `tui_select`.
