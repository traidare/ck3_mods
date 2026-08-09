# Vanilla Game Folder Tree

The CK3 `game/` folder contains all game data. Mods override these files by
mirroring the folder structure.

## Top-Level Folders

| Folder            | Role                                                                 | Modding Frequency |
| ----------------- | -------------------------------------------------------------------- | ----------------- |
| `common/`         | Core game definitions (traits, decisions, religions, cultures, etc.) | **Very often**    |
| `events/`         | All game events (.txt files with namespaced events)                  | **Very often**    |
| `localization/`   | All display text, organized by language                              | **Very often**    |
| `gfx/`            | Graphical assets (icons, textures, portraits, CoA)                   | Often             |
| `gui/`            | UI layout files (.gui)                                               | Often             |
| `history/`        | Historical data (characters, titles, provinces)                      | Often             |
| `map_data/`       | Map definitions (provinces, terrain, rivers)                         | Rarely            |
| `content_source/` | Source assets (not loaded by the game)                               | Never             |
| `fonts/`          | Font files                                                           | Rarely            |
| `music/`          | Music files and playlists                                            | Sometimes         |
| `sound/`          | Sound effects                                                        | Sometimes         |
| `tools/`          | Development tools                                                    | Never             |

## common/ Subfolders

The `common/` folder is where most modding happens. Key subfolders:

| Subfolder                            | Contents                              | File Type |
| ------------------------------------ | ------------------------------------- | --------- |
| `common/traits/`                     | Character trait definitions           | .txt      |
| `common/decisions/`                  | Player and AI decisions               | .txt      |
| `common/character_interactions/`     | Character interaction definitions     | .txt      |
| `common/on_actions/`                 | On_action event triggers (game hooks) | .txt      |
| `common/scripted_effects/`           | Reusable effect templates             | .txt      |
| `common/scripted_triggers/`          | Reusable trigger templates            | .txt      |
| `common/script_values/`              | Calculated values usable in script    | .txt      |
| `common/scripted_modifiers/`         | Weight modifier templates             | .txt      |
| `common/culture/`                    | Culture and culture group definitions | .txt      |
| `common/religion/religions/`         | Religion and faith definitions        | .txt      |
| `common/religion/religion_families/` | Religion family definitions           | .txt      |
| `common/landed_titles/`              | Title hierarchy (empires to baronies) | .txt      |
| `common/coat_of_arms/`               | Coat of arms definitions              | .txt      |
| `common/defines/`                    | Game defines (numeric constants)      | .txt      |
| `common/governments/`                | Government type definitions           | .txt      |
| `common/laws/`                       | Law definitions                       | .txt      |
| `common/casus_belli_types/`          | Casus belli definitions               | .txt      |
| `common/schemes/`                    | Scheme type definitions               | .txt      |
| `common/lifestyle_perks/`            | Lifestyle perk definitions            | .txt      |
| `common/modifiers/`                  | Modifier definitions                  | .txt      |
| `common/dynasties/`                  | Dynasty definitions                   | .txt      |
| `common/dynasty_houses/`             | Dynasty house definitions             | .txt      |
| `common/genes/`                      | Portrait gene definitions             | .txt      |
| `common/dna_data/`                   | Preset DNA for characters             | .txt      |
| `common/game_concepts/`              | Game concept tooltip definitions      | .txt      |
| `common/bookmark_portraits/`         | Bookmark screen portrait configs      | .txt      |

## events/

Contains .txt files with namespaced events. Each file typically starts with
`namespace = event_namespace` and contains one or more event definitions.

## localization/

Organized by language: `localization/english/`, `localization/french/`, etc.
Files must be named `*_l_english.yml` (or appropriate language suffix) and
encoded as UTF-8 BOM.

## gfx/

| Subfolder           | Contents                                             |
| ------------------- | ---------------------------------------------------- |
| `gfx/interface/`    | UI icons, illustrations, decision images             |
| `gfx/portraits/`    | Portrait-related assets (genes, modifiers, palettes) |
| `gfx/coat_of_arms/` | CoA patterns, emblems (textured and colored)         |
| `gfx/models/`       | 3D model assets                                      |
| `gfx/map/`          | Map textures                                         |

## gui/

Contains .gui files that define the game's user interface layout. Key files and
folders:

- `gui/window_*.gui` — main game windows
- `gui/event_windows/` — event display templates
- `gui/decision_view_widgets/` — custom decision widgets
- `gui/preload/textformatting.gui` — text formatting styles

## history/

| Subfolder             | Contents                                      |
| --------------------- | --------------------------------------------- |
| `history/characters/` | Historical character definitions              |
| `history/titles/`     | Title holder history                          |
| `history/provinces/`  | Province setup (buildings, culture, religion) |
| `history/wars/`       | Historical war setups                         |

## .info Files

The game ships with `.info` files — Paradox's official syntax documentation for
each moddable system. They document every valid key, type, and value. After
running `ck3mm refs sync`, these are available at `references/generated/info/`.

| Location in game                                             | What it documents                            |
| ------------------------------------------------------------ | -------------------------------------------- |
| `common/buildings/_buildings.info`                           | Building keys, types, modifiers              |
| `common/traits/_traits.info`                                 | Trait keys, categories, modifiers, XP tracks |
| `common/character_interactions/_character_interactions.info` | Interaction structure, AI logic              |
| `common/decisions/_decisions.info`                           | Decision structure, widgets, AI              |
| `common/casus_belli_types/_casus_belli_types.info`           | CB structure, war scoring                    |
| `common/on_actions/_on_actions.info`                         | On_action hooks and scopes                   |
| `common/scripted_effects/_scripted_effects.info`             | Scripted effect syntax                       |
| `common/scripted_triggers/_scripted_triggers.info`           | Scripted trigger syntax                      |
| `common/culture/_culture.info`                               | Culture definitions                          |
| `common/religion/religions/_religions.info`                  | Religion and faith definitions               |
| `events/_events.info`                                        | Event structure, portraits, themes           |
| `gfx/...`                                                    | Graphical asset definitions                  |
| `gui/...`                                                    | GUI widget definitions                       |

There are ~165 .info files total across all systems. Always check the relevant
.info file before writing code for a system you haven't worked with before.

<!-- TODO: Run `find "$CK3_GAME_DIR" -type d -maxdepth 2` with actual game files to verify and complete this tree. -->
