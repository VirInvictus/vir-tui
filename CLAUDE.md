# vir-tui

- **Domain**: Terminal UI rendering for VirInvictus CLI apps.
- **Dependencies**: `stdlib` only. No dependencies are allowed in `pyproject.toml`.
- **Formatting**: ANSI codes.

Read `spec.md` before making changes.

### Consumers
Any breaking changes to `vir-tui` MUST be cascaded to the following applications that depend on it:
1. `CalibreQuarry` (tracks `@main`)
2. `Lattice` (tracks `@main`)
3. `Bindery` (pins an exact commit by policy — bump the pin deliberately)

- This is a generalized library. Do NOT hardcode domain menus. Pass them via `tui_select`.
