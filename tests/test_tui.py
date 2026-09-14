from vir_tui import core, menu

import pytest
import vir_tui


def test_formatters():
    # Since we can't easily mock sys.stdout.isatty without side effects,
    # we just test that they return strings without crashing
    assert isinstance(core.info("test"), str)
    assert isinstance(core.warn("test"), str)
    assert isinstance(core.error("test"), str)
    assert isinstance(core.success("test"), str)


def test_build_fallback():
    sections = [("Header", ["Item 1", "Item 2"]), ("Header 2", ["Item 3", "Quit"])]
    aliases = {"i1": (0, 0), "q": None}
    letter_keys = {"Quit": ("q", None), "Item 1": ("s", "self")}

    display, mapping, max_n = menu.build_fallback(sections, aliases, letter_keys)

    # max_n should count non-letter items. Item 1 is 's', Quit is 'q'.
    # Item 2 is 1, Item 3 is 2.
    assert max_n == 2
    assert "i1" in mapping
    assert mapping["s"] == (0, 0)
    assert mapping["q"] is None
    assert mapping["1"] == (0, 1)  # Item 2
    assert mapping["2"] == (1, 0)  # Item 3


def test_session_screen_reflects_state():
    # No interactive session in tests: accessor mirrors the module state.
    assert menu.session_screen() is menu._SCREEN
    sentinel = object()
    menu._SCREEN = sentinel
    try:
        assert menu.session_screen() is sentinel
    finally:
        menu._SCREEN = None


# --- Phase 3 primitives -----------------------------------------------------


def test_text_mode_reflects_fallback_flag(monkeypatch):
    monkeypatch.setattr(menu, "_USE_CURSES", False)
    assert menu.text_mode() is True
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    assert menu.text_mode() is False


def test_out_note_public_form(monkeypatch):
    monkeypatch.chdir("/tmp")
    assert menu.out_note("x.txt") == "Report written to /tmp/x.txt"
    assert menu.out_note(None) == ""
    assert menu.out_note("") == ""


def test_prompt_float_converts_and_bounds(monkeypatch):
    answers = iter(["3.5"])
    monkeypatch.setattr(menu, "ask", lambda label, default: next(answers))
    assert menu.prompt_float("Rating", 0.0, lo=0, hi=5) == 3.5

    # Non-number and out-of-range inputs re-ask with the reason appended.
    answers = iter(["abc", "7", "4.5"])
    seen = []
    monkeypatch.setattr(
        menu, "ask", lambda label, default: (seen.append(label), next(answers))[1]
    )
    assert menu.prompt_float("Rating", 0.0, lo=0, hi=5) == 4.5
    assert "not a number" in seen[1]
    assert "between 0 and 5" in seen[2]


def test_prompt_path_loops_until_exists(monkeypatch, tmp_path):
    target = tmp_path / "real.txt"
    target.write_text("x")
    answers = iter([str(tmp_path / "missing.txt"), str(target)])
    monkeypatch.setattr(menu, "ask", lambda label, default: next(answers))
    got = menu.prompt_path("Path")
    assert got == str(target)

    # must_exist=False returns the (absolute) path immediately.
    monkeypatch.setattr(menu, "ask", lambda label, default: str(tmp_path / "nope"))
    assert menu.prompt_path("Path", must_exist=False) == str(tmp_path / "nope")


def test_confirm_wording_and_default(monkeypatch):
    calls = []

    def fake_ask_yn(label, default):
        calls.append((label, default))
        return default.lower().startswith("y")

    monkeypatch.setattr(menu, "ask_yn", fake_ask_yn)
    assert menu.confirm("Permanently delete book 7", danger=True) is False
    assert calls[-1][0].startswith("DANGER: ")
    assert calls[-1][1] == "N"
    assert menu.confirm("Keep going", default=True) is True
    assert calls[-1][0] == "Keep going"
    assert calls[-1][1] == "y"


