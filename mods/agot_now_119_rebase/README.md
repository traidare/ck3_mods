# AGOT NOW - CK3 1.19 Rebase

Narrow script repair for **AGOT Nobility of Westeros** on current A Game of
Thrones and CK3 1.19.

## Requirements and load order

1. A Game of Thrones
2. AGOT Nobility of Westeros
3. This rebase

Load immediately after Nobility of Westeros and before any map compatch that
merges it with Legacy of Valyria or Essos Expanded.

## What it repairs

The rebase preserves Nobility of Westeros' logic while fixing three errors that
CK3 1.19 rejects:

- Great Fork's title-change events used a scope that does not exist, so they
  failed instead of firing.
- The Summerhall events read an unset saved scope while searching for a second
  or third eligible family member; those comparisons are now optional, so the
  search completes.
- Nobility of Westeros' personal coat-of-arms event file was missing its
  namespace declaration, which made CK3 reject the event entirely and left its
  three calling decisions pointing at a missing event.
