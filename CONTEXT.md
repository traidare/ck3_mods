# CK3/AGOT Work Context

Use this document for every CK3 or AGOT request in this repository. Collect only
the context required by the task, but do not write Paradox Script from memory.

## Start every task

1. Check `git status --short` and identify the requested local mod or parent.
2. For playset work, run `ck3mm playset summary [playset]`. The live Launcher
   database is authoritative.
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

### Effective game data

`ck3mm cultures`, `ck3mm traditions`, and `ck3mm faiths` answer what the playset
actually defines, resolved through the same load order and `replace_path`
shadowing `conflicts` uses. Prefer them over hand-walking layer directories.

```sh
ck3mm cultures list --heritage heritage_andal --with-traditions
ck3mm cultures show andal
ck3mm traditions list --culture andal
ck3mm traditions show tradition_chivalry
ck3mm faiths list --religion the_seven_religion --doctrine tenet_knighthood
ck3mm faiths show fots_seven
ck3mm faiths holy-sites fots_seven
```

## Evidence rules

- Check the relevant `.info` file first; then local script docs when available;
  then AGOT source, vanilla source, and the matching guides.
- For AGOT changes, check whether a matching `agot-ext-*.md` exists and read it
  with the generic pattern guide.
- Treat a same-path conflict as evidence to investigate, never as a default
  last-writer decision.

## Live playsets and conflicts

`ck3mm playset` reads the Launcher SQLite database. It selects a playset by
command argument, `CK3_PLAYSET_NAME`, then the active Launcher playset. Use
`summary` for current load-order questions; exported JSON is only a snapshot.
`--format text|json` and `--apply` are global flags, so every report can be
requested as JSON.

```sh
ck3mm playset summary
ck3mm playset summary AGOT
ck3mm playset export AGOT --output /tmp/agot-playset.json
```

Start conflict inspection broad, then narrow by Workshop ID or local launcher
registry ID:

```sh
ck3mm conflicts AGOT --summary-only
ck3mm conflicts AGOT --mods-only
ck3mm conflicts AGOT --involving 3206891770
ck3mm conflicts AGOT --involving mod/cafg_agot_compatch.mod
```

`--involving` also accepts an installed mod the playset does not enable. It is
analyzed as if added last in load order, so a candidate addition can be checked
before it joins the playset.

Use `--include-prefix`, `--exclude-prefix`, and `--format json` to reduce a
report. Schema-v2 JSON is deterministic and excludes host filesystem paths; it
records same-path and `replace_path` conflicts, content status, and the
effective winner. A reported conflict is an investigation starting point, not an
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
the re-audit trigger in the affected module's `workspace/<slug>/README.md`.

Every module carries two documents, and each fact belongs to exactly one:

`workspace/<slug>/README.md` documents that module's CURRENT state: what it
owns, what it patches, why that compatch layer was chosen, how to regenerate it,
what its source assertions detect, and when to re-audit. It never narrates a
parent's release history or what an upstream update changed. Name parent
versions only where the module's own behavior is pinned to them.

`mods/<slug>/README.md` is the compact, player-facing description — exactly what
would be published as the mod's Workshop description. It states what the mod
CURRENTLY does, which parent mods it requires, the required load order by
display name, the user-visible behavior, and any incompatibility a player must
act on. It carries no `ck3mm` commands, no repository paths, no bare Workshop
IDs used as identifiers, no pinned parent versions, and no re-audit
instructions. Prefer at most 40 lines.

For rebases, identify the common base, compare each parent's delta, and inspect
every merge conflict. Whole-file speed or automation overrides can accidentally
restore vanilla logic AGOT disabled; validate unrelated behavior as well as the
intended change.

For a runtime repair, retain the exact log signature, source location, effective
last writer, and reason the narrower repair is safe in
`workspace/<slug>/README.md`. Quote the signature itself; never cite a specific
log file, dated run, or playtest session.

For map-data merges:

- Merge `definition.csv` by province ID and locator files by numeric ID.
- Merge generated transforms spatially and recompute declared counts.
- Composite heightmaps and masks from exact base-to-parent pixel deltas.
- Validate unique IDs/colors, dimensions, bit depth, transform counts, and
  generated-image invariants.

Use [the heightmap repack workflow](docs/agot-heightmap-repack.md) for the NOW,
LoV, and Essos Expanded heightmap workflow.

## Repository layout

`mods/<slug>/` holds only installable CK3 payload. Everything used to build,
validate, or audit that mod lives in `workspace/<slug>/` and never ships:

| path                                  | contents                                    |
| ------------------------------------- | ------------------------------------------- |
| `mods/<slug>/descriptor.mod`          | game-facing metadata only                   |
| `mods/<slug>/README.md`               | Workshop-facing description;                |
| `mods/<slug>/common/`, `map_data/`, … | payload CK3 loads                           |
| `workspace/<slug>/README.md`          | module state, ownership, re-audit trigger   |
| `workspace/<slug>/mod.toml`           | generator manifest, declared sources        |
| `workspace/<slug>/implementation.py`  | the mod's generator                         |
| `workspace/<slug>/assets/`            | generator inputs and source manifests       |
| `workspace/<slug>/artifacts/`         | generated audits and unpacked sources       |
| `workspace/<slug>/ck3-tiger.conf`     | dependency load order for static validation |

## Generated outputs and validation

When a module has a `workspace/<slug>/mod.toml` generator, edit its generator or
assets and regenerate its declared owned outputs. The staged generator's
assertions and granular source-manifest assets are upstream-change detectors,
not optional noise.

A manifest declares two output roots. `owned_outputs` are payload paths promoted
into `mods/<slug>/`; `owned_artifacts` are paths promoted into
`workspace/<slug>/artifacts/`. Generators stage artifacts under the reserved
`artifacts/` prefix, so audits never reach the Launcher.

Validate from narrow to broad:

```sh
ck3mm mod generate <mod>  # when the manifest declares a generator
ck3mm mod validate <mod>
ck3mm conflicts AGOT --involving <id>
```

Every command previews by default and writes only with `--apply`. `mod generate`
without `--apply` reports what differs, and exits 1 when an owned output is
stale. `--apply` promotes it. The same holds for `mod install`,
`playset import`, `playset preserve`, and `refs sync`. Let the user run any
apply that writes to Launcher state or another external root.

Keep upstream-change checks granular to the files and definitions a generator
actually consumes. Review that source evidence and update it deliberately after
an intentional parent change.
