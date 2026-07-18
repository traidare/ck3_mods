# Load Order and File Overrides

Understanding how CK3 loads and merges files is critical for modding without
unintended side effects.

> Reference docs: references/wiki/wiki_pages/Mod_structure.md

## How Loading Works

1. **Vanilla loads first** — all files in the `game/` folder are loaded
2. **Mods load in order** — mods are loaded in the order defined in the
   launcher's mod list
3. **Later files override earlier ones** — if a mod file has the same path as a
   vanilla file, the mod file replaces it entirely

## File Override (Same-Name Replacement)

If your mod contains a file at the same relative path as a vanilla file, **your
file completely replaces the vanilla file**.

Example: if you create `your_mod/common/traits/00_traits.txt`, it will
**replace** the entire vanilla `00_traits.txt`. All vanilla traits defined in
that file will be lost unless you include them in your version.

**Best practice**: Copy the vanilla file, then modify your copy. This ensures
you don't accidentally remove vanilla content.

## replace_path

The `replace_path` directive in your `.mod` file tells the game to skip loading
all vanilla files from a specific folder.

```
replace_path = "history/characters"
```

This means:

- No vanilla files from `history/characters/` will be loaded
- Only your mod's files in that folder will be used
- Useful for total conversions that need to completely replace a category

**Warning**: `replace_path` applies to the exact folder, not subfolders. Use it
sparingly.

## Merged vs Replaced Files

Most files in CK3 are **replaced** (same-name override). However, some file
types are **merged**:

- **Localization files** are merged by key — you can override individual loc
  keys without replacing the entire file, if your file is in a `replace/`
  subfolder
- **Most common/ files** are merged by top-level key — if you define a new trait
  in a new .txt file, it's added alongside vanilla traits

### Adding New Content

To add new content without overriding vanilla:

1. Create a **new .txt file** with a unique name (e.g., `my_mod_traits.txt`)
2. Place it in the correct folder (e.g., `common/traits/`)
3. Define your content with unique keys

The game will load your file alongside vanilla files and merge them.

### Overriding Specific Content

To modify a specific vanilla definition:

1. Create a new file (or copy the vanilla file)
2. Use the **same key** as the vanilla definition you want to change
3. The game will use your definition instead (last loaded wins)

**Warning**: If you copy a vanilla file to override one entry, you must keep ALL
other entries in that file, or they will be lost.

## Mod Load Order Between Mods

When multiple mods are active:

- Mods lower in the launcher's list have higher priority
- If two mods modify the same file, the one loaded last wins
- There is no automatic merging between mods

For mod compatibility strategies, see
references/wiki/wiki_pages/Mod_compatibility.md.
