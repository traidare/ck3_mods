# Legacy Of The Dragon - Linux Texture Fix

Case-sensitive filesystem repair for **Legacy Of The Dragon**.

## Requirements and load order

Load immediately after **Legacy Of The Dragon**.

## What it repairs

Legacy Of The Dragon references one Valyrian nobility colour-palette texture in
lowercase but ships the file with an uppercase extension. Windows resolves that
mismatch; Linux and other case-sensitive filesystems do not, so the texture
fails to load. This mod supplies a byte-for-byte copy of the same asset at the
lowercase path the parent actually asks for.

Windows players do not need it. It becomes unnecessary once Legacy Of The Dragon
ships the lowercase filename itself.
