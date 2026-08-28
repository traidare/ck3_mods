# essos_expanded_further_east_rebase — module state

Narrow history repair for **Essos Expanded: The Further East** (`3768149491`),
the expansion pack that supersedes Essos Expanded's own map and history. Load
position: immediately after Further East and before the Further East TempLoV/NOW
compatch.

## Ownership

- `history/titles/hist_titles.txt`
- `history/provinces/k_generated.txt`

Both are whole-file overrides of Further East's paths, generated from its
current release so an upstream history change is carried forward rather than
frozen at the version this module was written against.

## Repairs and evidence

### Invalid dated capitals

The parent repeats `capital = ...` inside 46 dated title-history blocks. CK3
1.19 rejects `capital` in that context and emits 46 persistent-reader errors.
The same empire, kingdom, and duchy capitals are already declared in Further
East's landed titles, so this rebase removes only those invalid history tokens
and preserves every holder and government transition; the date blocks are
otherwise byte-for-byte intact.

### Generated lay-clergy temples

Further East generates 1,180 `church_holding` provinces. Of these, 410 secondary
baronies use one of three AGOT faiths that combine lay clergy with fixed
spiritual appointment:

- `song_nefer`: 375;
- `dothraki_faith`: 21; and
- `sarnori_faith`: 14.

AGOT's theocracy government rejects lay-clergy characters, while its secular
governments do not accept a church as their primary holding. CK3 therefore
generated invalid rulers for precisely these 410 baronies and repeatedly
reported `unhandled succession order [invalid]`.

The province override converts only those 410 secondary holdings from
`church_holding` to `city_holding`. Cities retain the intended separately held,
tax-producing secondary-barony role without changing faith doctrine or creating
extra feudal domains. No county capital or other province field changes.

## Generation

```sh
ck3mm mod generate essos_expanded_further_east_rebase
ck3mm mod generate essos_expanded_further_east_rebase --apply
```

Each repair asserts its own count — 46 dated capitals, 1,180 church holdings,
410 conversions — so a Further East history change fails generation instead of
silently repairing more or fewer provinces than intended.

## Re-audit

Re-audit whenever Workshop `3768149491` updates. The counted assertions surface
the common cases; a structural change to how it generates temple provinces needs
the faith set re-derived by hand.
