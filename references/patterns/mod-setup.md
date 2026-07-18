# Setting Up a New Mod — Practical Recipe

## What You Need to Know First

Every CK3 mod needs two things: a `.mod` file (metadata) and a mod folder
(content). The easiest way to create these is through the game launcher, but you
can also set them up manually.

> Reference docs: references/wiki/wiki_pages/Mod_structure.md

## Minimal Template

### descriptor.mod (inside your mod folder)

```
version="1.0.0"
tags={
	"Events"
	"Gameplay"
}
name="My Mod Name"
supported_version="1.12.*"
```

### my_mod_name.mod (alongside your mod folder)

```
version="1.0.0"
tags={
	"Events"
	"Gameplay"
}
name="My Mod Name"
supported_version="1.12.*"
path="mod/my_mod_name"
```

The `.mod` file alongside the folder MUST include the `path` key. The
`descriptor.mod` inside the folder does NOT need it.

### Minimal Folder Structure

```
my_mod_name/
├── descriptor.mod
├── common/
│   └── (subfolders as needed)
├── events/
│   └── my_events.txt
└── localization/
    └── english/
        └── my_mod_l_english.yml
```

## Annotated Vanilla Example

<!-- TODO: Add a real vanilla descriptor.mod example. Check:
$CK3_GAME_DIR/../descriptor.mod
-->

## Common Variants

### Adding a decision (minimum files)

```
my_mod/
├── descriptor.mod
├── common/
│   └── decisions/
│       └── my_decisions.txt
└── localization/
    └── english/
        └── my_decisions_l_english.yml
```

### Adding events with scripted effects

```
my_mod/
├── descriptor.mod
├── common/
│   └── scripted_effects/
│       └── my_scripted_effects.txt
├── events/
│   └── my_events.txt
└── localization/
    └── english/
        └── my_events_l_english.yml
```

### Using replace_path for total conversion

Add to both .mod files:

```
replace_path = "history/characters"
replace_path = "common/traits"
```

This skips all vanilla files in those folders.

## Checklist

- [ ] `descriptor.mod` inside the mod folder (no `path` key)
- [ ] `.mod` file alongside the mod folder (with `path` key)
- [ ] Both files have matching `name`, `version`, `tags`, `supported_version`
- [ ] `supported_version` matches your CK3 version (use `*` wildcard for patch)
- [ ] Mod appears in the launcher under "All Installed Mods"
- [ ] Folder structure mirrors vanilla for the content you're adding

## Common Pitfalls

- **Mod not showing in launcher**: Check that both `.mod` files exist and have
  valid syntax. Quotation marks around all values are required.
- **Name too short**: Mod name must be at least 3 characters
- **Path issues**: The `path` key can be relative (`mod/my_mod`) or absolute.
  Relative paths are relative to the CK3 user folder, not the game folder.
- **Non-English characters in path**: If your Windows username has non-English
  characters, the default mod path may not work. Use a directory outside your
  Documents folder.
- **Case sensitivity**: Folder and file names are case-sensitive on macOS and
  Linux
- **File encoding**: ALL game files (.txt, .yml, .gui) must be UTF-8 with BOM —
  not just localization. The game logs warnings for files without BOM and may
  fail to parse them
