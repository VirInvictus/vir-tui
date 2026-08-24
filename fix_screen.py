import re

menu_path = '/home/bdkl/.gitrepos/vir-tui/src/vir_tui/menu.py'
with open(menu_path, 'r') as f:
    content = f.read()

# Make open_screen set _SCREEN
old_open_screen = """def open_screen():
    \"\"\"Start the session screen (initscr + the modes curses.wrapper would
    set). Returns the screen, or None when curses can't start on this
    terminal — the caller degrades the whole session to the text menu.\"\"\"
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        _init_tui_colors()
        return stdscr"""

new_open_screen = """def open_screen():
    \"\"\"Start the session screen (initscr + the modes curses.wrapper would
    set). Returns the screen, or None when curses can't start on this
    terminal — the caller degrades the whole session to the text menu.\"\"\"
    global _SCREEN, _USE_CURSES
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        _init_tui_colors()
        _SCREEN = stdscr
        _USE_CURSES = True
        return stdscr"""

content = content.replace(old_open_screen, new_open_screen)
with open(menu_path, 'w') as f:
    f.write(content)
