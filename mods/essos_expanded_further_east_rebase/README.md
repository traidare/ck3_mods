# Essos Expanded: The Further East - CK3 1.19 History Rebase

Narrow history repair for **Essos Expanded: The Further East**.

## Requirements and load order

Load immediately after **Essos Expanded: The Further East** and before **Essos
Expanded - TempLoV/NOW Compatch**.

## What it repairs

**Invalid dated capitals.** Further East repeats a capital declaration inside 46
dated title-history blocks. CK3 1.19 rejects that and reports 46 errors. The
same empire, kingdom, and duchy capitals are already declared in Further East's
landed titles, so only the invalid history tokens are removed; every holder and
government transition is preserved.

**Generated lay-clergy temples.** Further East generates 1,180 temple provinces.
410 secondary baronies among them use one of three AGOT faiths that combine lay
clergy with fixed spiritual appointment. AGOT's theocracy government rejects
lay-clergy characters, while its secular governments will not take a temple as
their primary holding, so CK3 generated invalid rulers for exactly those 410
baronies and repeatedly reported invalid succession.

Those 410 secondary holdings are converted from temples to cities. They keep the
intended separately held, tax-producing secondary-barony role without changing
faith doctrine or creating extra feudal domains. No county capital or other
province field changes.
