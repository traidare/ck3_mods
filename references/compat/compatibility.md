# CK3 Mod Compatibility Reference

## How CK3 Mod Loading Works (for compatibility)

- Mods load after vanilla; later mods override earlier ones
- Files with the same name completely replace each other (no merging)
- Localization keys merge by key (last loaded wins)
- `common/` files merge by top-level block key

## Types of Conflicts

### 1. File-level override

Two mods modify the same vanilla file. The last-loaded mod wins entirely. The
other mod's changes are invisible.

```
# Mod A ships: common/traits/00_personality_traits.txt
# Mod B ships: common/traits/00_personality_traits.txt
# Result: only Mod B's version is used — Mod A's changes are lost
```

### 2. Key-level collision

Two mods add/modify the same scripting key (trait, decision, event namespace).
Last loaded wins for that key.

```
# Mod A: common/traits/mod_a_traits.txt  defines "brave_warrior"
# Mod B: common/traits/mod_b_traits.txt  defines "brave_warrior"
# Result: last loaded mod's "brave_warrior" wins silently
```

### 3. Localization stomping

Same loc key in both mods. Last loaded wins.

```
# Mod A: localization/english/mod_a_l_english.yml
#   trait_brave_warrior: "Brave Warrior"
# Mod B: localization/english/mod_b_l_english.yml
#   trait_brave_warrior: "Bold Fighter"
# Result: depends on load order
```

### 4. replace_path nuclear option

One mod uses `replace_path` in its `.mod` descriptor to wipe a vanilla folder.
All other mods' additions to that folder are also deleted.

```
# In descriptor.mod:
replace_path = "common/traits"
# Result: ALL files in common/traits/ from vanilla AND other mods are removed
```

### 5. Scripted effect/trigger shadowing

Two mods define a `scripted_effect` or `scripted_trigger` with the same name.
Silent override — no warning in the error log.

```
# Mod A: common/scripted_effects/mod_a_effects.txt  defines "apply_battle_bonus"
# Mod B: common/scripted_effects/mod_b_effects.txt  defines "apply_battle_bonus"
# Result: last loaded wins, no error
```

### 6. On_action stacking

Multiple mods adding to the same `on_action`. This actually WORKS (merges), but
can cause unexpected interactions.

```
# Mod A: common/on_action/mod_a_on_actions.txt
on_birth_child = { events = { mod_a_events.0001 } }
# Mod B: common/on_action/mod_b_on_actions.txt
on_birth_child = { events = { mod_b_events.0001 } }
# Result: BOTH events fire — they merge. But order/interactions may surprise you.
```

## Total Conversion Mods

- Total conversions (like AGOT, EK2, etc.) use `replace_path` extensively
- They are generally incompatible with content mods designed for vanilla
- Sub-mods designed FOR the total conversion work because they target the TC's
  files, not vanilla
- If making a mod compatible with a TC: target the TC's file structure, not
  vanilla's

## Making Your Mod Compatible

- **Use unique filenames** — never name your file the same as a vanilla file
  unless you intend to override it
- **Use unique key names** — prefix with your mod name (e.g.,
  `mymod_trait_brave` not `custom_brave`)
- **Use unique namespaces** — for events, use a distinctive namespace (e.g.,
  `mymod_events` not `events`)
- **Avoid replace_path** unless you're a total conversion
- **Use unique loc keys** — prefix with mod name
- **Document overrides** — if you MUST override vanilla, document which files
  and why

## Conflict Detection Patterns

- Compare file trees between mods
- Grep for same top-level keys in `common/` files
- Compare loc keys across localization files
- Check `descriptor.mod` for `replace_path` directives
- Check for same event namespaces

## Resolution Strategies

1. **Load order** — put the mod whose changes you prefer later
2. **Compatibility patch** — a third mod that merges the changes from both
3. **Modular design** — split mod into independent modules (separate file per
   feature)
4. **Unique naming** — prevents most conflicts entirely

## Using the repository conflict checker

```bash
scripts/ck3-playsets.py export > /tmp/agot-playset.json
ck3_mod_conflict_checker -playset /tmp/agot-playset.json -summary-only
ck3_mod_conflict_checker -playset /tmp/agot-playset.json -involving <workshop-id>
```

Use the live Launcher playset as the comparison scope, then narrow the report by
Workshop ID or local launcher registry ID. It shows file conflicts and
`replace_path` interactions for the installed playset.
