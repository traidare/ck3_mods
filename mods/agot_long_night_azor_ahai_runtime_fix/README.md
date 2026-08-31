# AGOT: The Long Night & Azor Ahai - CK3 1.19 Runtime Fix

A narrow ruler-designer safety fix for AGOT: The Long Night & Azor Ahai.

## Requirements and load order

Requires **A Game of Thrones** and **AGOT: The Long Night & Azor Ahai**. Load
this fix immediately after the Long Night mod and before its DFP compatch.

Disable this fix whenever AGOT: The Long Night & Azor Ahai is disabled.

## What it fixes

The Long Night mod groups special portrait genes in a form CK3's static
validator identifies as a ruler-designer crash. This fix preserves the genes and
their appearance curves while removing only the invalid grouping and inheritance
fields.

Ruler presets saved against older Long Night gene layouts are not guaranteed to
load without missing-gene messages.
