import warnings

from .core import (
    info,
    success,
    warn,
    error,
    dry_run,
    print_header,
    print_summary,
    color,
    tqdm,
)
from .menu import (
    CP_FRAME,
    CP_HEADER,
    CP_HINT,
    CP_ITEM,
    CP_SELECTED,
    CP_TITLE,
    FALLBACK,
    INVALID,
    ProgressBox,
    configure_theme,
    confirm,
    interactive_session,
    out_note,
    pause,
    progress,
    progress_box,
    prompt_float,
    prompt_path,
    safe_addstr,
    tui_select,
    tui_active,
    build_fallback,
    reset_terminal,
    open_screen,
    close_screen,
    session_screen,
    text_mode,
    ask,
    ask_yn,
    prompt_int,
    prompt_out,
    run_with_capture,
    CancelledError,
    notify,
    flash,
    tui_page,
    box_menu,
    fallback_input,
    capture_output,
)


def __getattr__(name):
    # PEP 562 module hook: fires only for names the imports above do not
    # define. _Cancelled is the retired private alias of CancelledError; the
    # 2.0.0 clean-public-API claim is restored with a deprecation cycle
    # instead of a hard break, and the alias is removed in 3.0.
    if name == "_Cancelled":
        warnings.warn(
            "vir_tui._Cancelled is the deprecated private alias of "
            "CancelledError; it will be removed in 3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return CancelledError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