def test_interactive_session_closes_and_degrades(monkeypatch):
    closed = []
    monkeypatch.setattr(menu, "open_screen", lambda: None)
    monkeypatch.setattr(menu, "close_screen", lambda: closed.append(True))
    with menu.interactive_session() as scr:
        assert scr is None  # degrade path: no curses screen
    assert closed == [True]

    # A real screen is yielded and closed afterwards.
    sentinel = object()
    monkeypatch.setattr(menu, "open_screen", lambda: sentinel)
    with menu.interactive_session() as scr:
        assert scr is sentinel
    assert len(closed) == 2


def test_interactive_session_reraises_keyboardinterrupt(monkeypatch):
    monkeypatch.setattr(menu, "open_screen", lambda: None)
    monkeypatch.setattr(menu, "close_screen", lambda: None)
    try:
        with menu.interactive_session():
            raise KeyboardInterrupt
    except KeyboardInterrupt:
        pass  # hosts translate this into exit code 130 themselves
    else:
        raise AssertionError("KeyboardInterrupt must propagate")


def test_match_lines_forward_backward_wrap():
    lines = ["alpha", "beta gamma", "Gamma two", "delta"]
    assert menu._match_lines(lines, "gamma") == 1  # first hit from the top
    assert menu._match_lines(lines, "gamma", start=2) == 2
    assert menu._match_lines(lines, "gamma", start=3) == 1  # wraps once
    assert menu._match_lines(lines, "gamma", start=1, reverse=True) == 1
    # Reverse search includes the start line itself: "Gamma two" matches at 2.
    assert menu._match_lines(lines, "gamma", start=2, reverse=True) == 2
    assert menu._match_lines(lines, "gamma", start=0, reverse=True) == 2  # wraps back
    assert menu._match_lines(lines, "zebra") is None
    assert menu._match_lines(lines, "") is None
    # Case-insensitive in both directions.
    assert menu._match_lines(lines, "BETA") == 1


def test_progressbox_text_fallback_is_safe(monkeypatch, capsys):
    # No session screen and a non-tty stdout (pytest capture): drawing must
    # be a no-op that never raises, and close() stays idempotent.
    monkeypatch.setattr(menu, "_SCREEN", None)
    bar = menu.ProgressBox(10, "Scanning")
    bar.update(4)
    bar.update()  # throttled updates must not blow up either
    bar.close()
    bar.close()  # idempotent
    bar.update()  # after close: ignored
    assert bar.current == 5
    captured = capsys.readouterr()
    # Non-tty stdout: nothing written (writes would corrupt pipes/redirects).
    assert captured.out == ""


def test_progressbox_counts_and_context_manager(monkeypatch):
    monkeypatch.setattr(menu, "_SCREEN", None)
    with menu.progress_box(3, "Work") as bar:
        bar.update()
        bar.update()
        bar.update()
    assert bar.current == 3
    assert bar._closed


# --- Theme overrides + type-to-filter (2.3.0) --------------------------------


@pytest.fixture(autouse=True)
def _clean_overrides():
    """Every test sees default theming; overrides never leak between tests."""
    menu._GLYPHS.clear()
    menu._PAIR_OVERRIDES.clear()
    yield
    menu._GLYPHS.clear()
    menu._PAIR_OVERRIDES.clear()


def test_configure_theme_glyph_override_applies_and_validates():
    menu.configure_theme(glyphs={"pointer": "→"})
    assert menu._glyph("pointer") == "→"
    assert menu._glyph("tl") == "╔"  # untouched default

    with pytest.raises(ValueError):
        menu.configure_theme(glyphs={"nope": "x"})


def test_configure_theme_color_pair_names_validate():
    menu.configure_theme(color_pairs={"selected": (1, 0)})
    assert menu._PAIR_OVERRIDES["selected"] == (1, 0)

    with pytest.raises(ValueError):
        menu.configure_theme(color_pairs={"frames": (1, 0)})


