# CK3/AGOT Work Context

Use this document for every CK3 or AGOT request in this repository. Collect only
the context required by the task, but do not write Paradox Script from memory.

## Start every task

1. Check `git status --short` and identify the requested local mod or parent.
2. For playset work, run `scripts/ck3-playsets.py summary [playset]`. The live
   Launcher database is authoritative; exported JSON is a snapshot only.
3. Classify the task and read the relevant section below before changing files.
4. State the parent mod(s), their effective load order, and the intended owner
   of each changed file.

## Reference sources

Use sources in this order when authoring or diagnosing Paradox Script:

1. `references/generated/info/` — synchronized CK3 `.info` syntax files.
2. `references/generated/script_docs/` — generated effect, trigger, scope,
   target, and modifier logs when present.
3. `$CK3_WORKSHOP_DIR/2962333032/` — current AGOT implementation.
4. `$CK3_GAME_DIR` — current vanilla implementation.
5. `references/agot/` — AGOT patterns and extensions.
6. `references/patterns/`, `references/structure/`, and `references/compat/` —
   generic CK3 patterns and workflow guides.

Generate the local cache with `scripts/sync-ck3-references.bash` and check it
with `scripts/sync-ck3-references.bash --check`; absent script-doc logs are not
an error, but they must not be assumed to exist.

## Evidence rules

- Check the relevant `.info` file first; then local script docs when available;
  then AGOT source, vanilla source, and the matching guides.
- For AGOT changes, check whether a matching `agot-ext-*.md` exists and read it
  with the generic pattern guide.
- Treat a same-path conflict as evidence to investigate, never as a default
  last-writer decision.

## Live playsets and conflicts

`scripts/ck3-playsets.py` reads the Launcher SQLite database. It selects a
playset by command argument, `CK3_PLAYSET_NAME`, then the active Launcher
playset. Use `summary` for current load-order questions; exported JSON is only a
snapshot.

```sh
scripts/ck3-playsets.py summary
scripts/ck3-playsets.py summary AGOT
scripts/ck3-playsets.py export > /tmp/agot-playset.json
```

Start conflict inspection broad, then narrow by Workshop ID or local launcher
registry ID:

```sh
scripts/ck3-playsets.py export > /tmp/agot-playset.json
ck3_mod_conflict_checker -playset /tmp/agot-playset.json -summary-only
ck3_mod_conflict_checker -playset /tmp/agot-playset.json -involving 3206891770
ck3_mod_conflict_checker -playset /tmp/agot-playset.json \
  -involving mod/cafg_agot_compatch.mod
```

Use `-include-prefix`, `-exclude-prefix`, and `-format json` to reduce a report.
A reported same-path conflict is an investigation starting point, not an
instruction to copy a file into the final compatch.

## Compatch workflows

Choose the smallest appropriate layer:

1. **Upstream rebase:** a parent whole-file override is stale against a current
   parent. Preserve its intended delta while restoring current parent behavior.
2. **Map-data merge:** multiple parents make real, spatially distinct map edits.
   Merge by semantic identifiers and source-image deltas.
3. **Final integration:** only genuine cross-mod overlaps that require a single
   intentional last writer.
4. **Narrow runtime repair:** a parent is otherwise usable but has evidenced
   CK3/AGOT-invalid syntax, scope, or database references.

Keep the first three categories separate when practical. Record ownership and
the re-audit trigger in the affected module README.

For rebases, identify the common base, compare each parent's delta, and inspect
every merge conflict. Whole-file speed or automation overrides can accidentally
restore vanilla logic AGOT disabled; validate unrelated behavior as well as the
intended change.

For a runtime repair, retain the exact log signature, source location, effective
last writer, and reason the narrower repair is safe in the module README.

For map-data merges:

- Merge `definition.csv` by province ID and locator files by numeric ID.
- Merge generated transforms spatially and recompute declared counts.
- Composite heightmaps and masks from exact base-to-parent pixel deltas.
- Validate unique IDs/colors, dimensions, bit depth, transform counts, and
  generated-image invariants.

Use [the heightmap repack workflow](docs/agot-heightmap-repack.md) for the NOW,
LoV, and Essos Expanded heightmap workflow.

## Generated outputs and validation

When a module has a generator, edit the generator and regenerate its output. The
generator's assertions are an upstream-change detector, not optional noise.

Validate from narrow to broad:

```sh
scripts/generate-<module>.py --check  # when supported
just check-tiger <mod>
scripts/ck3-playsets.py export > /tmp/agot-playset.json
ck3_mod_conflict_checker -playset /tmp/agot-playset.json -involving <id>
```

Finish with the relevant runtime test when the change can execute in CK3.
