# vir-tui API

The full exported surface of `vir_tui`, with the contract each name carries. Every curses-backed name degrades to plain text without a TTY or the `curses` module; nothing here writes outside the terminal. Version sync: this file documents the surface as of the version in `VERSION`.

## Sessions

- **`interactive_session()`** — context manager owning the curses screen lifecycle: opens the session (yielding the screen, or `None` when the terminal can't support one and the whole session degrades to text), always closes on exit, and re-raises `KeyboardInterrupt` after cleanup so hosts keep mapping it to exit code 130.
- **`tui_active()`** — `True` while a curses surface owns the terminal (an open session, or a one-shot widget mid-run). Gate host-side ANSI printing and progress handling on it.
- **`open_screen()`** — start the session screen manually. Returns the screen, or `None` when curses can't start (including on interpreters built without curses). Calling `interactive_session()` instead is almost always right.
- **`close_screen()`** — end the session screen. Idempotent and safe after a mid-session degrade; a real session ending also flips `text_mode()` back to `True`.
- **`session_screen()`** — the persistent curses screen an open session owns, else `None`. Publish it to host-drawn widgets.
- **`text_mode()`** — `True` when the session runs without curses (no TTY, no curses module, or a mid-session degrade). Pick text-only affordances with it.
- **`reset_terminal()`** — best-effort `stty sane` for a terminal curses engaged. A terminal curses never touched is left alone.

## Menu

- **`tui_select(title, sections, hints=..., aliases=None, letter_keys=None)`** — full-screen arrow-key menu. `sections` is a list of `(header, items)`; returns the chosen `(section_index, item_index)`, or `None` on quit/Esc. Menus taller than the terminal scroll in a viewport that follows the selection, with an `item i/N` counter in the hints. Type-to-filter arms at 15+ entries: printable characters narrow the view (backspace edits, Esc clears then quits, Enter selects). `aliases` and `letter_keys` apply to the numbered text fallback only; inside curses, navigation is arrows, mouse, and the filter. On interpreters without curses the call degrades to the text menu and returns the same shapes, plus the string sentinels **`FALLBACK`** (`"fallback"`: curses died mid-menu, re-enter; `text_mode()` is True from then on) and **`INVALID`** (`"invalid"`: unmatched text choice, re-ask).
- **`box_menu(title, sections)`** — the plain double-line text menu the fallback renders.
- **`build_fallback(sections, aliases=None, letter_keys=None)`** — the fallback's `(display, mapping, max_n)`: letter keys become fixed choices (a digit letter key raises `ValueError`; they collide with the auto numbers), everything else is auto-numbered.
- **`fallback_input(prompt, mapping)`** — one text-menu prompt; returns the mapping value, `None` on EOF (treated as quit), or `INVALID`. `KeyboardInterrupt` propagates so Ctrl-C exits 130 like the curses menu.

## Pager

- **`tui_page(title, content)`** — scrollable, pannable pager for long text: arrows scroll, `←→` pan (8 columns), `/` search with `n`/`N` match jumping (wrap-around), matched spans highlighted, and a `line i/N · M matches` indicator in the hints; `g`/`G` top/bottom, mouse wheel pages, `q`/Esc/Enter closes. Tab stops expand; `\r` and `\x00` frames are stripped. Without curses: prints and pauses.

## Progress

- **`progress(total, desc="")`** — the session-aware factory: a `ProgressBox` drawing into the session screen while a TUI session is active, the sanctioned `tqdm` re-export (real tqdm when installed, the stub otherwise) in text mode. Replaces the IN_TUI-style dispatch hosts used to hand-roll.
- **`progress_box(total, desc="")`** — `ProgressBox` factory matching tqdm's `(total, desc)` shape. Draws into the session screen when one exists; without one it prints carriage-returned text on a TTY and stays silent when piped. Throttled redraws; the final state always lands (including on short runs via `close()`).
- **`ProgressBox`** — the widget itself: `update(n=1)`, `set_description(desc)`, `close()`, context-manager support. Progress is cosmetic: draw failures never kill the mode.

## Prompts

All raise **`CancelledError`** when the user cancels (Esc in the TUI, Ctrl-C/EOF at a text prompt), except `_prompt_str`-shaped internals. A multi-prompt handler aborts as one unit.

- **`ask(label, default)`** — one string prompt; returns the entered value (default on bare Enter).
- **`ask_yn(label, default="N")`** — yes/no.
- **`confirm(label, default=False, *, danger=False)`** — yes/no gate for destructive actions; `danger` prefixes the label and defaults to No, so a bare Enter never destroys anything.
- **`prompt_int(label, default)`** — re-asks until numeric.
- **`prompt_float(label, default, lo=None, hi=None)`** — re-asks with a reason on non-numeric or out-of-range input.
- **`prompt_out(label, default)`** — output path: expands `~`, stays relative otherwise.
- **`prompt_path(label, default="", *, must_exist=True)`** — absolute path prompt with a built-in existence loop.
- **`out_note(path)`** — "Report written to ..." footer text, or `""`.
- **`notify(msg)`** — a notice the user must see before the next menu redraw (paged in curses, printed in text).
- **`flash(msg)`** — a one-line status notice on the hints row; any key dismisses it. For acknowledgements whose weight does not justify `notify()`'s full-screen pager. Prints in text mode.
- **`pause()`** — wait for user acknowledgement before redrawing (the curses "Press Enter" box, or an input() line in text mode).

## Capture

- **`run_with_capture(title, func, *args, footer="", **kwargs)`** — run `func` with stdout/stderr captured, then page the result. Exceptions become a paged `[Error]` traceback (never a raw crash with the screen stuck); `KeyboardInterrupt` becomes `[Cancelled]`; the footer is suppressed when the run died. Terminal teardown is gated on curses having engaged.
- **`capture_output()`** — the raw stdout/stderr redirect context manager yielding `(out, err)` string buffers.

## Theming and host-drawn widgets

- **`configure_theme(*, color_pairs=None, glyphs=None)`** — host-level remapping, call once at startup. `color_pairs` maps the six semantic pair names to `(fg, bg)` curses color ints (applied at the next screen open); `glyphs` maps the fourteen glyph names to single characters (immediate). Unknown names and wrong-shaped values raise `ValueError` before anything is applied.
- **`CP_FRAME`, `CP_TITLE`, `CP_HEADER`, `CP_ITEM`, `CP_SELECTED`, `CP_HINT`** — public color-pair ids for hosts drawing their own widgets into the session screen. Ids 1-6 are re-initialized at every screen open and are reserved: use these constants as-is or pick ids 7+ for private pairs.
- **`safe_addstr(stdscr, y, x, text, attr)`** — the out-of-bounds-safe write every widget here uses, published for host-drawn widgets.

## Formatters (`vir_tui.core`, re-exported)

- **`color(text, code)`**, **`info(msg)`**, **`success(msg)`**, **`warn(msg)`**, **`error(msg)`**, **`dry_run(msg)`** — ANSI styling gated on `NO_COLOR` and TTY detection.
- **`print_header(title)`**, **`print_summary(stats)`** — report framing.
- **`tqdm`** — the real tqdm when the environment has it, a minimal stdlib stub otherwise (iteration counting, `update`/`close`/`set_description`, `write`; no context-manager protocol).
