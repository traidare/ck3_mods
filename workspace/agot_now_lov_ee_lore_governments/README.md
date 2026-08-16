# agot_now_lov_ee_lore_governments — module state

Generated government, culture, and Ibben faith-history integration for the
current AGOT, NOW, Legacy of Valyria, and Essos Expanded playset. Load position:
immediately after `agot_now_lov_ee_world_data`, before the generic runtime-fix
and full-playset compatches.

## Ownership

This module intentionally owns the effective history files it emits under
`history/titles`, `history/characters`, and `history/provinces`, plus the
effective `00_agot_character_data_effects.txt` scripted-effect file.

The full-file history overrides are generated because CK3 merges history by
filename and title/character/province key; small fragments cannot safely amend
every dated holder without risking duplicate keys or losing later parent
history. The generator first reconstructs the effective LoV/EE source layer,
including the map compatch's cleaned history winners, then makes only the
audited government, culture, faith, legitimacy, and flavor-effect changes.

The map compatch publishes `artifacts/map_data/removed_titles.json`. This
generator excludes those titles from government planning and removes all 215
matching effective title-history blocks from its later full-file overrides.

The effective character-title dispatcher starts with
`Essos Expanded - TempLoV/NOW Compatch`, the final Workshop compatch in the
required chain. This module transforms that dispatcher in place: it preserves
its AGOT mapping semantics, adds the two lore government fallbacks through
AGOT's feudal path, and carries no government lists of its own.

This module does not own landed-title structure, map data, terrain, holdings,
names, dynasties, or unrelated faith history.

## Lore policy

The source of truth is `assets/lore_governments/government_lore_rules.csv`. Its
confidence and source columns distinguish direct lore from conservative gameplay
interpretations. In summary:

- Dothraki and Jogos Nhai rulers are nomadic; the Dosh Khaleen are theocratic.
- Norvos and the Red Priesthood are theocratic.
- the Free Cities use administrative or oligarchic forms according to their
  described ruling institutions;
- the Ghiscari slave cities, Valyrian Freehold, and Qarth use oligarchic
  government;
- Yi Ti uses celestial government for the God-Emperor and meritocratic
  government below him; Leng uses mandala government;
- poorly described or decentralized peoples use conservative tribal, clan, or
  feudal approximations recorded individually in the rules table; and
- explicit pirate, ruin, wilderness, unknown, and landless governments are
  preserved instead of being overwritten by geographic rules.

Ibben deliberately changes at the Doom on `7899.8.14`. Earlier rulers and
provinces retain `ib_ven_god_king`, with the island represented as a feudal
God-King realm. From the Doom onward, rulers and provinces use `ib_ven_sound`,
while the realm uses oligarchic government to represent the Shadow Council. A
later-bookmark God-King configuration is deliberately not used: the God-Kings
ended with the Doom, whereas the Sound/Shadow Council branch describes post-Doom
Ibben.

## Generation and audit

The generator reads the effective Workshop and local rebase sources in playset
order, resolves title holders and character families, and emits all runtime
files and audit tables:

```sh
ck3mm mod generate agot_now_lov_ee_lore_governments
ck3mm mod generate agot_now_lov_ee_lore_governments --apply
```

The audit CSVs record every government assignment, Jogos Nhai culture
correction, Ibben character faith transition, and Ibben province faith
transition.

## Re-audit

Re-run the audit after updates to Workshop mods `2962333032`, `3664900993`,
`3403938445`, `3719888822`, `3682802751`, `3768149491`, or `3773608127`, or
after changing the LoV/EE rebases or the map compatch. After an intentional
upstream change, review the source diff and update the granular source-manifest
asset before regenerating.
