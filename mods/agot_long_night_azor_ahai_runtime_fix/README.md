# AGOT: The Long Night & Azor Ahai - CK3 1.19 Runtime Fix

Two narrow script fixes for AGOT: The Long Night & Azor Ahai.

## Requirements and load order

Requires **A Game of Thrones** and **AGOT: The Long Night & Azor Ahai**. Load
this fix immediately after the Long Night mod and before its DFP compatch.

Disable this fix whenever AGOT: The Long Night & Azor Ahai is disabled.

## What it fixes

**Ruler designer.** The Long Night mod groups special portrait genes in a form
CK3's static validator identifies as a ruler-designer crash. This fix preserves
the genes and their appearance curves while removing only the invalid grouping
and inheritance fields.

**Who may serve.** The rule that stops the dead from serving the living, and the
living from serving the dead, is written in a conditional form CK3 1.19 rejects
outright. The rule therefore fails for everyone, so no character can be taken as
a captain, commander, councillor, or court position holder. This fix completes
the condition so the restriction applies only to the pairings it is meant to
block.

Ruler presets saved against older Long Night gene layouts are not guaranteed to
load without missing-gene messages.
