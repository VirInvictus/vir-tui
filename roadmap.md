# Roadmap

- [x] Extract `GridMenu`, pagers, and prompts from existing CLI apps.
- [x] Investigate Windows terminal support (`msvcrt`) for raw TTY.

### Consumer Updates
When a roadmap item is completed, ensure the following dependent applications are bumped or verified:
- [x] `CalibreQuarry`
- [x] `Lattice`
- [x] `Bindery` (holds a PyPI floor like the other consumers; the exact-commit-pin era is retired, so bumps are additive at Bindery's own releases)

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

- [x] **ProgressBox**: a curses progress widget (`progress_box()` / `ProgressBox`) that draws into the session screen with throttled redraws, a tqdm-like `update`/`set_description`/`close` API, context-manager support, and a plain-text fallback when no session owns a screen. Lattice was mirroring `_TUI_BOX_W` and the `_CP_FRAME`/`_CP_HEADER` pair ids by hand and reimplementing the whole box in `lattice/utils.py`, which breaks silently whenever vir-tui restyles. The `CP_*` color-pair constants are now public for advanced hosts.
- [x] **interactive_session()**: Context manager owning the open-screen / degrade-to-text / KeyboardInterrupt / close-screen boilerplate that CalibreQuarry and Lattice each duplicated in `interactive_menu()`.
- [x] **Prompt primitives**: `prompt_float(label, default, lo, hi)` (CalibreQuarry hand-rolled its rating loop; Lattice loops tool/threshold choices), `prompt_path(label, default, must_exist)` (both apps hand-rolled path-existence loops), `confirm(label, default, danger)` (CalibreQuarry's double `ask_yn` destructive gates), and public `out_note(path)` (both consumers duplicated vir-tui's private `_out_note` verbatim).
- [x] **Pager search**: `/` opens a query prompt and `n`/`N` jump to the next/previous match (case-insensitive, wrapping) in `tui_page`; long audit/catalog reports are the primary artifact of every host.
- [x] **Mouse support**: click-to-select in `tui_select`, scroll-wheel paging in `tui_page` (needs `getmask`/`BUTTON*` plumbing and fallback no-ops). *(Shipped 2.3.0: the session screen and one-shot boot activate `mousemask` best-effort; a click moves the selection, a double-click selects, the wheel pages `tui_page` three lines per notch and navigates `tui_select`. KEY_MOUSE events in prompts/pauses are inert by shape, so no fallback code was needed.)*
- [x] **Type-to-filter**: incremental narrowing in `tui_select` for menus with 15+ items (CalibreQuarry's main menu crossed that line in 3.21.0). *(Shipped 2.3.0: printable characters type a casefold containment filter, shown in the hints line with a visible/total count; backspace edits, Esc clears then quits, Enter selects from the narrowed view. Below `_FILTER_MIN_ITEMS` (15) every key keeps its simple meaning. Matching is the pure `_filter_visible()` helper, unit-tested.)*
- [x] **Theme overrides**: let hosts remap color pairs or box glyphs per app instead of mirroring ids (only needed once a host actually wants a distinct look). *(Shipped 2.3.0: `configure_theme(color_pairs=..., glyphs=...)` maps the six semantic pair names and fourteen glyph names; unknown names raise ValueError instead of silently half-restyling. All five widgets draw through `_glyph()`, and pair overrides apply at color init.)*


## New findings 2026-09-12 (six-lens full audit; detail: audit/FULL-AUDIT-2026-09-12.md, Wave 12)

- [x] **HIGH: j/k are hijacked by navigation while type-to-filter is
      armed** (menu.py:771/774 dispatch before the filter branch; q got
      the not-query guard, j/k did not). Typing "jazz" moves the cursor
      and filters "azz". Guard both on the filter state + a unit test.
      *(Done 2026-09-14 in 2.4.0: on 15+ menus j/k are filter text and the
      arrows carry navigation; dispatch tests pin "jazz", small-menu j/k,
      and q's quit guard.)*
- [x] **HIGH: open_screen raises a double NameError on curses-less
      interpreters** (the except clause evaluates curses.error with the
      name unbound). First line: if not HAVE_CURSES: return None,
      mirroring close_screen. *(Done 2026-09-14 in 2.4.0, with the
      degrade path tested.)*
- [x] **LICENSE three-way mismatch (needs a Brandon ruling):** the
      LICENSE file is MIT; README + PyPI say GPL-3.0-or-later; pyproject
      has no license field. Stated intent is GPL - replace the LICENSE
      text with GPL-3.0-or-later and add license + classifier to
      pyproject. *(Done: LICENSE replaced and the license expression added
      in 6af9d49 (decision 62); the classifier is superseded by PEP 639,
      where the license expression carries the metadata and a license
      classifier is deprecated duplication. The PyPI half rides the 2.4.0
      republish.)*
- [x] **Terminal-safety fixes:** configure_theme validates names but not
      values (a bad tuple escapes mid-initscr leaving the terminal
      broken; validate at configure + widen _init_tui_colors' catch);
      run_with_capture runs stty sane on terminals curses never touched
      (gate on engagement); color-pair ids 1-6 have no reservation policy
      (document the reserve or add an allocator). *(Done 2026-09-14 in
      2.4.0: atomic value validation + per-pair try; the _CURSES_TOUCHED
      gate on reset_terminal/run_with_capture; the 1-6 reserve documented
      in spec and API.md.)*
- [x] **The hygiene quartet (still open, confirmed today):** git rm
      refactor.py (tracked one-off with hardcoded /home/bdkl paths);
      delete tag_message.txt; uv lock (records 2.1.0 vs 2.3.0); the
      roadmap's bindery exact-commit-pin line contradicts the retired
      policy. Patchnotes H1 restructure stays deferred to the next
      release entry. *(Done 2026-09-13: refactor.py removed from the
      tree, tag_message.txt deleted, uv.lock refreshed to 2.3.0, and
      the Bindery consumer line above rewritten for the retired pin
      policy.)*
- [ ] **Enhancement queue:** vir_tui.progress() factory absorbing the
      consumers' IN_TUI/_make_pbar machinery; session-aware color() +
      tui_active(); menu-loop contract cleanup (handle "fallback"/
      "invalid" in-library, publicize pause); deprecate the _Cancelled
      export; wire progress bars through _glyph("block") or drop the two
      dead glyph names; type-hint the public seven. *(Progress 2026-09-14:
      the _Cancelled deprecation and the glyph wiring landed in 2.4.0;
      the session-awareness unit, the additive FALLBACK/INVALID constants
      + public pause, and the type-hints are queued for 2.5.0 per
      Brandon's gate answers.)*
      *(Done 2026-09-14 in 2.5.0: progress() + session-aware color() +
      tui_active() shipped as one unit; FALLBACK/INVALID constants and
      public pause() landed additively; type-hints + py.typed done.)*
- [x] **GitHub presentation (workspace batch):** description is
      literally "a tui library" (replacement drafted); topics null;
      homepage should be the PyPI page; no Releases (v2.3.0 notes ready);
      README needs an Install section + usage example (it is the PyPI
      storefront). *(Done 2026-09-14: description, homepage, and ten
      topics applied; v2.3.0 Release backfilled and a create-release job
      added to publish.yml; README rebuilt with Install/usage/floor.)*

- [x] **DECIDED 2026-09-13: the license is GPL-3.0-or-later** (decision
      62) - replace the MIT LICENSE text with the standard GPL-3.0
      file, add `license = "GPL-3.0-or-later"` + the classifier to
      pyproject, and republish at the next release. *(Done: in-tree half
      6af9d49; classifier superseded per PEP 639; the republish rides the
      2.4.0 tag per Brandon's 2026-09-14 confirmation.)*

### Final audit 2026-09-13 (THE FINAL AUDIT: NEW findings, one line each; full detail in audit-final/vir-tui/FINAL-REPORT.md)
- [x] **HIGH (NEW): nested curses.wrapper corrupts the live outer session: any nested widget call while a one-shot _with_screen is active re-enters curses.wrapper, whose finally runs endwin() on a live loop; concrete path is `/` search in a one-shot tui_page (menu.py:32-44, trigger :1148-1152 → :908-915; same via notify() in prompt_path).** Fix: _boot publishes the one-shot stdscr into _SCREEN for the wrapper's duration.
- [x] **HIGH (CONFIRMED, Wave 12): j/k dispatch to navigation before the filter branch; only q/Q got the `not query` guard, so "jazz" moves the cursor and filters "azz" on 15+ menus (menu.py:771-776).** Guard + dispatch unit test + a rationale comment on the guard discipline.
- [x] **HIGH (CONFIRMED, Wave 12): open_screen double-NameError on curses-less interpreters (`except curses.error:` evaluates the unbound name); the documented "returns None" degrade crashes interactive_session (menu.py:47-69).** First line `if not HAVE_CURSES: return None`.
- [x] MED (done 2026-09-14, 2.4.0): configure_theme validates names, not values: wrong-shaped values raise TypeError past open_screen's curses.error catch, leaving the terminal initscr'd in cbreak/noecho with no endwin; typed-but-wrong values abort the pair loop half-way (menu.py:334-395). Validate at configure time + per-pair try.
- [x] MED (done 2026-09-14, 2.4.0): Esc "clears the filter" resets query without recomputing visible (menu.py:780-785); pager strips \x00 but not \r (tqdm frames scramble rendering, menu.py:1049); sub-terminal-height menus go negative and blank silently (menu.py:648-652); text_mode() stale after close_screen (menu.py:99-103); ProgressBox "final update always draws" false on short runs (close() never forces).
- [x] MED (done 2026-09-14, 2.4.0): Every width computation is code-point based, not cell-based: CJK labels overflow the box, desync the prompt cursor, under-measure pager pan ranges (menu.py:697-1118, seven sites). One stdlib east_asian_width helper + a shared box-frame helper (border drawing is hand-rolled in four widgets).
- [x] MED (done 2026-09-14, 2.4.0): PyPI-facing lane: README is the storefront with no Install/usage/3.14-floor (PEP 758 makes the floor load-bearing); PyPI 2.3.0 metadata empty (classifiers [], urls null, license None — the GPL statement is README-only; add [project.urls], non-license classifiers, keywords; the classifier from the DECIDED box never landed); GitHub description still "a tui library"/topics null/homepage empty; zero Releases with no mechanism to make one (add a create-release job + backfill v2.3.0); pypa/gh-action-pypi-publish@release/v1 is a mutable branch pinning the job that holds id-token: write (SHA-pin all actions).
- [x] MED (done 2026-09-14, 2.4.0): Honesty fixes: dead glyph names block/block_light accepted by configure_theme but consulted by no widget (wire through _glyph() or drop — released surface, needs a release); _Cancelled export contradicts the 2.0.0 clean-API claim (deprecate, remove at 3.0); spec "styled fallback" (stub is plain); seven of 31 __init__ exports documented nowhere; CP_FRAME…CP_HINT host-widget promise has no 1-6 reservation policy; reset_terminal needs the engagement gate + a docstring; "robust cross-platform ANSI colors" overstates (no Windows VT enablement; record the investigation verdict).
- [x] LOW (done 2026-09-14, 2.4.0): Comment truth batch: run_with_capture teardown comment names lattice's retired _TUIPbar and a screen-start claim false here; ask()'s docstring points at private _Cancelled; CancelledError's doc is a dead string literal; _with_screen cites nonexistent _open_screen; _enable_mouse ignores its parameter; "T7:" planning tag on the _SCREEN comment; "letters do nothing below threshold" false in code comment and test; two test comments describe assertions they don't make (docstring-presence check; threshold-only check); menu.py/core.py lack module docstrings; the local `import curses` in _draw_curses deserves its one-liner.
- [x] LOW (done 2026-09-14, 2.4.0): Dead ANSI constants MAGENTA/DIM (core.py, zero references); .gitignore is 35 bytes with no .venv*/.pytest_cache/.ruff_cache/dist/egg-info coverage (tool self-ignore is masking it); tag_message.txt ignore line now vestigial (keep-or-drop call); local .venv_ci (50M) is a one-off with zero references (disk rule).
- [x] LOW (done 2026-09-14, 2.4.0): build_fallback digit letter_key collides silently with auto numbers; pager text-degrade body duplicated; hints default string duplicated; tqdm stub lacks __enter__/__exit__ and absorbs unknown kwargs (document the surface).
- [x] Feature candidates (done 2026-09-14 in 2.5.0; logged FINAL-REPORT L4, ranked): vir_tui.progress() session-aware factory + session-aware color()/tui_active() (one release; retires lattice's IN_TUI machinery); pager search-match highlighting + line/match indicator; scrolling viewport + i/N counter for tall menus (both consumers' main menus crossed the filter line); flash/status notice instead of full-pager notify; publish safe_addstr; type-hint the public API (all six shipped in 2.5.0). BRANDON DECISIONS: menu-loop sentinel contract (additive constants vs redesign breaking six consumer sites); letter_keys document-as-fallback-only vs dispatch (dispatch re-creates the hijack class); menu.py organization (section banners now vs six-file split).
- [x] Prose pass (done 2026-09-14, 2.4.0): 23 em-dashes across README/spec/roadmap/patchnotes/docstrings (the patchnotes 2.2.0 block is 5-in-6-lines of "Term — gloss"; configure_theme's docstring has four); "robust" at README:5; "first-class" doing promotional work; roadmap/patchnotes progress-widget sentence maintained as a near-verbatim twin (recast one); user-facing "DANGER — " string (entrenched by test).

**CONFIRMED-prior (final-audit verification):** both Wave-12 HIGHs still open and unchanged; configure_theme, reset_terminal gating, dead glyphs, _Cancelled, CP-id reservation, README storefront, description/topics, Releases-zero, license republish (decision 62), lattice floor (>=2.3.0 actual), bindery overstatement, Consumers line, patchnotes H1 restructure (deferred by lane rule). SUPERSEDED (verified done): the hygiene quartet (e1cda42, pushed), the LICENSE three-way mismatch in-tree (PyPI metadata tail remains), shadowed prompts.py still gone. Audit-side corrections: e1cda42 is pushed (close-out said unpushed); PyPI 2.3.0 carries license=None, not old-MIT. Slop-reader verdict: unusually clean prose; the "term — gloss" appositive shape is the one systemic pattern.
