# AGOT+ 1.0.0 - CK3 1.19 Runtime Rebase

Narrow executable-script repair for **AGOT+** (`2950245430`, version `1.0.0`) on
CK3 `1.19`.

Load this mod immediately after **AGOT: Canon Children EZ Mode**. The EZ-mode
mod does not override the repaired AGOT+ file, but loading after both parents
makes the intended winner unambiguous.

## Override

- `common/scripted_effects/asoiaf_canon_children_effects.txt`
- `common/scripted_effects/asoiaf_setup_effects.txt`

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

Recompare this override after every update to Workshop mod `2950245430`.
