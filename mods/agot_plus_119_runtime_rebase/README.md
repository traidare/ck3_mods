# AGOT+ 1.0.0 - CK3 1.19 Runtime Rebase

Narrow script repair for **AGOT+** on CK3 1.19.

## Requirements and load order

Load immediately after **AGOT: Canon Children EZ Mode**. That mod does not
override the repaired AGOT+ files, but loading after both parents makes the
intended winner unambiguous.

## What it repairs

- **All 202 canon-child creations.** AGOT+ specifies both a location and an
  employer, which CK3 1.19 rejects, so every canon child failed to be created.
  The redundant location is removed; employer, parentage, appearance, traits,
  and travel-plan handling are unchanged.
- **Historical-character perks.** AGOT+ assigned perks without checking whether
  the character is alive at the selected bookmark, which CK3 1.19 rejects. Perk
  assignments are now gated on the character being alive; living characters get
  exactly the same perks.
- **Redbeard strong seed.** AGOT+ looked up a Redbeard dynasty; current AGOT
  defines Redbeard as a house under the Forester dynasty. The lookup is
  corrected.
- **Outdated trigger and iterator syntax** throughout the setup and canon-child
  files, including 24 dragon-bond schemes, one mistyped trait effect, one
  invalid spouse iterator, four removed or misspelled traits, and nine triggers
  that were being run as effects — so a missing bookmark character now skips
  only the dependent effect instead of erroring.
- **Eighty obsolete canon-child appearance references**, now resolved to current
  AGOT historical characters. Two stillborn children without appearance
  templates fall back to normal parental inheritance, and two renamed historical
  characters resolve to their current AGOT identities.
- **Remaining stale setup values**: the hunter XP track, a stewardship focus
  typo, and the `bossy` childhood trait applied as a trait rather than an
  education focus. Two compatibility blocks for the disabled More Bookmarks mod
  are removed, since current AGOT already supplies the faith they queried.
- **A missing modifier.** AGOT+ applies and localizes a separate Asha variant of
  its Greyjoy canon-child modifier but never defines it. It is defined here with
  the same values as the Yara variant, keeping the separate Asha text.
- **Two incomplete Aegon IV event branches** that reference seven child-birth
  effects AGOT+ does not define. Those branches are disabled so they can no
  longer terminate a pregnancy and then call a nonexistent effect. Every
  complete canon-child branch stays enabled.
