# Legacy Of The Dragon - Linux Texture Fix

Case-sensitive filesystem repair for **Legacy Of The Dragon** (`3101422928`).

Load this mod immediately after **Legacy Of The Dragon**.

The parent mod references:

`gfx/portraits/accessory_variations/textures/color_palette_valyrian_generic_nobility_high_metal01.dds`

but ships that asset as uppercase `.DDS`. Windows resolves that mismatch; Linux
does not. This mod supplies an exact byte-for-byte copy at the lowercase path
expected by the two references in the parent's `valyrian.txt`.

Source asset SHA-256:

`7b638f8a363c6a2decb1cf01ecf816a252eb44cdfad3075e0ee279bd9e1e9915`

Remove this fix if the Workshop parent starts shipping the lowercase filename.
