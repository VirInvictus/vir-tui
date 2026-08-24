import os
import re

init_path = 'src/vir_tui/__init__.py'
with open(init_path, 'r') as f:
    content = f.read()

# Collect all exported names
names = re.findall(r'(\w+)[,]?', content.split('from .menu import (')[1].split(')')[0])
core_names = ["info", "success", "warn", "error", "dry_run", "print_header", "print_summary", "color", "tqdm"]

all_names = core_names + names
all_str = "\\n    ".join(f'"{n}",' for n in all_names)

content += f"\\n__all__ = [\\n    {all_str}\\n]\\n"
with open(init_path, 'w') as f:
    f.write(content)
