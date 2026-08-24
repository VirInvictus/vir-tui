import os
import re

menu_path = '/home/bdkl/.gitrepos/vir-tui/src/vir_tui/menu.py'
with open(menu_path, 'r') as f:
    content = f.read()

# 1. Unicode Fix
content = content.replace("key = stdscr.getch()", "key = stdscr.get_wch()")
# get_wch returns int for special keys and str for chars.
# we need to handle that.
content = content.replace("elif 32 <= key <= 126:", "elif isinstance(key, str) and key.isprintable():")

# 2. Narrow Pager Crash Fix
content = content.replace("visible_w = content_w - 4", "visible_w = max(1, content_w - 4)")

# 3. Remove hardcoded sections
start_idx = content.find("_MAIN_SECTIONS = [")
end_idx = content.find("def _tui_page", start_idx)

if start_idx != -1 and end_idx != -1:
    # Insert new build_fallback and tui_select wrapper
    new_code = """def build_fallback(sections, aliases=None, letter_keys=None):
    aliases = aliases or {}
    letter_keys = letter_keys or {}
    mapping = dict(aliases)
    display = []
    n = 0
    for si, (hdr, items) in enumerate(sections):
        rows = []
        for ii, label in enumerate(items):
            clean = " ".join(label.split())
            letter = letter_keys.get(clean)
            if letter is not None:
                key, target = letter
                rows.append(f"{key}) {clean}")
                mapping[key] = (si, ii) if target == "self" else target
            else:
                n += 1
                rows.append(f"{n}) {clean}")
                mapping[str(n)] = (si, ii)
        display.append((hdr, rows))
    return display, mapping, n

def tui_select(title, sections, hints="\u2191\u2193 Navigate  \u23ce Select  q Quit", aliases=None, letter_keys=None):
    if _USE_CURSES:
        res = _tui_select(title, sections, hints=hints)
        if res != "fallback":
            return res
    # Fallback
    display, mapping, max_n = build_fallback(sections, aliases, letter_keys)
    _box_menu(title, display)
    return _fallback_input(f"  Select [1-{max_n}/q]: ", mapping)

"""
    content = content[:start_idx] + new_code + content[end_idx:]

with open(menu_path, 'w') as f:
    f.write(content)
