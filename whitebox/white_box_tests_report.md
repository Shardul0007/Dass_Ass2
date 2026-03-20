# 1.3 White Box Test Cases (CFG / Branch Coverage)

Date: 2026-03-20

## How to run

From the repo root (`Dass_Ass2/`):

- Run tests: `python -m pytest -q`
- Run branch coverage: `python -m coverage run --branch -m pytest -q`
- Coverage report: `python -m coverage report -m`

## What “white-box” means here

These tests were designed by reading the code and mapping the **decision points** (e.g., `if/elif/else`, early returns, and nested conditions) into separate pytest test cases.

Each test:
- Forces a specific branch to execute by setting up the object state.
- Uses Arrange–Act–Assert.
- Includes at least one assertion.
- Covers edge cases (e.g., `None`, `0`, negative values, large values, missing/invalid actions).

## Errors / logical issues found by the tests (and fixes)

The following defects were exposed by tests (they failed before the fix, and pass after):

### Error 1 — Dice was not 6-sided
- Symptom: `Dice.roll()` called `randint(1, 5)` so a value of 6 could never occur.
- Why it matters: breaks game probability and expected Monopoly rules.
- Test that found it: `test_dice_roll_uses_six_sided_die`.
- Fix: change randint upper bound from 5 to 6.
- Commit: `1ec0a6a` — **Error 1: Fix Dice roll range to 1-6**

### Error 2 — Winner selection was reversed
- Symptom: `Game.find_winner()` returned the **minimum** net worth player instead of the maximum.
- Why it matters: prints the wrong winner at the end of the game.
- Test that found it: `test_find_winner_returns_highest_net_worth_player`.
- Fix: use `max(..., key=net_worth)`.
- Commit: `e557dad` — **Error 2: Fix find_winner to choose highest net worth**

### Error 3 — Passing GO did not award salary
- Symptom: `Player.move()` only paid salary when landing exactly on position 0.
- Why it matters: standard Monopoly behavior is to collect when you **pass or land on GO**.
- Test that found it: `test_player_move_passing_go_awards_salary`.
- Fix: detect wrap-around (`old_pos + steps >= BOARD_SIZE`) and award salary (supports large steps).
- Commit: `483d5a5` — **Error 3: Award GO salary when passing Go**

### Error 4 — Player jail state API mismatch (would crash real gameplay)
- Symptom: `Game` code uses `player.in_jail`, `player.jail_turns`, `player.get_out_of_jail_cards`.
  But `Player` stored jail state only inside `player.jail[...]`.
- Why it matters: when a real `Player` instance is used, `Game.play_turn()` can raise `AttributeError`.
- Test that found it: `test_player_exposes_jail_state_via_attributes`.
- Fix: add compatibility properties on `Player` that mirror the jail dict fields.
- Commit: `c2f2a8f` — **Error 4: Add Player jail-state attributes for Game**

### Error 5 — Bank.collect accepted negative values (docstring mismatch)
- Symptom: `Bank.collect(-10)` reduced bank funds even though the docstring said negatives are ignored.
- Why it matters: code paths that accidentally pass negatives would silently corrupt bank reserves.
- Test that found it: `test_bank_collect_negative_is_ignored`.
- Fix: ignore negative amounts.
- Commit: `1fa7f48` — **Error 5: Ignore negative amounts in Bank.collect**

### Error 6 — Bank.give_loan did not reduce bank funds
- Symptom: issuing a loan credited the player but didn’t reduce the bank’s reserves.
- Why it matters: bank accounting becomes incorrect (bank can “create money”).
- Test that found it: `test_bank_give_loan_reduces_bank_funds_and_credits_player`.
- Fix: route through `Bank.pay_out()`.
- Commit: `2e2421d` — **Error 6: Reduce bank funds when issuing loans**

### Error 7 — Board↔Property constructor mismatch (Board init crash)
- Symptom: `Board` constructed `Property(name, pos, price, rent, group)` but `Property.__init__` expected a dict config.
- Why it matters: the game could crash on board creation.
- Test that found it: `test_board_initializes_without_type_errors`.
- Fix: make `Property.__init__` support both dict and positional construction.
- Commit: `986cbe4` — **Error 7: Fix Property constructor to match Board usage**

### Error 8 — PropertyGroup ownership logic used any() instead of all()
- Symptom: `PropertyGroup.all_owned_by` returned True if *any* property was owned by a player.
- Why it matters: incorrectly doubles rent for partial ownership.
- Test that found it: `test_property_group_all_owned_by_requires_all_properties_owned_by_player`.
- Fix: require `all(...)` and handle empty groups.
- Commit: `70ff69f` — **Error 8: Require full group ownership to be all properties**

### Error 9 — buy_property rejected exact-funds purchases
- Symptom: players with `balance == price` could not buy a property.
- Why it matters: affordability check was stricter than “can afford”.
- Test that found it: `test_buy_property_allows_exact_funds`.
- Fix: change condition from `<=` to `<`.
- Commit: `471209f` — **Error 9: Allow buying property with exact funds**

