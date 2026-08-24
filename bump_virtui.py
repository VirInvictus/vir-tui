import re
from datetime import datetime

date_str = datetime.now().strftime("%Y-%m-%d")

# pyproject.toml
with open("pyproject.toml", "r") as f: content = f.read()
content = re.sub(r'version = "1\.0\.0"', 'version = "2.0.0"', content)
with open("pyproject.toml", "w") as f: f.write(content)

# VERSION file
with open("VERSION", "w") as f: f.write("2.0.0")

# patchnotes.md
patchnotes = f"""# 2.0.0 ({date_str})
- **Breaking**: Gutted hardcoded Lattice/CalibreQuarry domains (`_MAIN_SECTIONS`, `_LIB_SECTIONS`). Consumers must now provide their own tuples to `tui_select`.
- **Breaking**: Exported public API clean without underscores (e.g. `tui_select`, `ask`, `notify`, `reset_terminal`).
- **Feature**: `tui_select` now automatically builds text-mode fallback menus dynamically using `aliases` and `letter_keys` kwargs.
- **Fix**: Reverted `getch()` to `get_wch()` to fix a multibyte character search crash.
- **Fix**: Enforced `visible_w = max(1, content_w - 4)` in `_tui_page` to prevent slicing crashes on narrow terminals.
- **Maintenance**: Added `tests/` directory with `pytest` suite for core formatters.

"""
with open("patchnotes.md", "r") as f: current_pn = f.read()
with open("patchnotes.md", "w") as f: f.write(patchnotes + current_pn)

# spec.md
with open("spec.md", "r") as f: spec = f.read()
spec = spec.replace("The library provides a hardcoded fallback mapping specifically for Lattice.", "The library accepts `aliases` and `letter_keys` to dynamically generate text-fallback menus for any domain.")
with open("spec.md", "w") as f: f.write(spec)

# README.md
with open("README.md", "r") as f: readme = f.read()
readme = readme.replace("1.0.0", "2.0.0")
if "Lattice-specific" in readme:
    readme = re.sub(r"Lattice-specific.*", "fully generalized menus with dynamic text fallbacks.", readme)
with open("README.md", "w") as f: f.write(readme)

# CLAUDE.md
with open("CLAUDE.md", "r") as f: claude = f.read()
claude = claude.replace("v1.0.0", "v2.0.0")
if "hardcoded" not in claude:
    claude += "\n- This is a generalized library. Do NOT hardcode domain menus. Pass them via `tui_select`.\n"
with open("CLAUDE.md", "w") as f: f.write(claude)