def test_configure_theme_value_validation_is_atomic():
    # A wrong-shaped value raises and applies nothing (the old code stored
    # the good entries before dying on the bad one, and a wrong-shaped pair
    # could escape mid-initscr with the terminal left broken).
    with pytest.raises(ValueError):
        menu.configure_theme(color_pairs={"selected": ("cyan", "nope")})
    assert menu._PAIR_OVERRIDES == {}

    with pytest.raises(ValueError):
        menu.configure_theme(color_pairs={"frame": (1, 0)}, glyphs={"pointer": 7})
    assert menu._PAIR_OVERRIDES == {}
    assert menu._GLYPHS == {}

    with pytest.raises(ValueError):
        menu.configure_theme(glyphs={"tl": "<<"})  # not a single character
    assert menu._GLYPHS == {}


def test_init_tui_colors_survives_one_bad_pair(monkeypatch):
    # Per-pair try: a pair the terminal rejects must not abort the loop and
    # leave every later pair uninitialized.
    attempted = []

    def fake_init_pair(cp, fg, bg):
        attempted.append(cp)
        if cp == menu._CP_HEADER:
            raise menu.curses.error

    monkeypatch.setattr(menu.curses, "start_color", lambda: None)
    monkeypatch.setattr(menu.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(menu.curses, "init_pair", fake_init_pair)
    menu._init_tui_colors()
    assert attempted == [
        menu._CP_FRAME,
        menu._CP_TITLE,
        menu._CP_HEADER,
        menu._CP_ITEM,
        menu._CP_SELECTED,
        menu._CP_HINT,
    ]


def test_glyph_defaults_cover_every_name_the_widgets_use():
    for name in [
        "tl",
        "tr",
        "bl",
        "br",
        "join_l",
        "join_r",
        "soft_l",
        "soft_r",
        "hline",
        "hline_light",
        "vline",
        "pointer",
        "block",
        "block_light",
    ]:
        assert menu._glyph(name), f"{name} must resolve"


def test_filter_visible_narrows_casefold():
    flat = [(0, 0, "Ambient"), (0, 1, "Jazz"), (1, 0, "ambient works")]
    assert menu._filter_visible(flat, "") == flat
    assert menu._filter_visible(flat, "AMB") == [
        (0, 0, "Ambient"),
        (1, 0, "ambient works"),
    ]
    assert menu._filter_visible(flat, "zzz") == []


def test_filter_threshold_keeps_small_menus_unchanged():
    # Below the threshold every key keeps its simple meaning: q quits,
    # arrows and j/k navigate, other letters are inert. The constant is the
    # contract; the dispatch itself is exercised by the one-shot tests below.
    assert menu._FILTER_MIN_ITEMS >= 15


# --- Terminal safety: the one-shot screen lifecycle --------------------------------


class _FakeScr:
    """Minimal stdscr double: records addstr calls, feeds scripted keys."""

    def __init__(self, keys, h=24, w=80):
        self.keys = iter(keys)
        self.h, self.w = h, w
        self.drawn = []

    def getmaxyx(self):
        return (self.h, self.w)

    def erase(self):
        pass

    def refresh(self):
        pass

    def addstr(self, y, x, text, attr=0):
        self.drawn.append((y, x, text))

    def move(self, y, x):
        pass

    def get_wch(self):
        return next(self.keys)


def test_one_shot_screen_published_and_restored(monkeypatch):
    # A one-shot widget boot publishes its screen for the wrapper's duration:
    # nested widgets, ProgressBox, and session_screen() must see it, and it
    # must be gone again once the wrapper returns.
    fake = _FakeScr(["q"])
    monkeypatch.setattr(menu.curses, "wrapper", lambda boot: boot(fake))

    seen = {}

    def body(scr):
        seen["scr"] = scr
        seen["session"] = menu.session_screen()
        return "ok"

    assert menu._with_screen(body) == "ok"
    assert seen["scr"] is fake
    assert seen["session"] is fake  # visible mid-one-shot
    assert menu._SCREEN is None  # restored after the wrapper returns


@pytest.fixture
def one_shot_screen(monkeypatch):
    """A one-shot curses.wrapper routed through a fake screen. color_pair is
    stubbed to its real (started-session) shape: without a terminal behind
    pytest it would raise curses.error and trip every degrade path."""
    scr = _FakeScr(())
    monkeypatch.setattr(menu.curses, "color_pair", lambda n: n << 8)
    monkeypatch.setattr(menu.curses, "wrapper", lambda boot: boot(scr))
    return scr


def test_pager_search_reuses_the_one_shot_screen(monkeypatch, one_shot_screen):
    # The concrete corruption path: "/" search inside a one-shot tui_page
    # (what run_with_capture produces with no session). The search prompt
    # must render into the pager's screen, not re-enter curses.wrapper.
    one_shot_screen.keys = iter(["/", "q"])
    monkeypatch.setattr(menu, "_USE_CURSES", True)

    seen = {}

    def fake_prompt(label, default):
        # Mid-one-shot the published screen must be the pager's, or the
        # prompt boots a second wrapper whose teardown kills the outer one.
        seen["screen"] = menu._SCREEN

    monkeypatch.setattr(menu, "_tui_prompt_str", fake_prompt)
    menu.tui_page("Report", "hello world")
    assert seen["screen"] is one_shot_screen


# --- Type-to-filter dispatch ---------------------------------------------------------


def test_filter_menu_dispatches_jk_to_the_filter(monkeypatch, one_shot_screen):
    # The 2026-09 audit's HIGH: on a 15+ menu, j/k are filter text (the
    # documented contract is "printable characters type a filter"), so
    # typing "jazz" must land whole in the query. "Razzberry" placed before
    # "Jazz standards" makes the old dispatch observable: the hijack moved
    # the cursor on "j" and narrowed to "azz", returning Razzberry.
    items = [f"Item {i:02d}" for i in range(14)] + ["Razzberry", "Jazz standards"]
    one_shot_screen.keys = iter(["j", "a", "z", "z", "\r"])
    got = menu._tui_select("Pick", [("Music", items)])
    assert got == (0, 15)


def test_small_menu_j_still_navigates(monkeypatch, one_shot_screen):
    # Below the filter threshold every key keeps its classic meaning.
    items = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    one_shot_screen.keys = iter(["j", "\r"])
    assert menu._tui_select("Pick", [("Music", items)]) == (0, 1)


def test_open_screen_degrades_without_curses(monkeypatch):
    # The documented contract: no curses module means open_screen returns
    # None and interactive_session degrades to the text menu. The old code
    # crashed first: its except clause evaluated the unbound curses name.
    monkeypatch.setattr(menu, "HAVE_CURSES", False)
    assert menu.open_screen() is None
    assert menu._SCREEN is None

    closed = []
    monkeypatch.setattr(menu, "close_screen", lambda: closed.append(True))
    with menu.interactive_session() as scr:
        assert scr is None
    assert closed == [True]


def test_close_screen_restores_text_mode(monkeypatch):
    # After a real session closes, no TUI is active: text_mode() must be
    # True again (it used to stay False, steering prompts at a dead screen).
    monkeypatch.setattr(menu, "_SCREEN", object())
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    menu.close_screen()
    assert menu._SCREEN is None
    assert menu.text_mode() is True

    # A defensive close with no session owns nothing to reset: one-shot
    # routing stays as it was.
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    menu.close_screen()
    assert menu.text_mode() is False


def test_esc_clearing_the_filter_widens_the_menu(monkeypatch, one_shot_screen):
    # Esc used to reset the query string but leave the narrowed view on
    # screen, so the hints promised the full menu while Enter picked from
    # the filter's leftovers.
    items = [f"Item {i:02d}" for i in range(15)] + ["Zebra finale"]
    one_shot_screen.keys = iter(["z", "e", "b", "\x1b", "\r"])
    got = menu._tui_select("Pick", [("Music", items)])
    assert got == (0, 0)


def test_short_terminal_keeps_the_menu_on_screen(monkeypatch, one_shot_screen):
    # A terminal shorter than the menu: the shift up must clamp at the top
    # edge. It used to go negative, where every draw failed silently and
    # left a blank screen with keys working blind.
    items = [f"Item {i:02d}" for i in range(16)]
    one_shot_screen.h = 4
    one_shot_screen.keys = iter(["\r"])
    got = menu._tui_select("Pick", [("Music", items)])
    assert got == (0, 0)
    assert one_shot_screen.drawn  # rows did draw
    assert min(y for y, _x, _t in one_shot_screen.drawn) >= 0


def test_pager_strips_carriage_returns(monkeypatch, one_shot_screen):
    # Captured stderr carries tqdm's \r progress frames; they used to
    # scramble the pager's addstr rendering.
    one_shot_screen.keys = iter(["q"])
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    menu.tui_page("Report", "Scan\rScan: 1\rScan: 2\nplain\r")
    drawn_text = "".join(t for _y, _x, t in one_shot_screen.drawn)
    assert "\r" not in drawn_text
    assert "Scan: 2" in drawn_text  # the last frame survived, as text


def test_progressbox_close_forces_the_final_state(monkeypatch):
    # A run ending short of total: the throttled update left the new count
    # undrawn, and close() must land it anyway ("final update always
    # draws" was false on exactly this path).
    monkeypatch.setattr(menu, "_SCREEN", None)
    bar = menu.ProgressBox(10, "Scanning")
    bar.update(4)  # inside the redraw window: throttled
    assert bar._dirty
    bar.close()
    assert bar._dirty is False  # the final state was forced out


# --- Cell-based widths (CJK) ------------------------------------------------------------


def test_cell_width_helpers():
    assert menu._cell_width("abc") == 3
    assert menu._cell_width("日本語") == 6  # wide: 2 cells each
    assert menu._cell_width("ｆｕｌｌ") == 8  # fullwidth forms: 2 cells each
    assert menu._cell_width("e\u0301") == 1  # combining mark adds nothing
    assert menu._cell_width("") == 0

    # Truncation never splits a wide character.
    assert menu._fit_cells("日本語", 5) == "日本"
    assert menu._fit_cells("abc", 10) == "abc"

    # Slicing by cells keeps pan positions aligned with what renders.
    assert menu._slice_cells("日本語", 0, 4) == "日本"
    assert menu._slice_cells("日本語", 2, 4) == "本語"
    assert menu._slice_cells("日本語", 1, 2) == ""  # a wide char straddles the edge
    assert menu._slice_cells("abcdef", 2, 3) == "cde"

    # The tail keeps the rightmost cells (the input field shows the tail).
    assert menu._tail_cells("日本語", 4) == "本語"
    assert menu._tail_cells("abcdef", 2) == "ef"

    # Padding and centering land on exact cell widths.
    assert menu._cell_width(menu._pad_cells("日", 5)) == 5
    assert menu._cell_width(menu._center_cells("日", 7)) == 7
    assert menu._center_cells("toolongtitle", 5) == "toolo"


def test_cjk_items_render_within_the_box(monkeypatch, one_shot_screen):
    # Wide labels used to overflow the 46-column box: padding and
    # truncation went by code points, not display cells.
    items = ["Ｗｉｄｅラベルその１ " * 3 for _ in range(16)]
    one_shot_screen.keys = iter(["\r"])
    menu._tui_select("日本語タイトル", [("ライブラリ", items)])
    inner_rows = [t for _y, x, t in one_shot_screen.drawn if x == 18]  # bx + 1
    assert inner_rows
    for t in inner_rows:
        assert menu._cell_width(t) <= menu._TUI_INNER


def test_pager_pans_cjk_by_cells(monkeypatch, one_shot_screen):
    # Panning used to slice by code points, so wide characters rendered
    # past the right border and the pan range under-measured.
    line = "日本語のテキスト " * 8
    one_shot_screen.keys = iter(["l", "q"])
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    menu.tui_page("レポート", f"{line}\nplain\n")
    assert one_shot_screen.drawn
    for _y, _x, t in one_shot_screen.drawn:
        assert menu._cell_width(t) <= 80  # nothing renders past the screen


# --- Honesty fixes (final audit) ---------------------------------------------------


def test_cancelled_alias_deprecated():
    # vir_tui._Cancelled still resolves (backwards compatibility) but warns;
    # the public CancelledError is the documented name.
    with pytest.warns(DeprecationWarning):
        alias = vir_tui._Cancelled
    assert alias is vir_tui.CancelledError


def test_build_fallback_rejects_digit_letter_keys():
    # A digit letter key used to collide silently with the auto numbers:
    # whichever mapping entry came last won.
    sections = [("Header", ["One", "Two", "Three"])]
    with pytest.raises(ValueError):
        menu.build_fallback(sections, letter_keys={"One": ("1", None)})
    # Non-digit letter keys keep working; a None target stays the
    # quit-style mapping, and auto-numbering skips the lettered item.
    display, mapping, max_n = menu.build_fallback(
        sections, letter_keys={"One": ("a", None)}
    )
    assert mapping["a"] is None
    assert mapping["1"] == (0, 1)


def test_progress_bar_draws_through_block_glyphs(monkeypatch):
    # The bars used to hardcode their fill characters, so the documented
    # block/block_light glyph overrides silently did nothing.
    monkeypatch.setattr(menu, "_SCREEN", None)
    menu.configure_theme(glyphs={"block": "=", "block_light": "-"})
    bar = menu.ProgressBox(4, "Work")
    bar.update(2)
    line = bar._text_line()
    assert "=" in line and "-" in line
    assert "█" not in line and "░" not in line


def test_reset_terminal_gates_on_curses_engagement(monkeypatch):
    # A terminal curses never touched gets no `stty sane`: it used to run
    # unconditionally, even in pure-text sessions.

    class _TtyStdin:
        def isatty(self):
            return True

    calls = []
    monkeypatch.setattr(menu.sys, "stdin", _TtyStdin())
    monkeypatch.setattr(menu, "_SCREEN", None)
    monkeypatch.setattr(menu.subprocess, "run", lambda cmd, **k: calls.append(cmd))

    monkeypatch.setattr(menu, "_CURSES_TOUCHED", False)
    menu.reset_terminal()
    assert calls == []

    monkeypatch.setattr(menu, "_CURSES_TOUCHED", True)
    menu.reset_terminal()
    assert calls == [["stty", "sane"]]


# --- Session awareness, viewport, flash (2.5.0) ------------------------------------


def test_tui_active_reflects_sessions_and_one_shots(monkeypatch):
    monkeypatch.setattr(menu, "_USE_CURSES", False)
    monkeypatch.setattr(menu, "_SCREEN", None)
    assert menu.tui_active() is False

    monkeypatch.setattr(menu, "_USE_CURSES", True)
    assert menu.tui_active() is True

    # Mid-one-shot: no session flag, but a screen is published.
    monkeypatch.setattr(menu, "_USE_CURSES", False)
    monkeypatch.setattr(menu, "_SCREEN", object())
    assert menu.tui_active() is True


def test_progress_factory_is_session_aware(monkeypatch):
    monkeypatch.setattr(menu, "_USE_CURSES", False)
    assert isinstance(menu.progress(5, "Work"), core.tqdm)
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    assert isinstance(menu.progress(5, "Work"), menu.ProgressBox)


def test_color_gates_on_an_active_tui(monkeypatch):
    # Hosts printing through color()/info() during a curses session used to
    # inject raw ANSI under the screen; the gate drops styling instead.

    class _TtyOut:
        def isatty(self):
            return True

    monkeypatch.setattr(core.sys, "stdout", _TtyOut())
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(menu, "_USE_CURSES", False)
    monkeypatch.setattr(menu, "_SCREEN", None)
    assert core.color("x", core.RED).startswith("\033[")

    monkeypatch.setattr(menu, "_SCREEN", object())  # a one-shot is live
    assert core.color("x", core.RED) == "x"


def test_sentinel_constants_keep_their_contract_values():
    assert menu.FALLBACK == "fallback"
    assert menu.INVALID == "invalid"


def test_fallback_input_returns_the_invalid_sentinel(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "zzz")
    assert menu.fallback_input("Sel: ", {"1": (0, 0)}) == menu.INVALID


def test_public_pause_routes_by_mode(monkeypatch):
    hit = []
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    monkeypatch.setattr(menu, "_tui_pause", lambda: hit.append("tui"))
    menu.pause()
    assert hit == ["tui"]

    monkeypatch.setattr(menu, "_USE_CURSES", False)
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    menu.pause()  # text path: must not raise


def test_flash_draws_one_line_and_dismisses(monkeypatch, one_shot_screen):
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    one_shot_screen.keys = iter([" "])
    menu.flash("Not found: /x")
    drawn = "".join(t for _y, _x, t in one_shot_screen.drawn)
    assert "Not found: /x" in drawn


def test_prompt_path_flashes_misses(monkeypatch, tmp_path):
    target = tmp_path / "real.txt"
    target.write_text("x")
    answers = iter([str(tmp_path / "nope"), str(target)])
    monkeypatch.setattr(menu, "ask", lambda label, default: next(answers))
    flashed = []
    monkeypatch.setattr(menu, "flash", lambda msg: flashed.append(msg))
    got = menu.prompt_path("Path")
    assert got == str(target)
    assert flashed and "nope" in flashed[0]


def test_match_span_finds_the_highlight_range():
    assert menu._match_span("the beta release", "beta") == (4, 8)
    assert menu._match_span("any", "") is None
    assert menu._match_span("nope", "beta") is None
    # Casefolded matching, like the search itself.
    assert menu._match_span("The BETA", "beta") == (4, 8)


def test_pager_highlights_matches_and_shows_the_indicator(monkeypatch, one_shot_screen):
    one_shot_screen.keys = iter(["/", "q"])
    monkeypatch.setattr(menu, "_USE_CURSES", True)
    monkeypatch.setattr(menu, "_tui_prompt_str", lambda label, default: "beta")
    menu.tui_page("Report", "the beta release\nnothing here\nbeta two")
    texts = [t for _y, _x, t in one_shot_screen.drawn]
    # The matched span is drawn as its own run between the plain runs.
    assert "the " in texts and "beta" in texts and " release" in texts
    # The hints line carries the position and the match count.
    hints = [t for t in texts if "match" in t]
    assert hints and "3" in hints[0] and "2 matches" in hints[0]


def test_tall_menu_scrolls_and_counts(monkeypatch, one_shot_screen):
    # 30 items on a 24-row screen: the box is a window that follows the
    # selection, with an i/N counter in the hints.
    items = [f"Item {i:02d}" for i in range(30)]
    keys = [menu.curses.KEY_DOWN] * 20 + ["\r"]
    one_shot_screen.keys = iter(keys)
    got = menu._tui_select("Pick", [("Music", items)])
    assert got == (0, 20)
    texts = [t for _y, _x, t in one_shot_screen.drawn]
    assert any("item 21/30" in t for t in texts)


def test_small_menu_does_not_scroll_or_count(monkeypatch, one_shot_screen):
    items = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    one_shot_screen.keys = iter(["\r"])
    got = menu._tui_select("Pick", [("Music", items)])
    assert got == (0, 0)
    texts = [t for _y, _x, t in one_shot_screen.drawn]
    assert not any("item 1/5" in t for t in texts)


def test_filter_menu_arrows_navigate_and_q_still_quits(monkeypatch, one_shot_screen):
    # The arrows carry navigation on every menu, and q/Q stay reserved for
    # quit while no query is armed (their own guard predates the j/k fix).
    items = [f"Item {i:02d}" for i in range(16)]
    one_shot_screen.keys = iter([menu.curses.KEY_DOWN, "\r"])
    assert menu._tui_select("Pick", [("Music", items)]) == (0, 1)

    one_shot_screen.keys = iter(["q"])
    assert menu._tui_select("Pick", [("Music", items)]) is None