### Error 10 — pay_rent did not pay the owner
- Symptom: rent was deducted from the tenant but not credited to the owner.
- Why it matters: breaks core economic rules and net-worth outcomes.
- Test that found it: `test_pay_rent_transfers_to_owner_when_not_mortgaged`.
- Fix: add `prop.owner.add_money(rent)`.
- Commit: `7d9ebb7` — **Error 10: Transfer rent payment to property owner**

### Error 11 — trade deducted buyer cash but didn’t credit seller
- Symptom: trade removed cash from buyer but seller never received it.
- Why it matters: trades destroy money and skew balances.
- Test that found it: `test_trade_transfers_cash_to_seller_and_property_to_buyer`.
- Fix: add `seller.add_money(cash_amount)`.
- Commit: `6ff27a1` — **Error 11: Transfer trade cash to seller**

### Error 12 — mortgage_property did not pay out from bank funds
- Symptom: mortgaging used `bank.collect(-payout)` (which is ignored), so bank reserves never decreased.
- Why it matters: bank accounting incorrect; mortgage payout not modeled.
- Test that found it: `test_mortgage_property_pays_out_from_bank_funds`.
- Fix: use `bank.pay_out(payout)` and revert mortgage state on failure.
- Commit: `a5e3dae` — **Error 12: Mortgage uses bank payout**

### Error 13 — unmortgage_property cleared mortgage before affordability check
- Symptom: if a player couldn’t afford the redemption cost, the property still became unmortgaged.
- Why it matters: lets players escape mortgages for free on failed attempts.
- Test that found it: `test_unmortgage_property_does_not_change_state_if_cannot_afford`.
- Fix: compute cost and check affordability first; only call `prop.unmortgage()` after payment.
- Commit: `171d486` — **Error 13: Prevent unaffordable unmortgage from changing state**

## Test case rationale (simple explanations)

Below is why each test case exists (what decision/edge it covers).

### tests/test_dice.py
- `test_dice_roll_uses_six_sided_die`: Ensures the dice uses the correct 1–6 range (a structural assumption used everywhere in the game).
- Additional Dice tests cover doubles-streak increment/reset, `reset()`, `describe()` formatting, and `__repr__`.

### tests/test_game_find_winner.py
- `test_find_winner_returns_highest_net_worth_player`: Ensures winner logic matches the docstring and expected end-of-game behavior.
- `test_find_winner_returns_none_when_no_players`: Covers the empty-player edge case.

### tests/test_game_run.py (Game loop branches)
- `test_run_with_no_players_prints_no_winner_message`: Covers the branch where there is no winner (empty players list).
- `test_run_with_one_player_prints_game_over_banner`: Covers the early-exit condition `len(players) <= 1` and the winner-printing path.
- `test_run_stops_at_max_turns_and_calls_standings_each_turn`: Covers the loop condition where the game stops due to `MAX_TURNS` and verifies standings printing.
- `test_run_exits_when_players_reduce_to_one`: Covers mid-loop player reduction to one remaining player.
- `test_run_propagates_exception_from_play_turn`: Confirms exceptions are not swallowed (failure scenario).
- `test_run_when_not_running_skips_loop_and_does_not_call_play_turn`: Covers the short-circuit where `running` is already `False`.

### tests/test_game_play_turn.py (Turn decision branches)
- `test_play_turn_in_jail_branch_handles_jail_and_advances`: Covers the `if player.in_jail` branch; verifies jail handling and turn advancement.
- `test_play_turn_three_doubles_sends_player_to_jail_and_advances`: Covers the `doubles_streak >= 3` branch that forces jail.
- `test_play_turn_doubles_grants_extra_turn_does_not_advance`: Covers the doubles branch where the player gets an extra roll (no `advance_turn`).
- `test_play_turn_non_doubles_advances_turn`: Covers the non-doubles branch (normal advancement).

### tests/test_game_move_and_resolve.py (Tile-resolution branches)
- `test_move_and_resolve_go_to_jail_branch`: Covers tile == `go_to_jail`.
- `test_move_and_resolve_income_tax_branch_deducts_and_collects`: Covers tile == `income_tax` and the bank collection side-effect.
- `test_move_and_resolve_luxury_tax_branch_deducts_and_collects`: Covers tile == `luxury_tax`.
- `test_move_and_resolve_free_parking_branch_no_state_change`: Covers tile == `free_parking` (no money movement).
- `test_move_and_resolve_chance_branch_draws_and_applies_card`: Covers tile == `chance` with a draw/apply call.
- `test_move_and_resolve_community_chest_branch_draws_and_applies_card`: Covers tile == `community_chest`.
- `test_move_and_resolve_railroad_with_property_calls_handle_property_tile`: Covers railroad tile with property present.
- `test_move_and_resolve_railroad_with_no_property_does_not_call_handle_property_tile`: Covers railroad tile with property missing (edge case).
- `test_move_and_resolve_property_with_property_calls_handle_property_tile`: Covers property tile with property present.
- `test_move_and_resolve_property_with_no_property_does_not_call_handle_property_tile`: Covers property tile with property missing (edge case).
- `test_move_and_resolve_blank_tile_branch_only_checks_bankruptcy`: Covers the “no matching tile type” fall-through path.

