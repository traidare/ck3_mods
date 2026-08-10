# Grand Remembrance 1.8.2 - CK3 1.19 Runtime Fix

Narrow runtime repair for **Grand Remembrance** (`3678529052`, version `1.8.2`)
with its AGOT compatibility submod (`3683507542`).

Load this mod immediately after the Grand Remembrance AGOT compatibility submod.

## Repair

The chronicle window exists before a playable character does. Its original
`visible` expression always constructed `GetPlayer.MakeScope`, so the `is_shown`
trigger was sometimes invoked with an invalid character root and emitted an
untyped `(no character)` error on every GUI refresh. Wrapping the call in
`And(GetPlayer.IsValid, ...)` did not help because GUI data-function arguments
are evaluated eagerly.

This mod overrides:

- `common/decisions/gr_decisions.txt`, mirroring the character open flag to a
  scope-free global visibility flag;
- `gui/gr_chronicle_window.gui`, reading that global flag without constructing a
  player scope; and
- `gr_chronicle_close`, clearing both the global visibility flag and the
  parent's character variables.

The original character variables still own all chronicle page state. The global
flag only controls whether the window exists on screen.

The parent obituary processor also assumes vanilla and optional RICE databases.
AGOT removes its fame traits, religion tags, culture heritages, and elective
title laws, so the first processed death produced a large batch of invalid
database lookups. The generated `gr_on_actions.txt` rebase disables only those
unsupported flavor-classification sections and the removed `born_in_the_purple`
check. Core memories, stats, personality, education, health, heir, score, and
AGOT-submod obituary data remain active.

The same rebase removes Grand Remembrance's RICE-presence revalidation. Its test
queries a RICE-only placeholder faith by database key, which itself is an
invalid lookup whenever RICE is not installed; this AGOT playset does not load
RICE, and the unsupported RICE obituary classifiers are already disabled.

The generated `gr_npc_obituary_data_effect.txt` also replaces the parent's
unsupported `scope:character.opinion:target` data-function chain. CK3 1.19
reports that expression as an opinion trigger with no target. The rebase uses
the game's `save_temporary_opinion_value_as` effect while the player and dead
NPC scopes are both valid, then stores that numeric value on the obituary.

Generate the obituary override from the current Grand Remembrance source with:

```sh
ck3mm mod generate grand_remembrance_119_runtime_fix
ck3mm mod generate grand_remembrance_119_runtime_fix --apply
```

The per-mod manifest selects Grand Remembrance and this module's
destination-specific staged generator. It checks section markers and stops if a
Grand Remembrance update invalidates the assumptions. Recompare all overrides
after every update to Workshop mod `3678529052`.
