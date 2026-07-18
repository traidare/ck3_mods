# Common Errors and Debugging

> Reference docs: references/wiki/wiki_pages/Mod_troubleshooting.md

## Reading error.log

The error log is your primary debugging tool. Location:

- **Windows**:
  `%USERPROFILE%\Documents\Paradox Interactive\Crusader Kings III\logs\error.log`
- **macOS**: `~/Documents/Paradox Interactive/Crusader Kings III/logs/error.log`
- **Linux**:
  `~/.local/share/Paradox Interactive/Crusader Kings III/logs/error.log`

Launch with `-debug_mode` to get the error tracker in-game (Errorhoof icon). Run
`release_mode` in console to show the error counter on screen.

**Tip**: Newer errors appear at the top of the log. Clear the console to remove
old errors.

## Common Errors by Symptom

### "Unknown trigger/effect"

- **Cause**: Misspelled trigger/effect name, or using one that doesn't exist
- **Fix**: Check `triggers.log` or `effects.log` from `script_docs`. Never rely
  on memory — verify the exact name

### "Invalid scope type"

- **Cause**: Using a trigger/effect in the wrong scope (e.g., `is_ai` on a title
  scope)
- **Fix**: Check the "Supported Scopes" in `script_docs` logs. Use event targets
  to switch to the correct scope first

### "Unresolved event target"

- **Cause**: Referencing an event target that doesn't exist from the current
  scope, or typo in the name
- **Fix**: Check `event_targets.log` for valid targets and their input scopes

### Event doesn't fire

- **Cause**: Multiple possibilities:
  1. Missing namespace declaration at top of file
  2. Event ID doesn't match namespace (must be `namespace.number`)
  3. No on_action, decision, or other script fires the event
  4. Trigger block conditions not met
- **Fix**: Events don't fire automatically in CK3 (unlike older Paradox games).
  They must be triggered by something. Test with `event namespace.id` in console

### Localization not showing (shows key name instead)

- **Cause**: One of:
  1. File not encoded as UTF-8 BOM
  2. File not in correct language subfolder (`localization/english/`)
  3. File name doesn't include `_l_english` (or appropriate language)
  4. First line missing `l_english:`
  5. Typo in the loc key
- **Fix**: Check encoding first (most common issue). Save as "UTF-8 with BOM" in
  your editor

### "Duplicate hash" warning

- **Cause**: Two localization keys with the same name
- **Fix**: Search all loc files for the duplicate key and remove or rename one

### Character scope errors / "prev" issues

- **Cause**: `prev` only goes back one scope level in CK3 (no `prevprev`). Or
  using `scope:` before event targets
- **Fix**: Use `save_scope_as` to save references you'll need later. Only use
  `scope:` with saved scopes, never with event targets like `root` or `prev`

### Effects outside trigger blocks (or triggers in effect blocks)

- **Cause**: Mixing up trigger blocks (`limit`, `trigger`, `is_shown`) with
  effect blocks (`effect`, `immediate`, `on_accept`)
- **Fix**: Effects go in effect blocks, triggers go in trigger blocks.
  `limit = {}` inside `if = {}` is a trigger block; the effects go outside the
  limit but inside the if

### File not loading / changes not taking effect

- **Cause**: One of:
  1. File extension is wrong (must be `.txt` for script, `.yml` for loc, `.gui`
     for UI)
  2. File is in the wrong folder
  3. File name conflicts with vanilla (completely replaces it)
  4. Syntax error early in file prevents rest from loading
- **Fix**: Check error.log, verify folder structure matches vanilla

### Building not appearing in construction menu

- **Cause**: One of:
  1. Missing `is_enabled` or `can_construct` trigger
  2. `type` field wrong or missing (regular / special / duchy_capital)
  3. Building file not in `common/buildings/` or not a `.txt` file
  4. Syntax error in building definition (check error.log)
  5. `previous_building` doesn't match an existing building key
- **Fix**: Check error.log first. Verify building type, triggers, and file
  location

### Building modifiers not applying

- **Cause**: One of:
  1. Using `modifier` instead of `county_modifier` or `character_modifier`
  2. Invalid modifier name (check `modifiers.log` from script_docs)
  3. Building upgrade chain broken (`next_building` / `previous_building`
     mismatch)
- **Fix**: Check the .info file at
  `references/generated/info/common/buildings/_buildings.info` for valid fields

### Building localization shows raw key

- **Cause**: Wrong localization key prefix. Regular buildings use
  `building_<key>`, but some special buildings use `building_type_<key>`. Check
  vanilla examples for the specific building type.
- **Fix**: Look at vanilla localization for buildings of the same type to
  confirm the prefix pattern

## File Encoding Issues

**CRITICAL: ALL game files must be UTF-8 with BOM.** This is the #1 cause of "it
doesn't work" issues.

- **ALL files** (.txt, .yml, .gui, .asset): Must be **UTF-8 with BOM** encoding
- This applies to: event files, trait files, decision files, building files,
  localization files — **everything**
- The game will silently ignore or misparse files without BOM encoding
- **How to check**: In VS Code, look at the bottom-right status bar for "UTF-8
  with BOM". In Notepad++: Encoding menu → "Encode in UTF-8-BOM"
- **Line endings**: The game handles both LF and CRLF, but LF is preferred

## Useful Console Commands for Debugging

| Command                         | What it does                                    |
| ------------------------------- | ----------------------------------------------- |
| `event namespace.id`            | Fire an event on your character                 |
| `effect add_trait = trait_name` | Add a trait to test conditions                  |
| `effect add_gold = 1000`        | Give gold for testing                           |
| `trigger is_ai = no`            | Test a trigger on your character                |
| `script_docs`                   | Regenerate documentation logs                   |
| `release_mode`                  | Toggle error counter on screen                  |
| `run filename.txt`              | Execute a script from the `run/` folder         |
| `explorer`                      | Open the game explorer (includes script runner) |

## Hot-Loading

With `-debug_mode -develop` launch options, the game auto-reloads script and GUI
files when saved. Limitations:

- Works best for small, incremental changes
- Large changes may cause unexpected behavior — restart the game
- Localization can be updated at any time, but new keys may not hot-load
- Saved scopes are not updated when hot-loading events
