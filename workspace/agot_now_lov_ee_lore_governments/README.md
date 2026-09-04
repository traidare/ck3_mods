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
history. The generator reconstructs the effective LoV/EE source layer in playset
order, then makes only the audited government, culture, faith, legitimacy, and
flavor-effect changes.

Further East ships the last `common/landed_titles/01_landed_titles.txt` in the
playset, so it defines the whole eastern title tree and the generator reads the
effective title set straight from it. Every effective title history resolves
against that tree, so no title filtering is needed.

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
- the Red Priesthood is theocratic. Norvos, Lorath, and Qohor have no rules
  here: AGOT owns those cities natively, and Further East ships their history
  files empty. Its `vassal_titles_e_qohor.txt` does hold a Qohorik-culture rump
  kingdom (`k_R43G49B154`, no empire parent), so a file-scoped rule keeps those
  54 holders on the Free City's administrative form rather than letting them
  fall to the engine default.
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

The Jogos Nhai work splits in two. The scripted-effect side is handled upstream:
the Workshop bridge names `culture:jogos_nhai` in its own flavor branch, so the
generator only asserts that state instead of rewriting it. The character side is
not handled upstream: 277 Jogos rulers and relatives are authored as `nefer`,
and this module corrects them.

## Known upstream defects carried forward

Validation reports 79 errors. Every one of them is inherited verbatim from an
upstream file this module re-emits, not introduced here; the emitted holder,
liege, and succession lines are byte-identical to their sources.

- 16 `duplicate-character`. Further East renamed the Leng rulers into named
  Tengvar empresses in a new `zz_eetlv_leng_empresses.txt` instead of overriding
  the generated `bookmark_chars.txt`, so both definitions load and each id
  becomes two characters. Folding the file in the way this module folds the
  khal-name and bookmark overrides does not work: the renamed rulers are female,
  while Further East's own generated genealogy still references them through
  `father`, which trades 16 duplicates for 20 gender errors. Repairing it needs
  Further East's parentage reconciled, which is out of this module's scope.
- 60 `history` no-holder and 1 `missing-item`. Dated `liege` entries in the LoV
  bridge's `lv_*` files point at titles with no holder at that date.
- 2 `wrong-gender`. Further East's `gen_2495` (Lengoreth) is used as a `mother`
  but carries no `female = yes`.

## Re-audit

Re-run the audit after updates to Workshop mods `2962333032`, `3664900993`,
`3403938445`, `3719888822`, `3682802751`, `3768149491`, or `3773608127`, or
after changing the LoV/EE rebases. After an intentional upstream change, review
the source diff before regenerating. The exact files consumed by the generator
and their hashes are recorded in `sources.lock.json`.
