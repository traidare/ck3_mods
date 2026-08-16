# legacy_of_the_dragon_linux_fix — module state

Case-sensitive filesystem repair for **Legacy Of The Dragon** (`3101422928`).
Load position: immediately after Legacy Of The Dragon.

## Ownership

One asset only:

`gfx/portraits/accessory_variations/textures/color_palette_valyrian_generic_nobility_high_metal01.dds`

The parent references that lowercase path from two places in its `valyrian.txt`
but ships the asset as uppercase `.DDS`. Windows resolves the mismatch; Linux
does not. This module supplies an exact byte-for-byte copy at the lowercase
path.

Source asset SHA-256:

`7b638f8a363c6a2decb1cf01ecf816a252eb44cdfad3075e0ee279bd9e1e9915`

## Generation

None. This module has no `mod.toml` and no generator; the copied asset is
vendored. `ck3-tiger.conf` declares the dependency load order for static
validation only.

## Re-audit

Manual. Verify the source asset hash after every update to Workshop mod
`3101422928`. **Delete this module** if the parent starts shipping the lowercase
filename, or if it stops referencing that path.
