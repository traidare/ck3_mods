# grand_remembrance_119_runtime_fix — module state

Narrow runtime repair for **Grand Remembrance** (`3678529052`, version `1.9.0`)
with its AGOT compatibility submod (`3683507542`). Load position: immediately
after the Grand Remembrance AGOT compatibility submod.

## Ownership

Every override is generated from the Workshop parent:

- `gui/gr_chronicle_window.gui`
- `common/on_action/gr_on_actions.txt`
- `common/scripted_effects/gr_npc_obituary_data_effect.txt`

## Repairs and evidence

### Chronicle window visibility

The chronicle window's widget is loaded before a playable character exists. The
parent's `visible` expression always constructs `GetPlayer.MakeScope`, so the
`is_shown` trigger is invoked with an invalid character root and emits an
untyped `(no character)` error on every GUI refresh. Wrapping the call in
`And(GetPlayer.IsValid, ...)` does not help, because GUI data-function arguments
are evaluated eagerly.

### Obituary classification

The parent obituary processor assumes vanilla and optional RICE databases. AGOT
removes its fame traits, religion tags, culture heritages, and elective title
laws, so the first processed death produced a large batch of invalid database
lookups. The generated `gr_on_actions.txt` rebase disables only those
unsupported flavor-classification sections and the removed `born_in_the_purple`
check. Core memories, stats, personality, education, health, heir, score, and
AGOT-submod obituary data remain active.

The same rebase removes Grand Remembrance's RICE-presence revalidation. Its test
queries a RICE-only placeholder faith by database key, which itself is an
invalid lookup whenever RICE is not installed; this AGOT playset does not load
RICE, and the unsupported RICE obituary classifiers are already disabled.

### NPC obituary opinion

The generated `gr_npc_obituary_data_effect.txt` replaces the parent's
unsupported `scope:character.opinion:target` data-function chain. CK3 1.19
reports that expression as an opinion trigger with no target. The rebase uses
the game's `save_temporary_opinion_value_as` effect while the player and dead
NPC scopes are both valid, then stores that numeric value on the obituary.

## Generation

```sh
ck3mm mod generate grand_remembrance_119_runtime_fix
ck3mm mod generate grand_remembrance_119_runtime_fix --apply
```

The `mod.toml` manifest selects Grand Remembrance and this module's
destination-specific staged generator.

## Re-audit

The generator checks section markers and stops if a Grand Remembrance update
invalidates the assumptions. Recompare all overrides after every update to
Workshop mod `3678529052`.
