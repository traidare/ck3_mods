"""Shared generator logic for the three AGOT playset compatch modules.

The playset ships one always-on module and two that are enabled with the
optional families, and each one's `workspace/<slug>/implementation.py` is only a
thin entrypoint.  Every rule they apply lives here so a fix has exactly one
owner regardless of which modules a profile enables:

`runtime_fixes`
    Narrow repairs to evidenced CK3/AGOT-invalid syntax, scope, or database
    references.  Each repair takes the parent stack it reads, so the same
    function serves whichever module owns that parent.
`compatch`
    Map-data merges and the Further East world/lore pipeline.
`final_integration`
    Cross-mod overlaps needing a single intentional last writer, split into a
    `generate_core` entrypoint and a `generate_lov` entrypoint.
`lov_map`
    The Legacy of Valyria map bridge.

Which module a rule belongs to is a property of the entrypoint that calls it and
of the sources that module's `mod.toml` declares, never of where the rule is
defined.
"""
