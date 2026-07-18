# AGOT: Banking & Iron Bank

> System author: **Ronko**. All code lives under the `agot_banking` namespace.

## Overview

AGOT implements a full banking economy with **up to 4 concurrent banks**: the
hardcoded **Iron Bank of Braavos** (prefix `IB_`) and up to **3 player-founded
custom banks** (prefixes `bank1_`, `bank2_`, `bank3_`). The system covers:

- **Loans** -- characters borrow gold from a bank, repay principal + interest
  over a term
- **Shares & dividends** -- characters invest in banks by buying shares, receive
  periodic payouts
- **Credit scoring** -- banks evaluate borrowers before granting loans
- **Default enforcement** -- banks pursue defaulters through raids,
  assassination, economic warfare, or political pressure
- **Vassal loans** -- a parallel loan system between lieges and their vassals
- **Bank founding, dissolution, and conquest** -- banks can be created, go
  bankrupt, or be destroyed when conquered

### Source Files

| File                                                              | Purpose                                                              |
| ----------------------------------------------------------------- | -------------------------------------------------------------------- |
| `common/scripted_effects/00_agot_banking_effects.txt`             | Core scripted effects (init, inheritance, credit score, dissolution) |
| `common/decisions/agot_decisions/00_agot_banking_decisions.txt`   | All banking decisions                                                |
| `common/character_interactions/00_agot_banking_interactions.txt`  | Vassal loan and share transfer interactions                          |
| `events/agot_events/agot_banking_events.txt`                      | All banking events (~14,000 lines)                                   |
| `common/story_cycles/agot_story_cycle_loan.txt`                   | Story cycle that fires loan-due events                               |
| `common/script_values/01_agot_dynamic_values.txt`                 | Loan amounts, cash reserves, thresholds                              |
| `common/modifiers/00_agot_iron_bank_modifiers.txt`                | County modifier for economic punishment                              |
| `common/customizable_localization/00_agot_banking_custom_loc.txt` | Dynamic bank name and interest level display                         |

---

## Key Concepts

### Bank Slots and Prefixes

Every bank stores its state in **global variables** using a consistent prefix
pattern. The Iron Bank uses `IB_`, and custom banks use `bank1_`, `bank2_`,
`bank3_`. A bank slot is "empty" when its `BankValue` global variable equals 0.

Per-bank global variables (replace `XX` with the prefix):

| Variable            | Type      | Meaning                                               |
| ------------------- | --------- | ----------------------------------------------------- |
| `XX_location`       | title     | The barony where the bank is located                  |
| `XX_founder`        | character | The character who founded the bank                    |
| `XX_BankValue`      | float     | Total bank value (capital + loaned + earnings)        |
| `XX_FreeCapital`    | float     | Available gold for new loans                          |
| `XX_LoanedCapital`  | float     | Gold currently out on loan                            |
| `XX_InvestmentFund` | float     | Gold allocated to the investment fund                 |
| `XX_NofShares`      | int       | Total number of shares issued                         |
| `XX_ValuePerShare`  | float     | Current value of one share                            |
| `XX_NofLoans`       | int       | Number of active loans                                |
| `XX_NofDefaults`    | int       | Number of defaulted loans                             |
| `XX_RiskLevel`      | int       | Investment risk (3 = low, 6 = medium, 18 = high)      |
| `XX_DividendLevel`  | float     | Fraction of earnings paid as dividends (default 0.75) |
| `XX_InterestLevel`  | int       | -1 = low, 0 = normal, +1 = high interest              |
| `XX_Earnings`       | float     | Cumulative interest earnings                          |
| `XX_LostLoans`      | float     | Cumulative losses from defaults                       |
| `XX_Expenses`       | float     | Cumulative operational expenses                       |

Global variable lists:

| List Variable          | Contents                                   |
| ---------------------- | ------------------------------------------ |
| `XX_Shareholder`       | All characters holding shares in this bank |
| `Shareholder`          | All characters holding shares in ANY bank  |
| `XX_Important_Debtors` | Debtors with loans >= 200 gold             |

