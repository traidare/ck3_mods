# Essos Expanded + LoV - CK3 1.19 History Rebase

Narrow history repair for **Essos Expanded** (`3682802751`, version `1.0`) in
the Legacy of Valyria playset. Essos Expanded still declares support for CK3
`1.18.4`, and this history uses LoV's government database.

Load immediately after **Essos Expanded** and before **Essos Expanded - TempLoV
Compatch**.

## Override

- `history/titles/hist_titles.txt`

The parent repeats `capital = ...` inside 54 dated title-history blocks. CK3
1.19 rejects `capital` in that context and emitted 54 persistent-reader errors
in both the core and full test runs. The same empire, kingdom, and duchy
capitals are already declared in Essos Expanded's
`common/landed_titles/01_landed_titles.txt`, so this rebase removes only those
invalid history tokens and preserves every holder and government transition.

Recompare this file after every update to Workshop mod `3682802751`.
