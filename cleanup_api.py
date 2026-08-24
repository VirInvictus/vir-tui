import os

menu_path = '/home/bdkl/.gitrepos/vir-tui/src/vir_tui/menu.py'
with open(menu_path, 'r') as f:
    content = f.read()

replacements = {
    'class _Cancelled(Exception):': 'class CancelledError(Exception):\n    pass\n\n_Cancelled = CancelledError',
    'def _open_screen': 'def open_screen',
    'def _close_screen': 'def close_screen',
    'def _reset_terminal': 'def reset_terminal',
    'def _tui_page': 'def tui_page',
    'def _run_with_capture': 'def run_with_capture',
    'def _ask(': 'def ask(',
    'def _ask_yn': 'def ask_yn',
    'def _prompt_int': 'def prompt_int',
    'def _prompt_out': 'def prompt_out',
    'def _notify': 'def notify',
    'def _box_menu': 'def box_menu',
    'def _fallback_input': 'def fallback_input',
    '_ask(': 'ask(',
    '_ask_yn(': 'ask_yn(',
    '_prompt_int(': 'prompt_int(',
    '_prompt_out(': 'prompt_out(',
    '_open_screen()': 'open_screen()',
    '_close_screen()': 'close_screen()',
    '_reset_terminal()': 'reset_terminal()',
    '_tui_page(': 'tui_page(',
    '_run_with_capture(': 'run_with_capture(',
    '_notify(': 'notify(',
    '_box_menu(': 'box_menu(',
    '_fallback_input(': 'fallback_input(',
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(menu_path, 'w') as f:
    f.write(content)

init_path = '/home/bdkl/.gitrepos/vir-tui/src/vir_tui/__init__.py'
init_content = """from .core import info, success, warn, error, dry_run, print_header, print_summary, color, tqdm
from .menu import (
    tui_select,
    build_fallback,
    reset_terminal,
    open_screen,
    close_screen,
    ask,
    ask_yn,
    prompt_int,
    prompt_out,
    run_with_capture,
    CancelledError,
    notify,
    tui_page,
    box_menu,
    fallback_input,
    _Cancelled,  # for backwards compatibility
    capture_output
)
"""
with open(init_path, 'w') as f:
    f.write(init_content)

prompts_path = '/home/bdkl/.gitrepos/vir-tui/src/vir_tui/prompts.py'
if os.path.exists(prompts_path):
    os.remove(prompts_path)

