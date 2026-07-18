# AGOT Extension: GUI

> This guide extends [references/patterns/gui.md](../patterns/gui.md) with
> AGOT-specific changes.

## What AGOT Changes

AGOT massively extends the vanilla GUI system. Key changes:

- **Entirely new windows** for dragons, Kingsguard, Free Cities councils, spy
  networks, mega-wars, and more — all opened via `GetVariableSystem` or custom
  game views.
- **Vanilla window overrides** — the character window, council window, HUD,
  outliner, county view, war overview, title window, faith window, and many
  others are replaced or extended with AGOT-specific versions in
  `gui/custom_gui/`.
- **Shared GUI types** in `gui/shared/` — reusable dragon portraits,
  AGOT-specific button/icon types, custom cooltip (tooltip) inserts, coat of
  arms, text icons, and map mode legends.
- **Custom event windows** — dragon events, multi-duel events, feast events, and
  a character customizer event all have dedicated GUI layouts in
  `gui/event_windows/`.
- **Event window widgets** — dragon egg selection, artifact selection, Valyrian
  steel selection, character selection (2/3/4/5 options), dragon customizer, and
  shader effects (fire, snow, wildfire) in `gui/event_window_widgets/`.
- **Scripted widgets** — `gui/scripted_widgets/agot_scripted_widgets.txt`
  registers custom windows like the dragon tree, knight tree, and artifact
  market.
- **Templates** for dragon visibility checks — used throughout AGOT to toggle
  elements based on whether a character is a dragon, a dragon rider, or neither.

## AGOT GUI Files

### gui/custom_gui/ — Vanilla Window Overrides and New Windows

| File                               | Purpose                                                                  |
| ---------------------------------- | ------------------------------------------------------------------------ |
| `agot_character_window.gui`        | Overrides vanilla character window (adds dragon/bastard/knight displays) |
| `agot_dragon_character_window.gui` | Complete dragon character view (rider, host, bonded human, stats)        |
| `agot_kingsguard.gui`              | Kingsguard tab in the council window (7 slots: Lord Commander + 6)       |
| `agot_council_window.gui`          | Council window modifications (adds Kingsguard tab)                       |
| `agot_hud.gui`                     | HUD additions (dragon army composition, settlement limit)                |
| `agot_hud_outliner.gui`            | Outliner modifications                                                   |
| `agot_free_cities_window.gui`      | Three Daughters / Free Cities council window                             |
| `agot_dragon_tree.gui`             | Dragon family tree (custom game view)                                    |
| `agot_knight_tree.gui`             | Knight lineage tree (custom game view)                                   |
| `agot_spy_network_window.gui`      | Spy network management window                                            |
| `agot_mega_wars.gui`               | Mega-war (multi-realm war) display                                       |
| `agot_title.gui`                   | Title window modifications                                               |
| `agot_faith_window.gui`            | Faith window modifications                                               |
| `agot_county_view_window.gui`      | County view modifications                                                |
| `agot_declare_war_window.gui`      | War declaration modifications                                            |
| `agot_war_overview.gui`            | War overview modifications                                               |
| `agot_artifacts_sell.gui`          | Artifact market window (registered as scripted widget)                   |
| `agot_bookmarks.gui`               | Custom bookmark screen                                                   |
| `agot_ruler_designer.gui`          | Ruler designer modifications                                             |
| `agot_menu.gui`                    | Main menu modifications                                                  |
| `agot_legitimate_house.gui`        | House legitimization GUI                                                 |
| `agot_patron_window.gui`           | Patron/banking window                                                    |
| `agot_esr_types.gui`               | ESR (Extended Succession Rules) types                                    |
| `agot_event_shaders.gui`           | Custom event background shaders                                          |

### gui/shared/ — Reusable AGOT Types

| File                              | Purpose                                                                                |
| --------------------------------- | -------------------------------------------------------------------------------------- |
| `agot_buttons_icons.gui`          | AGOT-specific button icon types (dragon capture, dragonpit, knight tree, colonization) |
| `agot_dragon_portraits.gui`       | Dragon portrait types for small/relationship displays                                  |
| `agot_cooltip.gui`                | Character tooltip name flavoring (Ser, Maester, Silent Sister, bastard)                |
| `agot_coat_of_arms.gui`           | AGOT coat of arms modifications                                                        |
| `agot_texticons.gui`              | Text icons for AGOT MaA types, dragon stats, and more                                  |
| `agot_mapmodes.gui`               | Map mode buttons and legends (roads map mode)                                          |
| `agot_lists.gui`                  | Custom list types                                                                      |
| `agot_character_event_window.gui` | Shared character event window types                                                    |
| `agot_dragon_event_window.gui`    | Shared dragon event window types                                                       |
| `agot_fake_death_portraits.gui`   | Portraits for "fake death" characters                                                  |
| `agot_custom_background.gui`      | Custom background widgets                                                              |

