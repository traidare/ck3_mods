# AGOT: Whispers of Magic

An additive, balance-focused AGOT submod for skinchanging, animal bonds,
greensight mastery, and dragon dreams.

## Requirements and load order

1. A Game of Thrones
2. AGOT: Whispers of Magic

## Design boundaries

- AGOT continues to own `greensight`, `dragon_dreams`, magic level, dragonblood,
  and the Dragonriding House modifier.
- The fork adds the tracked `agot_wom_skinchanger` trait and a hidden
  `agot_wom_greensight_mastery` track.
- Supported animal bonds are dog, wolf, raven, eagle, bear, shadowcat, cat, and
  deer. Rats are intentionally excluded.
- There is no Three-Eyed Crow state, event chain, immortality, human warging,
  dragon warging, death prevention, or second-life mechanic.
- A character can hold at most two animal bonds. The first remains primary.
- Dragon-dream inheritance uses AGOT's `dragonblood_percent` script value and
  `dragonrider_house_modifier`; no parallel bloodline system is introduced.

## Balance summary

The natural skinchanger roll begins at 0.5%, is restricted to lore-compatible
heritage/faith/ancestry, and is capped at 8%. The gift is revealed between ages
6 and 15 only while AGOT magic is active. Bonding is a delayed encounter and
trial, not an instant trait grant. Active warging lasts 30 days, permits one
deed, and imposes a two-year rest.

Animal influence is a staged cost. Repeated or forceful entry may alter the
skinchanger's modifiers and, at most once per character, replace one
lore-compatible personality trait.

Dragon-dream inheritance is an additive native roll: 0.25% plus 0.025 percentage
points per point of AGOT `dragonblood_percent`, with another 2 points for
members of a Dragonriding House, capped at 6%. Thus 50% dragonblood adds a 1.5%
roll, while a 100% Dragonriding House member adds a 4.75% roll. The roll grants
AGOT's latent flag; the first actual dragon dream reveals AGOT's visible
`dragon_dreams` trait.

## Validation

Run:

```sh
ck3mm mod validate agot_whispers_of_magic
ck3mm conflicts AGOT \
  --all-files \
  --involving mod/agot_whispers_of_magic.mod
```
