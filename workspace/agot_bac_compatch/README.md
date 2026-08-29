# agot_bac_compatch — module state

Generated layer owning the two lobby GUI files AGOT and Build-a-Courtier both
write. Those two are its only parents.

## Ownership

Build-a-Courtier whole-file overrides `gui/multiplayer_types.gui` and loads
later, dropping both of AGOT's edits to it. AGOT is the authority here; the
generator replays Build-a-Courtier's delta onto AGOT's copy, so both edits
survive:

- `agot_create_landless_pirate_button` keeps its call site.
- The landless-adventurer button keeps AGOT's `enabled` gate excluding
  `ruins_government`, `unknown_government`, and `wilderness_government`.

Replayed: the set-intent call site, the two courtier buttons, and the
clear-intent call site on each of the three vanilla designer buttons.

Build-a-Courtier's commenting-out of those three buttons' `visible`/`enabled`
gates is deliberately **not** replayed. The gates are AGOT's, one of them
AGOT-authored, and the courtier button carries its own `landless_playable` gate
instead.

### The pirate button

`gui/custom_gui/agot_multiplayer_types.gui` is owned for one reason. AGOT's
pirate button opens the same `landless_adventurer` designer mode
Build-a-Courtier hooks, and that path runs
`create_landless_adventurer_title_effect` — so a designed pirate reaches
`on_ruler_designer_finished` holding `landless_adventurer_government`.

Build-a-Courtier clears its stale intent flag on the three buttons it knows
about. AGOT's is a fourth, so arming the flag, cancelling, then designing a
pirate the same day satisfies both limits in `custom_courtier.0002` and converts
the pirate, destroying their camp. The generator adds the same clear as the
first `onclick` there.

The scripted GUIs and the `.0002` hook stay Build-a-Courtier's; this module adds
call sites only. The `on_ruler_designer_finished` hooks need no merge — CK3
merges on_action files additively and the parents declare theirs in different
files.

### Narrow runtime repair

Both courtier buttons point at `gfx/interface/icons/flat_icons/character.dds`,
which exists in no parent, so the icon never draws; ck3-tiger reports
`missing-file`. The generator substitutes `add_character.dds`.
`assert_parent_delta` asserts the broken reference still appears twice upstream,
so the repair drops itself once the parent fixes it.

The remaining ck3-tiger warning,
`GetTransferSpeedSettingIndex returns int32 but a CVector2i is needed here`, is
vanilla's.

## Load order

After Build-a-Courtier. It carries AGOT's copies of both files, so it may sit
anywhere after that.

## Generation

```sh
ck3mm mod generate agot_bac_compatch
ck3mm mod generate agot_bac_compatch --apply
```

Every input is pinned by SHA-256 in `PINS`, vanilla included, so all three sides
of the merge are known inputs. Each output is written in its parent's encoding:
`multiplayer_types.gui` keeps its UTF-8 BOM, `agot_multiplayer_types.gui` has
none, both CRLF.

**Re-audit** on a pin mismatch, when either parent changes the lobby designer
buttons, or when AGOT adds another entry point into the `landless_adventurer`
designer — a new one needs the same clear-intent call site as the four existing
buttons.