### Per-Character State

Characters carry their banking state through **character variables** and
**character flags**.

**Debtor flags and variables:**

| Flag/Variable                              | Meaning                                           |
| ------------------------------------------ | ------------------------------------------------- |
| `has_a_loan_flag` (flag)                   | Character has an active bank loan                 |
| `IB_debtor` / `bank1_debtor` / etc. (flag) | Which bank the loan is from                       |
| `loan_requested` (flag)                    | Loan application in progress                      |
| `final_default` (flag)                     | Permanently blacklisted from all banks            |
| `defaulted_on_loan` (flag)                 | Has previously defaulted (hurts credit score)     |
| `loaned_amount` (var)                      | Principal of the current loan                     |
| `loan_term` (var)                          | Duration in years (3, 5, or 10)                   |
| `loan_interest_rate` (var)                 | Annual interest rate (percentage)                 |
| `total_repayment` (var)                    | Principal + total interest owed                   |
| `half_repayment` (var)                     | Half of total_repayment (minimum partial payment) |
| `payable_interest` (var)                   | Computed total interest amount                    |
| `credit_score` (var)                       | Computed risk score (lower is better)             |

**Shareholder flags and variables:**

| Flag/Variable                                  | Meaning                                       |
| ---------------------------------------------- | --------------------------------------------- |
| `IB_Shares` / `bank1_Shares` / etc. (var)      | Number of shares held                         |
| `IB_Director` / `bank1_Director` / etc. (flag) | This character is the bank's director         |
| `BankName` (var)                               | Reference to the bank's founder (for display) |
| `investments_forbidden` (flag)                 | Director has closed new investments           |

**Vassal loan state:**

| Flag/Variable                    | Meaning                            |
| -------------------------------- | ---------------------------------- |
| `has_a_vassal_loan` (flag)       | Debtor has a vassal loan           |
| `has_granted_liege_loan` (flag)  | Vassal has granted a loan to liege |
| `vassal_loan_amount` (var)       | Principal borrowed                 |
| `vassal_loan_total_amount` (var) | Principal x 1.25                   |
| `vassal_loan_interest` (var)     | The 25% interest portion           |
| `vassal_loan_creditor` (var)     | The vassal who lent the gold       |
| `vassal_loan_debtor` (var)       | The liege who borrowed             |

### Loan Amounts (Script Values)

Loan amounts scale with the borrower's income. Defined in
`common/script_values/01_agot_dynamic_values.txt`:

```pdx
low_loan_value = {
    value = monthly_character_income
    multiply = 12        # 1 year of income
    min = 50
    divide = 5
    ceiling = yes
    multiply = 5          # round up to nearest 5
}

high_loan_value = {
    value = monthly_character_income
    multiply = 30        # 2.5 years of income
    min = 75
    divide = 5
    ceiling = yes
    multiply = 5
}
```

### Cash Reserve Thresholds

Banks maintain a safety margin before lending or accepting investments:

```pdx
min_cash_reserve_IB = {
    value = global_var:IB_BankValue
    multiply = 0.15
    min = 300
    max = 5000
}

invest_threshold_IB = {
    value = global_var:IB_BankValue
    multiply = 0.25
    min = 2000
    max = 7500
}
```

Custom banks use identical formulas with their own prefix
(`min_cash_reserve_bank1`, etc.).

---

## AGOT Scripted API (Effects)

There are **no dedicated banking scripted triggers**. All banking conditions are
checked inline. The system provides these scripted effects:

### `agot_init_banking_system`

Called on game start. Initializes all global variables for every bank slot. The
Iron Bank is hardcoded to `title:b_purple_harbor` with 15,000 starting capital,
100 shares, and 150 gold per share. The Rogare Bank (`bank1`) starts at
`title:b_lys` with 1,500 capital and 10 shares (only in early bookmarks, before
year 8136).

Starting Iron Bank shares are distributed to Braavosi noble family title
holders:

