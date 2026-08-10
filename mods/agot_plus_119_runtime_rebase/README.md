# AGOT+ 1.0.0 - CK3 1.19 Runtime Rebase

Narrow executable-script repair for **AGOT+** (`2950245430`, version `1.0.0`) on
CK3 `1.19`.

Load this mod immediately after **AGOT: Canon Children EZ Mode**. The EZ-mode
mod does not override the repaired AGOT+ file, but loading after both parents
makes the intended winner unambiguous.

## Override

- `common/scripted_effects/asoiaf_canon_children_effects.txt`
- `common/scripted_effects/asoiaf_setup_effects.txt`
- `common/scripted_effects/asoiaf_scripted_effects_strong_seed.txt`
- `common/scripted_effects/zz_asoiaf_runtime_disabled_incomplete_children.txt`
- `common/scripted_triggers/zz_asoiaf_runtime_disabled_incomplete_children.txt`
- `common/modifiers/zz_asoiaf_runtime_missing_modifiers.txt`

## Canon-child creation

AGOT+ supplies 202 canon-child `create_character` effects with both:

```text
location = scope:mother.location
employer = scope:mother.employer
```

CK3 1.19 rejects specifying `location` and `employer` together, invalidating all
202 effects during post-validation. Current vanilla and AGOT newborn creation
use the mother's employer without a separate location. This rebase therefore
removes only the redundant `location` line and preserves employer, parentage,
appearance, traits, travel-plan handling, and all other behavior.

## Historical-character perks

AGOT+ also assigns perks to historical characters without first checking whether
they are alive at the selected bookmark. CK3 1.19 rejects `add_perk` on dead
characters; the 258 A.C. test emitted 422 such runtime errors.

This rebase gates each AGOT+ perk assignment with `is_alive = yes`. Living
characters receive exactly the same perks, while dead or not-yet-alive
characters skip an effect CK3 would reject.

## Redbeard strong seed

AGOT+ checked `dynasty:dynn_Redbeard`, but current AGOT defines Redbeard as
`house:house_Redbeard` under the Forester dynasty. The invalid dynasty lookup is
replaced with the corresponding house comparison.

## Current trigger and iterator syntax

The setup file now uses CK3 1.19's `has_claim_on` and `is_alive = no` triggers.
Six dynasty searches used effect iterators inside trigger limits; these now use
the corresponding `any_dynasty_member` trigger iterator.

The canon-child effects also use the current `target_character` field for 24
dragon-bond schemes, repair one mistyped `add_trait` effect and one invalid
spouse iterator. Alternative-age cleanup now checks the typed saved scope and
confirms it still refers to the current character, preventing a saved scope from
an earlier character from leaking into a later cleanup check.

The setup rebase also repairs four removed or misspelled trait identifiers. Nine
standalone `exists` triggers were being executed as effects; the affected
historical-character changes now use optional scopes or explicit `if` guards, so
missing bookmark characters safely skip only the dependent effect.

Eighty obsolete canon-child appearance references now resolve to the current
AGOT historical-character IDs. Two stillborn children whose dedicated appearance
templates do not exist fall back to normal parental inheritance. The
runtime-created Aerion check uses AGOT+'s stored global character variable, and
two renamed historical characters (Artys Dormand and Morrec Broome's spouse) now
resolve to their current AGOT IDs.

The remaining stale setup identifiers are rebased to their current forms: a
saved house is read through `scope:`, the hunter XP uses AGOT's `hunter` track,
the stewardship focus typo is corrected, and the `bossy` childhood trait is
applied as a trait rather than as an education focus. The two explicit
compatibility blocks for the disabled More Bookmarks mod are removed because
they query its absent `rhllor` faith; current AGOT's corresponding faith is
already `rhllor_fots`.

AGOT+ localizes and applies a separate Asha variant of its Greyjoy canon-child
modifier but omits the modifier definition. The additive modifier file defines
that variant with the same gameplay values as AGOT+'s Yara variant while
preserving the separate Asha localization.

Two Aegon IV event branches reference seven child birth effects that AGOT+ does
not define, and four of their triggers are missing as well. The generated late
definitions force only those incomplete triggers false and provide compile-safe
no-op effects. This prevents the branches from terminating a pregnancy before
calling a nonexistent birth effect while leaving every complete canon-child
branch enabled.

Refresh this generated override with:

```sh
ck3mm mod generate agot_plus_119_runtime_rebase
ck3mm mod generate agot_plus_119_runtime_rebase --apply
```

The per-mod manifest selects AGOT+ and this rebase's destination-specific staged
generator.

Recompare this override after every update to Workshop mod `2950245430`.