### gui/event_windows/ — Custom Event Layouts

| File                                    | Purpose                            |
| --------------------------------------- | ---------------------------------- |
| `agot_dragon_character_event.gui`       | Dragon-specific character events   |
| `agot_dragon_duel_event.gui`            | Dragon vs dragon duel events       |
| `agot_multi_duel_event_window.gui`      | Multi-character duel events        |
| `agot_multi_duel_team_event_window.gui` | Team-based duel events             |
| `agot_character_event_huge.gui`         | Extra-large character event window |
| `agot_customizer_event.gui`             | Character customizer event         |
| `agot_lmf_feast_event_window.gui`       | Feast event window                 |

### gui/event_window_widgets/ — Event Selection Widgets

| File                                         | Purpose                        |
| -------------------------------------------- | ------------------------------ |
| `agot_dragon_egg_selection.gui`              | Dragon egg picker              |
| `agot_dragon_tree_selection.gui`             | Dragon tree picker             |
| `agot_dragon_customizer.gui`                 | Dragon appearance customizer   |
| `agot_artifact_selection.gui`                | Artifact picker                |
| `agot_artifact_valyrian_steel_selection.gui` | Valyrian steel artifact picker |
| `agot_character_selection_two_options.gui`   | 2-option character picker      |
| `agot_character_selection_three_options.gui` | 3-option character picker      |
| `agot_character_selection_four_options.gui`  | 4-option character picker      |
| `agot_character_selection_five_options.gui`  | 5-option character picker      |
| `agot_event_shader_fire.gui`                 | Fire shader effect overlay     |
| `agot_event_shader_snow.gui`                 | Snow shader effect overlay     |
| `agot_event_shader_wildfire.gui`             | Wildfire shader effect overlay |

### gui/scripted_widgets/agot_scripted_widgets.txt

Registers custom windows as scripted widgets (game views opened via
`GetScriptedGui`):

```
gui/custom_gui/agot_artifacts_sell.gui = agot_artifact_market_window_open
gui/custom_gui/agot_dragon_tree.gui = agot_dragon_tree
gui/custom_gui/agot_knight_tree.gui = agot_knight_tree
```

## AGOT-Specific Template

### Adding a button to the AGOT dragon character window

```
# gui/my_submod_dragon_patch.gui
types CharacterWindow
{
	type my_submod_dragon_button = button_normal
	{
		name = "my_submod_action"
		datacontext = "[GetScriptedGui('my_submod_dragon_action')]"
		visible = "[ScriptedGui.IsShown( GuiScope.SetRoot( CharacterWindow.GetCharacter.MakeScope ).AddScope('owner', GetPlayer.MakeScope ).End)]"
		enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( CharacterWindow.GetCharacter.MakeScope ).AddScope('owner', GetPlayer.MakeScope ).End)]"
		tooltip = "MY_SUBMOD_ACTION_TT"
		using = tooltip_ne
		size = { 35 35 }

		icon_round_button_base = {}

		button_icon = {
			texture = "gfx/interface/icons/flat_icons/my_submod_icon.dds"
			onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( CharacterWindow.GetCharacter.MakeScope ).AddScope('owner', GetPlayer.MakeScope ).End)]"
			size = { 35 35 }
			parentanchor = center
		}
	}
}
```

### Using AGOT dragon visibility templates

```
# These templates are defined in agot_dragon_character_window.gui
# and used throughout AGOT to conditionally show/hide elements

widget = {
	using = visible_if_dragon          # visible = "[IsCharacterDragon]"
	# content shown only for dragon characters
}

widget = {
	using = visible_if_not_dragon      # visible = "[Not(IsCharacterDragon)]"
	# content shown only for non-dragon characters
}

widget = {
	using = visible_if_dragonrider_flight  # checks ScriptedGui 'dragonrider_flight'
	# content shown only when character is a dragonrider in flight
}
```

