# AGOT + Build-a-Courtier Compatch

Makes Build-a-Courtier's lobby buttons work alongside A Game of Thrones.

## Requirements and load order

Requires **A Game of Thrones** and **Build-a-Courtier**. Load it after both.

## What it fixes

Build-a-Courtier replaces the whole lobby button file, which on its own removes
two AGOT features:

- **The pirate ruler-designer button disappears.**
- **The landless-adventurer designer stops being gated.** AGOT blocks it for
  ruins, wilderness, and unknown-government characters; without this it opens
  for them again.

Both are restored, and Build-a-Courtier's "Create your own Courtier" button
keeps working.

It also closes a crossover between the two: AGOT's pirate button opens the same
designer Build-a-Courtier uses, so pressing "Create your own Courtier",
cancelling, then designing a pirate the same day turned the pirate into your
courtier and destroyed their camp.

Both courtier buttons asked for an icon that does not exist in the game, so none
ever drew. They now use the standard add-character icon.

## Note

Creating a courtier needs **Roads to Power**. Without it the button is shown but
disabled, and its tooltip explains why.
