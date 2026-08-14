# Essos Expanded + LoV - CK3 1.19 History Rebase

Narrow history repair for **Essos Expanded** (`3682802751`, version `1.0`) in
the Legacy of Valyria playset. Essos Expanded still declares support for CK3
`1.18.4`, and this history uses LoV's government database.

Load immediately after **Essos Expanded** and before **Essos Expanded - TempLoV
Compatch**.

## Override

- `history/titles/hist_titles.txt`
- `history/provinces/k_generated.txt`

### Invalid dated capitals

The parent repeats `capital = ...` inside 54 dated title-history blocks. CK3
1.19 rejects `capital` in that context and emits 54 persistent-reader errors.
The same empire, kingdom, and duchy capitals are already declared in Essos
Expanded's `common/landed_titles/01_landed_titles.txt`, so this rebase removes
only those invalid history tokens and preserves every holder and government
transition.

### Generated lay-clergy temples

Essos Expanded generates 1,180 `church_holding` provinces. Of these, 410
secondary baronies use one of three AGOT faiths that combine lay clergy with
fixed spiritual appointment:

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

Recompare both overrides after every update to Workshop mod `3682802751`.