- `title:d_nf_otherys` holder: 5 shares + IB_Director
- `title:d_nf_dothare`, `d_nf_grivas`, `d_nf_reyaan`, `d_nf_dimittis`,
  `d_nf_gresayn`, `d_nf_fregar` holders: 5 shares each

### `agot_credit_score_effect`

Computes a borrower's `credit_score` variable. Lower is better. Factors:

| Factor                                          | Effect on Score |
| ----------------------------------------------- | --------------- |
| Is a shareholder                                | -2 (discount)   |
| Stewardship < 5                                 | +2              |
| Stewardship < 10                                | +1              |
| Stewardship > 15                                | -1              |
| Stewardship > 20                                | -2              |
| Stewardship > 25                                | -3              |
| Previously defaulted (`defaulted_on_loan` flag) | +5              |
| Has `bank_punishment` flag                      | +2              |
| Title tier >= duchy                             | -1              |
| Age >= 50                                       | +1              |
| Age >= 60                                       | +1 (cumulative) |
| Age >= 70                                       | +1 (cumulative) |
| At war                                          | +2              |
| Imprisoned                                      | +3              |
| High loan value > 500                           | +1              |
| High loan value > 1000                          | +1              |
| Gold < 0                                        | +1              |

The loan type choice also adds to the score:

- Low amount, long term: +0
- Low amount, short term: +1
- High amount, long term: +2
- High amount, short term: +3

### `loan_inheritance`

Transfers a dead character's loan debt to their heir. Sets the heir's debtor
flags, copies loan variables, triggers `agot_banking.0007` (inform heir) or
`agot_banking.0006` (heir already has a loan -- stacks amounts).

### `share_inheritance`

Transfers shares to the heir on death. If the heir already holds shares in a
different bank, the shares are sold instead (paid out as gold). Handles director
succession -- if the dead character was director, triggers
`bank_director_election`.

### `bank_director_election`

When a bank's director dies, an election is held among shareholders. The
character with the most shares becomes the new director. Ties are broken by
stewardship. The new director is flagged (e.g., `IB_Director`) and informed via
`agot_banking.0205`.

### `vassal_loan_inheritance`

Handles inheritance of vassal loans when either the debtor or creditor dies.

### `historical_loan_on_game_start`