### tests/test_game_apply_card.py (Card action branches)
- `test_apply_card_none_returns_no_state_change`: Covers the early-return branch when no card is drawn.
- `test_apply_card_collect_increases_balance`: Covers action == `collect` with positive value.
- `test_apply_card_collect_zero_value_no_change`: Edge case: value == 0.
- `test_apply_card_pay_decreases_balance_and_collects`: Covers action == `pay` with positive value.
- `test_apply_card_pay_negative_value_raises_value_error`: Edge case: negative value should be rejected (invalid input).
- `test_apply_card_jail_sends_player_to_jail`: Covers action == `jail`.
- `test_apply_card_jail_free_increments_card_count`: Covers action == `jail_free`.
- `test_apply_card_move_to_passes_go_awards_salary`: Covers `move_to` with wrap-around (pass Go).
- `test_apply_card_move_to_does_not_pass_go_no_salary`: Covers `move_to` without wrap-around.
- `test_apply_card_move_to_lands_on_property_calls_handle_property_tile`: Covers nested branch `tile == 'property'` and property exists.
- `test_apply_card_move_to_not_property_does_not_call_handle_property_tile`: Covers nested branch `tile != 'property'`.
- `test_apply_card_move_to_property_with_missing_property_does_not_call_handle_property_tile`: Edge case: `tile == 'property'` but the property lookup returns `None`.
- `test_apply_card_birthday_transfers_from_all_eligible_players`: Covers transfer-from-all with both eligible and ineligible donors.
- `test_apply_card_collect_from_all_no_eligible_donors_no_transfer`: Covers transfer-from-all where nobody can pay (edge case).
- `test_apply_card_invalid_action_no_effect`: Covers invalid/unhandled action (no handler).

### tests/test_game_economy_flows.py (Money movement correctness)
- Covers key money-transfer branches for property purchase, rent, trade, mortgage, and unmortgage (including boundary/insufficient-funds states).

### tests/test_game_menus_and_jail.py (Interactive/menu/jail branches)
- Covers jail decision branches (use card, decline card, pay fine, no-action, mandatory release).
- Covers `interactive_menu()` choices (1–6, invalid choice) and submenu early-returns / invalid selections.
- Covers auction bid validation branches (pass, too low, too high, winner, no bids).

### tests/test_game_remaining_branches.py (Final branch completion)
- Covers `Game.__init__`, `advance_turn/current_player`, remaining property-tile paths, trade failure branches, `_check_bankruptcy` branches, and other small edge paths needed for full branch coverage.

### tests/test_bank.py
- Covers bank collect/pay_out boundary behavior, give-loan accounting, summary printing, and `__repr__`.

### tests/test_cards.py
- Covers deck draw/peek cycle behavior and reshuffle/reset/representation branches.

### tests/test_property_and_board.py
- Covers `Board` tile typing/purchasable/special-tile logic, ownership helpers, and `__repr__`.
- Covers `Property` construction styles + rent/mortgage/unmortgage branches and `PropertyGroup` ownership/counting branches.

### tests/test_ui.py
- Covers input helpers (`safe_int_input`, `confirm`), formatting, banner printing, player cards (with/without jail/properties), and board ownership register output.

### tests/test_player.py (Player state/edge cases)
- `test_player_add_money_increases_balance`: Normal add path.
- `test_player_add_money_negative_raises_value_error`: Branch where amount < 0.
- `test_player_deduct_money_decreases_balance`: Normal deduct path.
- `test_player_deduct_money_negative_raises_value_error`: Branch where amount < 0.
- `test_player_is_bankrupt_false_when_positive_balance`: Decision boundary above 0.
- `test_player_is_bankrupt_true_when_zero_balance`: Decision boundary at 0.
- `test_player_move_lands_on_go_awards_salary`: Landing on Go should award salary.
- `test_player_move_not_on_go_does_not_award_salary`: Normal move without Go.
- `test_player_move_passing_go_awards_salary`: Wrap-around (passing Go) edge case.
- `test_player_go_to_jail_sets_position_and_jail_state`: Jail state update branch.
- `test_player_exposes_jail_state_via_attributes`: Ensures API compatibility with `Game` logic.
- `test_player_status_line_has_jailed_tag_when_jailed`: Branch where jailed tag should appear.
- `test_player_status_line_no_jailed_tag_when_not_jailed`: Branch where jailed tag should not appear.
- `test_player_add_property_adds_once_and_remove_property_removes`: Property list add/remove behavior.
- `test_player_remove_property_when_absent_no_change`: Edge case remove of missing property.
- `test_player_net_worth_equals_balance`: Net worth logic.
- `test_player_repr_contains_name`: Debug representation sanity.