### Creating a standalone AGOT window (like Free Cities)

```
# gui/custom_gui/my_submod_window.gui
window = {
	name = "my_submod_window"
	widgetid = "my_submod_window"
	allow_outside = yes
	movable = yes
	size = { 700 100% }
	parentanchor = center|center
	visible = "[GetVariableSystem.Exists('my_submod_window')]"
	using = Window_Background
	using = Window_Decoration
	using = Animation_ShowHide_Standard
	layer = top

	vbox = {
		using = Window_Margins
		restrictparent_min = yes

		header_pattern_interaction = {
			layoutpolicy_horizontal = expanding

			blockoverride "header_text"
			{
				text = "MY_SUBMOD_WINDOW_TITLE"
			}

			blockoverride "button_close"
			{
				onclick = "[GetVariableSystem.Clear( 'my_submod_window' )]"
			}
		}

		# Window content goes here
	}
}
```

To open this window from a scripted GUI effect, set the variable system:

```
# In common/scripted_guis/
my_submod_open_window = {
	scope = character
	effect = {
		# The window is toggled via GetVariableSystem in the GUI itself
	}
}
```

## Annotated AGOT Example

The Kingsguard tab in the council window (`gui/custom_gui/agot_kingsguard.gui`)
demonstrates how AGOT adds a full new tab to an existing vanilla window.

```
types Kingsguard
{
	# Tab button row — added to the council window header
	type agot_kingsguard_council_tabs_hbox = hbox
	{
		layoutpolicy_horizontal = expanding
		# Only visible if player is independent AND has the Kingsguard mechanic
		visible = "[And(GetPlayer.IsIndependentRuler, GetScriptedGui('kingsguard_tab').IsShown(GuiScope.SetRoot(GetPlayer.MakeScope).End))]"

		# Vanilla council tab (re-created to sit alongside the new tab)
		button_tab = {
			layoutpolicy_horizontal = expanding
			down = "[GetVariableSystem.HasValue('council_tabs','my_council')]"
			onclick = "[CouncilWindow.SetPlayerCouncil]"
			onclick = "[GetVariableSystem.Set('council_tabs', 'my_council')]"
			# ...
		}

		# AGOT Kingsguard tab button
		agot_kingsguard_tab_button = {}
	}

	# The tab button type itself
	type agot_kingsguard_tab_button = button_tab
	{
		visible = "[GetScriptedGui('kingsguard_tab').IsShown(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
		# Uses GetVariableSystem to track which tab is active
		down = "[GetVariableSystem.HasValue('council_tabs','kingsguard')]"
		onclick = "[GetVariableSystem.Set('council_tabs','kingsguard')]"
		# ...
	}

	# The tab content — 7 council slots (Lord Commander + 6 members)
	type agot_kingsguard_tab_layout = vbox
	{
		vbox = {
			# Only shown when the Kingsguard tab is selected
			visible = "[GetVariableSystem.HasValue('council_tabs','kingsguard')]"
			using = Animation_Tab_Switch

			agot_kingsguard_lord_commander_row = {}
			agot_kingsguard_second_row = {}      # kingsguard_1, kingsguard_2
			agot_kingsguard_third_row = {}       # kingsguard_3, kingsguard_4
			agot_kingsguard_fourth_row = {}      # kingsguard_5, kingsguard_6
		}
	}

	# Each row uses the vanilla widget_councillor_item with AGOT council positions
	type agot_kingsguard_lord_commander_row = hbox
	{
		widget_councillor_item = {
			datacontext = "[CouncilWindow.GetCouncillor('kingsguard_lord_commander')]"
			datacontext = "[GuiCouncilPosition.GetActiveCouncilTask]"
			datacontext = "[ActiveCouncilTask.GetPositionType]"
			datacontext = "[ActiveCouncilTask.GetCouncillor]"
			# ...
		}
	}
}
```

Key patterns visible here:

- **`GetScriptedGui(...).IsShown()`** gates visibility on game-logic conditions
  defined in script.
- **`GetVariableSystem.HasValue()`** / `.Set()` / `.Clear()` manages tab state
  entirely in the GUI layer — no script needed for tab switching.
- **Vanilla types reused** — `widget_councillor_item`, `button_tab`,
  `header_pattern_interaction` are all vanilla types that AGOT slots its data
  into via `datacontext` and `blockoverride`.

