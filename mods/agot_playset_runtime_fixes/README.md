# AGOT Playset Runtime Fixes

Narrow repairs for script errors that a large AGOT playset produces on CK3 1.19.
Each fix targets one diagnosed failure in one parent mod and changes nothing
else.

## Requirements and load order

Load after every mod it repairs and before the final **AGOT Playset Compatch**.

## What it repairs

Roughly fifty parent mods are touched. The failures fall into a few classes:

- **Effects CK3 1.19 no longer accepts** — removed or renamed triggers,
  iterators used in the wrong position, obsolete event fields, negative gold
  costs, and malformed tooltips, all of which stop the affected event or
  decision from running at all.
- **Unset or missing scopes** — code that reads a character's father, capital,
  location, war, house, dynasty, previous title holder, or activity host without
  checking that it exists. These are guarded so the dependent effect is skipped
  instead of erroring, repeatedly, from game start onward.
- **References to content AGOT removes** — vanilla traits, faiths, cultures,
  regions, titles, artifact modifiers, and decisions that a vanilla-targeted mod
  still queries. These are made explicitly inert or remapped to AGOT's current
  equivalents.
- **Stale whole-file copies** — mods shipping pre-AGOT or pre-1.19 versions of
  files they also override, which silently revert AGOT's own content. These are
  rebased so the mod's intended change survives without the reversion.
- **Broken succession and war joins** — participants added to a war they are
  already in, and pirate titles left without a valid succession law, both of
  which loop on every evaluation.
- **Portrait and interface breakage** — obsolete DNA and gene entries, missing
  illustrations, a crash-prone pre-1.19 GUI widget, and an event that opened as
  an empty blocking popup.

Gameplay intent from every repaired mod is preserved; only the code CK3 rejects
is changed.
