import re

menu_path = '/home/bdkl/.gitrepos/vir-tui/src/vir_tui/menu.py'
with open(menu_path, 'r') as f:
    content = f.read()

# Fix 1: _tui_select keys
content = content.replace('key in (curses.KEY_UP, ord("k"))', 'key in (curses.KEY_UP, "k")')
content = content.replace('key in (curses.KEY_DOWN, ord("j"))', 'key in (curses.KEY_DOWN, "j")')
content = content.replace('key in (curses.KEY_ENTER, 10, 13)', 'key in (curses.KEY_ENTER, 10, 13, "\\n", "\\r")')
content = content.replace('key in (ord("q"), ord("Q"), 27)', 'key in ("q", "Q", 27, "\\x1b")')

# Fix 2: _tui_prompt_str keys
content = content.replace('key == 27:', 'key in (27, "\\x1b"):')
content = content.replace('key in (curses.KEY_BACKSPACE, 127, 8)', 'key in (curses.KEY_BACKSPACE, 127, 8, "\\x7f", "\\x08")')
content = content.replace('key == 21:', 'key in (21, "\\x15"):')
content = content.replace('buf.append(chr(key))', 'buf.append(key)')

# Fix 3: _tui_pause keys
content = content.replace('key in (curses.KEY_ENTER, 10, 13, ord("q"), ord("Q"), 27)', 'key in (curses.KEY_ENTER, 10, 13, "\\n", "\\r", "q", "Q", 27, "\\x1b")')

# Fix 4: _tui_page keys
content = content.replace('key in (curses.KEY_LEFT, ord("h"))', 'key in (curses.KEY_LEFT, "h")')
content = content.replace('key in (curses.KEY_RIGHT, ord("l"))', 'key in (curses.KEY_RIGHT, "l")')
content = content.replace('key in (curses.KEY_HOME, ord("g"))', 'key in (curses.KEY_HOME, "g")')
content = content.replace('key in (curses.KEY_END, ord("G"))', 'key in (curses.KEY_END, "G")')
content = content.replace('key in (ord("q"), ord("Q"), 27, curses.KEY_ENTER, 10, 13)', 'key in ("q", "Q", 27, "\\x1b", curses.KEY_ENTER, 10, 13, "\\n", "\\r")')


with open(menu_path, 'w') as f:
    f.write(content)
