# vir-tui Specification

1. **Domain**: Terminal UI rendering and input capturing for VirInvictus Python CLI applications.
2. **Dependencies**: `stdlib` only. If `tqdm` is available in the consumer's environment, `vir_tui` re-exports it; otherwise, it exports a minimal stub.
3. **Architecture**:
   - `core.py`: ANSI state logic, color formats, `tqdm` handling (the real tqdm is re-exported when installed, a minimal fallback otherwise). Color output drops to plain text while a curses surface owns the terminal (`tui_active()`), so hosts printing through `color()`/`info()` cannot inject ANSI under a live screen.
   - `menu.py`: everything interactive:
     - the curses arrow-key menu (`tui_select`, sections/aliases/letter keys, auto-generated typed-input fallback via `build_fallback`; aliases and letter keys steer the text fallback only, while the curses menu navigates by arrows, mouse, and the filter). Menus taller than the terminal scroll in a viewport that follows the selection, with an `item i/N` counter in the hints,
     - the scrollable, pannable results pager (`tui_page`) with `/` search, `n`/`N` match jumping (pure `_match_lines` helper), highlighted match spans, and a `line i/N · M matches` indicator,
     - boxed prompts (`ask`, `ask_yn`, `confirm`, `prompt_int`, `prompt_float`, `prompt_out`, `prompt_path`), the `out_note` report footer, the one-line `flash()` notice, and public `pause()`,
     - the progress widgets: session-aware `progress(total, desc)` (a `ProgressBox` during a session, the sanctioned tqdm re-export in text mode) and `progress_box()` / `ProgressBox` drawing into the session screen with a pipe-safe text fallback,
     - the session lifecycle (`open_screen`/`close_screen`, `interactive_session`, `session_screen`, `text_mode`),
     - theme overrides (`configure_theme(color_pairs=..., glyphs=...)`): hosts remap the six semantic color pairs (applied at the next color init) and the fourteen glyphs (immediate) instead of mirroring private ids; unknown names raise `ValueError`,
     - best-effort mouse support: the session activates the curses mouse mask when the terminal offers it (click moves/selects in `tui_select`, wheel navigates and scrolls the pager); without it, everything degrades silently to keyboard-only,
     - type-to-filter in `tui_select` on menus of `_FILTER_MIN_ITEMS` (15)+ entries: printable keys narrow the view incrementally; below the threshold keys keep their plain meanings,
     - `run_with_capture` for paging a mode's captured stdout/stderr.
   - Public style constants (`CP_FRAME` … `CP_HINT`) let hosts render their own widgets into the session screen without mirroring private ids. Ids 1-6 are re-initialized at every screen open and are reserved: hosts use the constants as-is or pick ids 7+ for private pairs. `safe_addstr`, the out-of-bounds-safe write every widget uses, is public for the same audience.
   - The text fallback's sentinels are public constants: `FALLBACK` (`"fallback"`, curses died mid-menu, re-enter) and `INVALID` (`"invalid"`, unmatched text choice, re-ask); the string values keep working.
   - The package is fully type-annotated and carries a `py.typed` marker.

4. **Guarantees**:
   - Must fail gracefully and degrade if `sys.stdout` is not a TTY: every widget has a plain-text fallback (menus become numbered typed lists, the pager prints, progress stays silent when piped).
   - Generic by contract: no host-domain menus or strings; hosts pass their own sections/aliases/letter keys to `tui_select`.
   - Widths are measured in terminal display cells (East Asian wide characters take 2, combining marks 0), so CJK labels pad, pan, and truncate to what the terminal actually shows.