## Key Differences from Vanilla

| Aspect                | Vanilla                             | AGOT                                                                                           |
| --------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| **File organization** | Single folder (`gui/`)              | Split into `gui/custom_gui/`, `gui/shared/`, `gui/event_windows/`, `gui/event_window_widgets/` |
| **Type namespaces**   | Standard (`types CharacterWindow`)  | Same namespaces but adds many `agot_*` prefixed types                                          |
| **Visibility logic**  | Simple data model checks            | Heavy use of `GetScriptedGui('...').IsShown()` for game-logic gating                           |
| **Tab switching**     | Built-in window controllers         | `GetVariableSystem.Set/HasValue/Clear` for custom tab state                                    |
| **Dragon characters** | Not a concept                       | `[IsCharacterDragon]` check, dedicated templates (`visible_if_dragon`, etc.)                   |
| **Custom windows**    | Opened via game views               | Mix of `GetVariableSystem.Exists('window_name')` and scripted widget registration              |
| **Tooltip overrides** | Standard cooltip                    | Custom cooltip inserts for Ser/Maester/bastard name flavoring                                  |
| **Scope passing**     | `GuiScope.SetRoot(...)`             | Often uses `.AddScope('owner', GetPlayer.MakeScope)` for multi-scope checks                    |
| **Portrait types**    | Standard `portrait_head_small` etc. | Additional `agot_dragons_portrait_head_small` with dragon-specific camera/environment          |
| **Text icons**        | Vanilla icon set                    | Hundreds of AGOT text icons (MaA types, dragon stats, etc.) in `gui/shared/agot_texticons.gui` |

## AGOT Pitfalls

1. **Type namespace collisions** — AGOT adds types into existing vanilla
   namespaces (`types CharacterWindow`, `types HUD`, `types GameTooltipTypes`,
   etc.). If your submod defines a type with the same name as an AGOT type, one
   will silently override the other depending on file load order. Always prefix
   your types with your submod name.

2. **ScriptedGui dependencies** — Many AGOT GUI elements depend on specific
   scripted GUIs (`agot_check_host`, `agot_check_rider`, `kingsguard_tab`,
   `agot_can_see_dragon_military_view`, etc.). If you blockoverride an AGOT
   section that references these, the scripted GUIs must still exist or the GUI
   will error.

3. **Dragon character detection** — AGOT uses `[IsCharacterDragon]` (a promoted
   data function, not a scripted GUI) to detect dragon characters. This is used
   in templates like `visible_if_dragon` / `visible_if_not_dragon`. If you
   modify the character window, you must account for dragon characters rendering
   differently.

4. **Variable system window management** — AGOT standalone windows (like the
   Free Cities window) use `GetVariableSystem.Exists('window_three_daughters')`
   for visibility. If you need to close an AGOT window before opening yours, you
   must `Clear` the correct variable name.

5. **Custom event widget naming** — AGOT event window widgets in
   `gui/event_window_widgets/` follow a strict naming pattern used by event
   definitions. If you create a new event widget, ensure your event definition
   references the exact widget type name.

6. **Shared type load order** — Files in `gui/shared/` load before files in
   `gui/custom_gui/`. AGOT defines reusable types (button icons, portrait types,
   cooltip inserts) in `shared/` and consumes them in `custom_gui/`. If your
   submod overrides a shared type, ensure your file also lives in `gui/shared/`
   to load at the right time.

7. **Multiple datacontext stacking** — AGOT frequently stacks multiple
   `datacontext` directives on a single widget (see the Kingsguard rows). Each
   `datacontext` provides a different data model to child elements. Getting the
   order wrong will cause silent data mismatches.

8. **Dynamic background scaling** — The dragon character window uses complex
   math expressions in `margin_top` to scale the background based on
   `dragon_size`. Avoid overriding background properties on dragon windows
   without understanding the scaling formula.

9. **Coat of arms overrides** — AGOT overrides coat of arms rendering in both
   `gui/shared/agot_coat_of_arms.gui` and `gui/shared/coat_of_arms.gui` (a
   vanilla filename replacement). If your submod also modifies coat of arms
   display, expect conflicts.

10. **Scripted widget registration** — Custom game views (dragon tree, knight
    tree, artifact market) must be registered in
    `gui/scripted_widgets/agot_scripted_widgets.txt`. If you add a new game view
    window, register it there or it will not open.
