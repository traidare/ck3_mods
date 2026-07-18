# Modifying the GUI — Practical Recipe

## What You Need to Know First

CK3's GUI uses `.gui` files (similar to HTML) in the `gui/` folder. GUI mods
change the checksum but since patch 1.9 they don't disable achievements. Use
`-debug_mode -develop` launch options for auto-reloading.

> Reference docs: references/wiki/wiki_pages/Interface.md

## Minimal Template — Adding a Button to an Existing Window

### gui/my_mod_patch.gui

```
# Override a type to add content
types MyModTypes {
	type my_custom_button = button_round {
		onclick = "[GetScriptedGui('my_scripted_gui').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
		tooltip = "MY_BUTTON_TOOLTIP"

		button_icon = "gfx/interface/icons/flat_icons/window_close.dds"
	}
}
```

### common/scripted_guis/my_scripted_guis.txt

```
my_scripted_gui = {
	scope = character

	is_shown = {
		is_ai = no
	}

	effect = {
		add_gold = 100
	}
}
```

Scripted GUIs are the bridge between the UI layer and game script. They let
buttons execute effects.

## Annotated Vanilla Example

<!-- TODO: Add a real vanilla GUI example. Check:
$CK3_GAME_DIR/gui/ for a simple window file. -->

## Common Variants

### Displaying a variable in the UI

```
# In GUI file:
text_single = {
	text = "[GetPlayer.MakeScope.Var('my_variable').GetValue]"
}
```

### Displaying a script value

```
text_single = {
	text = "[GuiScope.SetRoot(GetPlayer.MakeScope).ScriptValue('my_script_value')|0]"
}
```

### Conditional visibility

```
widget = {
	visible = "[GetPlayer.MakeScope.Var('show_widget').IsSet]"
	# widget content
}
```

### Using blockoverride to modify vanilla windows

```
# Override a specific block in a vanilla type
types MyModOverrides {
	type hud_bottom_overlay = hud_bottom_overlay {
		blockoverride "extra_content" {
			my_custom_button = {}
		}
	}
}
```

## Checklist

- [ ] GUI file in `gui/` folder with `.gui` extension
- [ ] Scripted GUI in `common/scripted_guis/` if executing effects
- [ ] Localization for all tooltip text
- [ ] Test with `-debug_mode -develop` for auto-reload
- [ ] Check errors with `release_mode` console command
- [ ] Use `tweak gui.debug` to inspect UI elements

## Common Pitfalls

- **GUI crashes**: Can crash the game. Always test incrementally. Common crash
  causes: referencing non-existent data models, invalid type names
- **No new hotkeys**: The game ignores `.shortcuts` files from mods. You can
  only reuse existing hotkeys
- **Script in GUI**: You can't use regular script in GUI files. Use Scripted
  GUIs to bridge the gap
- **Data model scope**: GUI elements can only access data that's been exposed by
  the game code. Use `dump_data_types` console command to see what's available
- **File loading order**: GUI files load in alphabetical order. If overriding
  vanilla types, your file must load after the original