Sets up pre-existing loans for historical characters on game start (e.g., the
Iron Throne's debt to the Iron Bank).

### `dissolve_conquered_bank`

Called when a bank's location is conquered by a realm that already contains
another bank. Pays out remaining free capital to shareholders, resets all global
variables to zero, and removes the bank's location.

### `dissolve_bankrupt_bank`

Similar to conquest dissolution but triggered when a bank's value drops to zero
or below.

---

## Interactions & Decisions

### Character Interactions

#### `take_vassal_loan_interaction`

**Category:** `interaction_category_vassal`

Lets a feudal liege (duke+) request a loan from a vassal. The vassal must have
enough gold (>= `low_loan_value`). Interest is **fixed at 25%**. Cooldown: 3
years per recipient.

AI acceptance factors: base -25, opinion (+1 per point), loyal +25, disloyal
-25, trusting +25, paranoid -25, ambitious +50, rival -100, intimidated +25,
cowed +50, hook +50.

On accept: triggers `agot_banking.0501` (gold transfer and repayment timer).

On decline: triggers `agot_banking.0502` (opinion malus).

Key flags: `has_a_vassal_loan` (debtor), `has_granted_liege_loan` (creditor).

#### `gift_share_interaction`

**Category:** `interaction_category_friendly`

Lets a shareholder gift one share to another player character in the same realm.
Auto-accepts. The recipient gains +20 opinion, and is added to the bank's
shareholder list if not already a member. A character cannot hold shares in
multiple banks simultaneously.

#### `take_share_interaction`

**Category:** `interaction_category_friendly`

Lets a **house head** seize all shares from a house member. Auto-accepts, -20
opinion. The target must not be a bank director. Same single-bank restriction
applies.

### Decisions

All banking decisions use `decision_group_type = banking` (or `major` for some).

#### `take_loan_decision`

Opens the loan application flow. Requirements:

- Landed, capable, no existing loan, not blacklisted (`final_default`), not
  Beyond the Wall
- At least one bank has a director and free capital > `min_cash_reserve`

Triggers `agot_banking.1001` (bank selection event).

#### `agot_repay_loan_decision`

Repay a loan early. Requires gold >= `half_repayment` (or at least 50 gold if
half_repayment >= 50). Triggers `agot_banking.0005`.

#### `buy_shares_decision`

Buy shares in a bank. Requirements:

- Adult, noble, not tribal, has `innovation_currency_03`
- Must be in the same realm as the bank (via de jure hierarchy check)
- Cannot hold shares in multiple banks
- Bank's `FreeCapital` < `invest_threshold` (bank needs capital)

Triggers `agot_banking.0203`.

#### `sell_shares_decision`

Sell shares back to the bank. The bank needs `FreeCapital > min_cash_reserve` to
buy back. Directors cannot sell their last share. Triggers `agot_banking.0204`.

#### `found_bank_decision`

Found a new bank. Requirements:

- Stewardship >= 15, `innovation_currency_03`, not at war
- No existing shares in any bank
- A free bank slot (`bank1/2/3_BankValue = 0`)
- No other bank already in your realm
- Cost: **1000 gold**

Triggers `agot_banking.0601`. The AI reserves at least 2 empty slots so the
player always has one.

#### `rename_bank_decision`

Rename a bank you direct. Only available to directors of custom banks. Triggers
`agot_banking.0607`.

#### `show_bank_numbers_decision`

View financial details of your bank (shareholder-only, player-only). Triggers
`agot_banking.0301`.

#### `show_shareholders_decision` / `show_debtors_decision`

View lists of shareholders or debtors. Player-only. Trigger `agot_banking.0603`
/ `agot_banking.0604`.

#### `fill_investment_fund_decision`

Director-only. Allocate bank capital to the investment fund when
`FreeCapital > invest_threshold` and > 2000. Cooldown: 729 days (~2 years).
Triggers `agot_banking.0401`.

#### AI-Only Director Decisions

These are only available to AI directors and auto-fire with `ai_will_do = 100`:

| Decision                      | Event               | Purpose                      |
| ----------------------------- | ------------------- | ---------------------------- |
| `set_risk_level_decision`     | `agot_banking.0206` | Set investment risk (3/6/18) |
| `set_dividend_level_decision` | `agot_banking.0207` | Set dividend payout ratio    |
| `set_interest_level_decision` | `agot_banking.0208` | Set interest level (-1/0/+1) |

#### `repay_vassal_loan_decision`

Repay a vassal loan in full. Requires gold >= `vassal_loan_total_amount`.
Directly transfers gold and cleans up all flags/variables.

---

## Events & Story Cycles

### Event Namespace: `agot_banking`

The events file contains approximately **80 events** covering the full loan
lifecycle.

### Loan Application Flow

```
take_loan_decision
    --> agot_banking.1001  (select bank: IB, bank1, bank2, or bank3)
        --> agot_banking.0001  (choose loan type: low/high x short/long)
            --> agot_credit_score_effect  (compute credit score)
            --> agot_banking.0002  (refused -- score too high)
            OR
            --> agot_banking.0003  (offer presented -- accept or refuse)
                --> accept: gold paid out, story_agot_loan created
```

### Loan Types

The borrower picks from 4 combinations:

| Flag                   | Amount            | Term  | Credit Score Add |
| ---------------------- | ----------------- | ----- | ---------------- |
| `agot_loan_low_long`   | `low_loan_value`  | long  | +0               |
| `agot_loan_low_short`  | `low_loan_value`  | short | +1               |
| `agot_loan_high_long`  | `high_loan_value` | long  | +2               |
| `agot_loan_high_short` | `high_loan_value` | short | +3               |

Interest rate and exact term (3, 5, or 10 years) are computed from the credit
score in `agot_banking.0001` and the bank's `InterestLevel`.

### Story Cycle: `story_agot_loan`

Defined in `common/story_cycles/agot_story_cycle_loan.txt`. Tracks the loan term
and fires `agot_banking.0004` (loan becomes due) after the specified number of
years:

```pdx
story_agot_loan = {
    on_setup = {
        set_variable = {
            name = story_loan_term
            value = story_owner.var:loan_term
        }
    }
    on_owner_death = {
        scope:story = { end_story = yes }
    }
    effect_group = {
        years = 3
        trigger = { var:story_loan_term = 3 }
        triggered_effect = {
            effect = {
                story_owner = {
                    trigger_event = { id = agot_banking.0004 }
                }
            }
        }
    }
    # Repeated for years = 5 and years = 10
}
```

Note: CK3 story cycle `years` does not accept variables, so three separate
`effect_group` blocks handle the three possible terms.

### Loan Due & Repayment (agot_banking.0004)

When the loan comes due, the debtor gets options:

- **Repay in full** (if gold >= `total_repayment`): principal + interest
  returned to bank, loan cleared
- **Repay half** (if gold >= `half_repayment`): partial payment, remaining debt
  persists
- **Default**: triggers the default enforcement chain

On repayment, the bank's financials update:

- `FreeCapital` += repayment amount
- `LoanedCapital` -= principal
- `BankValue` += interest earned
- `Earnings` += interest earned

### Early Repayment (agot_banking.0005)

Triggered by `agot_repay_loan_decision`. Allows paying before the due date with
similar options to the due-date event.

### Default Enforcement Chain

When a debtor defaults, the bank director (or a delegated shareholder) handles
it through `agot_banking.0210` and `agot_banking.0211`:

| Action            | Event (fail/success) | Cost     | Effect                                                        |
| ----------------- | -------------------- | -------- | ------------------------------------------------------------- |
| Send raiders      | 0101 / 0102          | 25+ gold | Raid defaulter's lands                                        |
| Hire assassin     | 0103 / 0104          | 75+ gold | Attempt to kill the defaulter                                 |
| Sell claim        | 0105 / 0106 / 0116   | 40+ gold | Fabricate/sell a claim on defaulter's land                    |
| Write to liege    | 0107 / 0108 / 0109   | 10+ gold | Ask the defaulter's liege to intervene                        |
| Economic collapse | 0113 / 0114          | 50+ gold | Apply `economically_undermined_modifier` to defaulter's lands |

Costs scale with the defaulter's title tier. If all actions fail, the bank
writes off the loan.

### The `economically_undermined_modifier`

Defined in `common/modifiers/00_agot_iron_bank_modifiers.txt`:

```pdx
economically_undermined_modifier = {
    icon = county_modifier_development_negative
    development_growth_factor = -0.5
    monthly_county_control_decline_add = -0.5
    tax_mult = -0.75
}
```

### Five-Year Bookkeeping (agot_banking.0201)

Every 5 years, each bank runs a bookkeeping cycle:

- Calculates earnings from interest and investment fund returns
- Deducts lost loans and expenses
- Updates `BankValue` and `ValuePerShare`
- Pays dividends to shareholders based on `DividendLevel`
- Informs shareholders via `agot_banking.0202`

### Investment Fund (agot_banking.0401 / 0402 / 0403)

Directors can allocate bank capital to an investment fund. Returns depend on
`RiskLevel`:

- Low risk (3): smaller but safer returns
- Medium risk (6): balanced
- High risk (18): high potential returns but higher chance of losses

Results are calculated yearly in `agot_banking.0402` and reported to the
director in `agot_banking.0403`.

### Vassal Loan Events

| Event               | Purpose                                                 |
| ------------------- | ------------------------------------------------------- |
| `agot_banking.0501` | Inform liege about accepted loan, transfer gold         |
| `agot_banking.0502` | Inform liege about declined loan                        |
| `agot_banking.0503` | Vassal loan repayment becomes due (fired after 5 years) |
| `agot_banking.0504` | Inform vassal about liege's reaction to due repayment   |

### Bank Founding & Dissolution

| Event               | Purpose                                    |
| ------------------- | ------------------------------------------ |
| `agot_banking.0601` | A new bank was founded                     |
| `agot_banking.0607` | Rename bank                                |
| `agot_banking.0603` | Show shareholders list                     |
| `agot_banking.0604` | Show debtors list                          |
| `agot_banking.0700` | Inform shareholders about bank dissolution |
| `agot_banking.0701` | Bank director decides about raiding threat |
| `agot_banking.0801` | Bank bankruptcy check                      |
| `agot_banking.0803` | Bank dissolved                             |
| `agot_banking.0804` | Bank saved from bankruptcy                 |

### Director Election

| Event               | Purpose                                                |
| ------------------- | ------------------------------------------------------ |
| `agot_banking.0205` | Inform new director                                    |
| `agot_banking.0215` | Inform shareholders about dead director, ask for votes |
| `agot_banking.0225` | Process election results                               |

---

## Sub-Mod Recipes

### Recipe 1: Grant a Loan via Script (Bypass the UI)

To give a character a loan from the Iron Bank programmatically:

```pdx
# In an event or scripted effect, with ROOT = the borrower
root = {
    set_variable = { name = loaned_amount  value = 500 }
    set_variable = { name = loan_term  value = 5 }
    set_variable = { name = loan_interest_rate  value = 10 }

    # Compute derived values
    set_variable = { name = payable_interest  value = var:loan_interest_rate }
    change_variable = { name = payable_interest  divide = 100 }
    change_variable = {
        name = payable_interest
        multiply = { value = var:loan_term  multiply = var:loaned_amount }
    }
    set_variable = { name = total_repayment  value = var:loaned_amount }
    change_variable = { name = total_repayment  add = var:payable_interest }
    set_variable = { name = half_repayment  value = var:total_repayment }
    change_variable = { name = half_repayment  divide = 2 }

    add_character_flag = has_a_loan_flag
    add_character_flag = IB_debtor
    add_gold = var:loaned_amount

    # Update bank state
    change_global_variable = { name = IB_NofLoans  add = 1 }
    change_global_variable = { name = IB_FreeCapital  subtract = var:loaned_amount }
    change_global_variable = { name = IB_LoanedCapital  add = var:loaned_amount }

    # Add to debtors list if large enough
    if = {
        limit = { var:loaned_amount >= 200 }
        add_to_global_variable_list = {
            name = IB_Important_Debtors
            target = this
        }
    }

    # Start the repayment timer
    create_story = { type = story_agot_loan }
}
```

### Recipe 2: Check If a Character Has Any Bank Loan

```pdx
# As a trigger
trigger = {
    has_character_flag = has_a_loan_flag
    NOT = { has_character_flag = final_default }
}
```

### Recipe 3: Check If a Character Is a Bank Shareholder

```pdx
trigger = {
    OR = {
        AND = { has_variable = IB_Shares     var:IB_Shares > 0 }
        AND = { has_variable = bank1_Shares  var:bank1_Shares > 0 }
        AND = { has_variable = bank2_Shares  var:bank2_Shares > 0 }
        AND = { has_variable = bank3_Shares  var:bank3_Shares > 0 }
    }
}
```

### Recipe 4: Check If a Bank Exists and Has Free Capital

```pdx
trigger = {
    exists = global_var:IB_location
    any_in_global_list = {
        variable = IB_Shareholder
        has_character_flag = IB_Director
    }
    global_var:IB_FreeCapital > min_cash_reserve_IB
}
```

### Recipe 5: Add a New Default Enforcement Action

To add a custom enforcement option, extend `agot_banking.0211` with a new option
block. The pattern is:

1. Add a new option in `agot_banking.0211` with a cost variable and trigger
2. Create two events: one for failure, one for success (following the
   `0101`/`0102` pattern)
3. On success, recover gold and call the bank to update its books
4. On failure, set a flag (e.g., `my_action_failed`) so the `0211` desc can
   report it on the next iteration

### Recipe 6: Force-Dissolve a Custom Bank

```pdx
# Assuming you want to dissolve bank1
every_in_global_list = {
    variable = bank1_Shareholder
    # Pay out remaining value
    if = {
        limit = { has_variable = bank1_Shares }
        add_gold = {
            value = global_var:bank1_ValuePerShare
            multiply = var:bank1_Shares
        }
        remove_variable = bank1_Shares
    }
    if = {
        limit = { has_character_flag = bank1_Director }
        remove_character_flag = bank1_Director
    }
    remove_list_global_variable = { name = bank1_Shareholder  target = this }
    remove_list_global_variable = { name = Shareholder  target = this }
}
# Reset all bank1 globals to zero
remove_global_variable = bank1_location
remove_global_variable = bank1_founder
set_global_variable = { name = bank1_BankValue  value = 0 }
set_global_variable = { name = bank1_FreeCapital  value = 0 }
set_global_variable = { name = bank1_NofShares  value = 0 }
# ... repeat for all bank1_ variables
```

---

## Pitfalls

### 1. Single-Bank Restriction

A character can only hold shares in **one bank at a time**. The system enforces
this in every `is_shown` block by checking that the character has zero shares in
all other banks. If your sub-mod grants shares without this check, the UI will
break and the character may become stuck.

### 2. The `has_a_loan_flag` Is the Master Lock

All loan-related decisions and events check `has_a_loan_flag`. If you remove it
manually without cleaning up the loan variables (`loaned_amount`,
`total_repayment`, etc.) and the debtor list, the bank's books will be
permanently wrong. Always clean up the full set of variables when resolving a
loan.

### 3. Director Death Without `share_inheritance`

If a bank director dies and `share_inheritance` is not triggered (e.g., due to a
mod conflict that blocks `on_death`), the bank becomes permanently leaderless --
no new loans will be issued, no dividends paid, no default enforcement. The
`bank_director_election` effect must fire.

### 4. Bank Dissolution on Conquest

When a realm conquers a territory containing a bank, `dissolve_conquered_bank`
fires -- but **only if the conquering realm already contains another bank**. Two
banks cannot coexist in the same top-level realm. If your sub-mod changes realm
structure, be aware this can silently dissolve banks.

### 5. Story Cycle Only Supports 3 Terms

The `story_agot_loan` story cycle only has effect groups for years 3, 5, and 10.
If you set `loan_term` to any other value, the loan-due event will **never
fire**, and the debt becomes permanent. Always use one of these three values.

### 6. Global Variable Initialization

All global variables must exist before use. The `agot_init_banking_system`
effect handles this on game start, but if your sub-mod runs before it (e.g., in
`on_game_start` with wrong load order), you will get errors. Always check
`exists = global_var:XX_location` before accessing bank state.

### 7. Cash Reserve Guards

Banks will not lend if `FreeCapital <= min_cash_reserve` (15% of BankValue, min
300, max 5000). Banks will not accept investments if
`FreeCapital >= invest_threshold` (25% of BankValue, min 2000, max 7500). These
are critical for bank health -- bypassing them can cause the bank to go
bankrupt.

### 8. Vassal Loan Interest Is Fixed at 25%

Unlike bank loans which have variable rates based on credit score and interest
level, vassal loans always charge exactly 25% interest with no negotiation. The
`vassal_loan_total_amount` is always `vassal_loan_amount * 1.25`.

### 9. The `innovation_currency_03` Gate

Both `buy_shares_decision` and `found_bank_decision` require the character's
culture to have `innovation_currency_03` (the Banking innovation). Characters
from cultures without this innovation can still take loans but cannot invest or
found banks.

### 10. Custom Loc for Bank Names

Bank names are rendered via `agot_bank_name` and `agot_bank_name_list` in
`00_agot_banking_custom_loc.txt`. The Iron Bank always shows as
`bank_name_default_IB`. Custom banks display using the founder's name via
`bank_name_normal` (player-founded) or `bank_name_default` (AI-founded, via
`ai_bank_founder` inactive trait). If your sub-mod creates a bank without
setting the `BankName` variable on the founder, the loc will fall through to a
fallback key.
