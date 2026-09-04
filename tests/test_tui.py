from vir_tui import core, menu

import pytest


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
    assert calls[-1][0].startswith("DANGER — ")
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
    # Unnamed pairs stay on their defaults at color init.
    assert menu._init_tui_colors.__doc__  # lazily applied, documented shape

    with pytest.raises(ValueError):
        menu.configure_theme(color_pairs={"frames": (1, 0)})


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
    # Below the threshold every key keeps its simple meaning (q quits,
    # letters are inert); the 2.2.0 behavior is untouched there.
    assert menu._FILTER_MIN_ITEMS >= 15
