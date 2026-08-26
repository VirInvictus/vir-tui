from vir_tui import core, menu


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
