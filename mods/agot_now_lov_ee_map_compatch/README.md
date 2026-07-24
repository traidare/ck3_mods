# AGOT NOW + Legacy of Valyria + Essos Expanded Map Compatch

Load after AGOT, AGOT Nobility of Westeros (NOW), Legacy of Valyria (LoV), the
AGOT 0.4.39 LoV temporary compatch, Essos Expanded, and its LoV compatch.

This is a semantic merge rather than a last-writer copy:

- keeps Essos Expanded's province table and applies the eleven province rows
  changed by NOW 1.2.4;
- preserves NOW's exact 3,470-pixel AGOT heightmap delta composited onto the
  Essos Expanded source under
  `content_source/heightmap/heightmap_now_delta_unpacked.png`;
- keeps LoV/Essos map objects outside NOW's Westeros edit rectangle and NOW
  objects inside it, merging locator records by numeric id;
- accepts the noncanonical indentation used by several EE/LoV locator records
  and verifies that no locator id is skipped or duplicated during generation;
- composites the two generator masks changed by NOW;
- merges NOW's title-data changes into the LoV/Essos government dispatcher.

`scripts/generate-agot-now-lov-ee-map-compatch.py` regenerates the text and
source-image merge from the installed Workshop inputs.

At runtime this layer deliberately leaves the coherent Essos Expanded 1.0
`heightmap.png` and packed heightmap set in control, so the small NOW elevation
delta remains inactive. The optional activation procedure is documented only in
`docs/agot-heightmap-repack.md`.
