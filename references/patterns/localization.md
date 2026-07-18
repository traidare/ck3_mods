# Adding Localization — Practical Recipe

## What You Need to Know First

Localization is the text shown to the player. CK3 uses `.yml` files with strict
encoding and naming requirements. Getting encoding wrong is the #1 cause of
localization issues.

> Reference docs: references/wiki/wiki_pages/Localization.md

## Minimal Template

### localization/english/my_mod_l_english.yml

```
l_english:
 my_event.0001.t: "Event Title"
 my_event.0001.desc: "Something happened to [ROOT.Char.GetFirstName]."
 my_event.0001.a: "Acknowledge"
 my_event.0001.b: "Refuse"
```

**Critical requirements:**

1. File MUST be encoded as **UTF-8 with BOM**
2. File name MUST contain `_l_english` (or appropriate language)
3. First line MUST be `l_english:` (note the colon)
4. Each key has a space before it (speeds up loading)
5. File goes in `localization/english/` subfolder

## Annotated Vanilla Example

<!-- TODO: Add a real vanilla localization example. Check:
$CK3_GAME_DIR/localization/english/ for a small file. -->

## Common Variants

### Dynamic text with character data

```
l_english:
 my_greeting: "[ROOT.Char.GetLadyLord] [ROOT.Char.GetFirstNameNicknamed], your realm prospers!"
 my_gender_text: "[ROOT.Char.GetSheHe] has decided to act."
```

Common data types (must be scoped to a character with `.Char`):

- `GetFirstName`, `GetName`, `GetFullName` — character names
- `GetSheHe`, `GetHerHim`, `GetHerHis` — gendered pronouns
- `GetLadyLord`, `GetDaughterSon` — gendered titles
- Use `|U` for uppercase first letter, `|L` for lowercase

### Text formatting

```
l_english:
 my_formatted: "#P This is green (positive)#! and #N this is red (negative)#!"
 my_bold: "You have #bold NOT#! done this."
 my_italic: "You #italic will#! do this."
 my_warning: "#warning This is dangerous!#!"
```

### Icons in text

```
l_english:
 my_cost: "Costs @gold_icon! 100 gold and @prestige_icon! 50 prestige."
```

### Game concept links

```
l_english:
 my_concept: "Increase your [faith|E] to gain benefits."
 my_concept_custom: "The [Concept('faith','religion')|E] matters here."
```

### Overriding vanilla localization

Place files in `localization/replace/english/` (or
`localization/english/replace/`):

```
l_english:
 existing_vanilla_key: "My replacement text"
```

### Multi-language support

Copy your English file, rename to match each language:

- `my_mod_l_french.yml` with `l_french:` on the first line
- `my_mod_l_german.yml` with `l_german:` on the first line

If not providing translations, copy the English file to prevent players in other
languages from seeing raw keys.

## Checklist

- [ ] File encoded as UTF-8 with BOM
- [ ] File in `localization/<language>/` folder
- [ ] Filename includes `_l_<language>` suffix
- [ ] First line is `l_<language>:`
- [ ] No duplicate keys across all localization files
- [ ] All event titles, descriptions, and option names have loc keys
- [ ] Test: if text shows raw key name, check encoding first

## Common Pitfalls

- **Wrong encoding**: The #1 issue. Must be UTF-8 BOM. Check your editor's
  encoding indicator
- **`l_english:` typo**: It's a lowercase L, not the number 1 or uppercase I
- **`localization` spelling**: Uses a Z, not an S (`localization`, not
  `localisation`)
- **Saved scopes in loc**: Do NOT use `scope:` prefix in localization. Write
  `[my_saved_scope.GetFirstName]`, not `[scope:my_saved_scope.GetFirstName]`
- **Missing .Char promote**: Use `[ROOT.Char.GetName]`, not `[ROOT.GetName]`.
  ROOT is a scope reference — you need `.Char` to access character data types
- **Line break issues**: `\n` works in loc files but not when text is set
  directly in UI code
- **Number after colon**: `key:0 "text"` — the number is optional and
  deprecated. You don't need it
- **Building loc keys**: Buildings use `building_type_<key>` for the name shown
  in the build menu, not `building_<key>`. Include both `building_type_<key>`
  and `building_<key>` to cover all tooltip contexts
- **Trait loc keys**: Traits use `trait_<key>`, not `building_type_` or just
  `<key>`
- **Decision loc keys**: Decisions use just `<key>`, plus `<key>_desc`,
  `<key>_tooltip`, `<key>_confirm`
