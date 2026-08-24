# vir-tui Specification

1. **Domain**: Provides terminal UI rendering and input capturing for Python CLI applications.
2. **Dependencies**: `stdlib` only. If `tqdm` is available in the consumer's environment, `vir_tui` will export it; otherwise, it exports a minimal stub.
3. **Architecture**:
   - `core.py`: ANSI state logic, color formats, `tqdm` handling.
   - `prompts.py`: Interactive input functions that wrap `input()` with styled prefixes.
   - `menu.py`: The `GridMenu` class that puts the terminal in raw mode via `tty.setraw` or `termios` and captures arrow keys to navigate a 2D layout.

4. **Guarantees**:
   - Must fail gracefully and degrade if `sys.stdout` is not a TTY.
