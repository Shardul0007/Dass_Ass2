# Integration Test Design (StreetRace Manager)

Each case validates **data flow and business rules across modules**, not just isolated unit logic.

> Tip: after you run the tests, fill in **Actual Result** and note which bug-fix commit resolved it.

|    ID | Scenario                                                | Modules involved                                                   | Why needed                                                          | Expected result                                                | Actual result (before fixes)                          | Errors / logical issues found                                                       |
| ----: | ------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------- |
| IT-01 | Assign role without registration                        | Registration + Crew Management                                     | Enforces rule: member must exist before role assignment             | Rejects with `ValueError`                                      | FAIL (observed: did not raise)                        | `assign_role` incorrectly creates a new member when missing                         |
| IT-02 | Register driver then enter race                         | Registration + Crew Management + Inventory + Race Management       | Confirms the happy-path integration works end-to-end                | Race entry saved with correct driver+car                       | TBD                                                   | None expected on happy path                                                         |
| IT-03 | Enter race with non-driver                              | Registration + Crew Management + Inventory + Race Management       | Enforces rule: only drivers can race                                | Rejects with `ValueError`                                      | FAIL (observed: did not raise)                        | `enter_race` does not validate role == driver                                       |
| IT-04 | Win race updates rankings and cash                      | Race Management + Results + Inventory                              | Ensures results update multiple modules consistently                | Rankings increase; cash increases by prize                     | FAIL (observed: cash not increased)                   | `award_prize` moves cash in wrong direction (debit vs credit)                       |
| IT-05 | Lose race damages car; rescue mission requires mechanic | Race Management + Maintenance + Mission Planning + Crew Management | Validates the “damage → mechanic requirement” workflow              | Car condition decreases; mission cannot start without mechanic | FAIL (observed: condition unchanged; mission started) | `damage_car` increases condition; `can_start_mission` uses ANY instead of ALL roles |
| IT-06 | Prevent inventory overdraft                             | Inventory                                                          | Prevents inconsistent state that breaks downstream prize/cost logic | Rejects with `ValueError`                                      | FAIL (observed: did not raise)                        | `remove_cash` allows overdraft silently                                             |

## Planned intentional integration bugs (initial state)

Initial implementation intentionally includes **6 integration-relevant defects** so the integration tests can detect and drive fixes:

1. `crew_management.assign_role` allows assigning a role to an unregistered name.
2. `race_management.enter_race` does not enforce `driver` role.
3. `results.award_prize` debits cash instead of crediting it.
4. `mission_planning.can_start_mission` requires ANY role instead of ALL required roles.
5. `maintenance.damage_car` increases condition instead of decreasing it.
6. `inventory.remove_cash` allows overdraft instead of raising.

## How to run (integration tests)

From the repo root (`Dass_Ass2/`):

- Run the integration test suite: `python -m pytest integration/tests -q`

## Test case rationale (simple explanations)

This section explains, in plain language, **why each test exists** and what cross-module rule or decision path it validates.

### integration/tests/test_integration_flows.py (Iteration 1 core flows)

- `test_register_then_assign_role_requires_registration`: Ensures the system does not allow role assignment for a name that was never registered.
- `test_register_driver_then_enter_race_success`: Happy path that proves Registration → Crew role → Race entry works end-to-end.
- `test_enter_race_rejects_non_driver`: Ensures the “only drivers can race” business rule is enforced.
- `test_race_win_updates_results_rankings_and_cash`: Verifies the win-path data flow touches **Results + Rankings + Inventory cash** (all must update consistently).
- `test_race_loss_damages_car`: Verifies the lose-path triggers **Maintenance damage** and reduces car condition.
- `test_rescue_mission_requires_driver_and_mechanic_available`: Ensures missions with multiple required roles (rescue) cannot start unless **all** required roles are available.
- `test_inventory_remove_cash_cannot_overdraft`: Ensures the Inventory layer blocks negative cash states (prevents downstream logic from becoming inconsistent).

### integration/tests/test_integration_iteration2_paths.py (Iteration 2 decision/edge paths)

**Registration**
- `test_register_member_strips_whitespace_and_stores_member`: Ensures names are normalized ("  Mia  " becomes "Mia") so later lookups behave consistently across modules.
- `test_register_member_rejects_blank_name`: Prevents creating invalid members that would break later role/skill/race logic.
- `test_register_member_rejects_duplicate_registration`: Ensures registry integrity (no accidental overwrites).

**Crew management**
- `test_assign_role_rejects_invalid_role`: Confirms invalid roles are blocked so later checks like "driver-only" remain reliable.
- `test_set_skill_requires_registration_and_range_checked`: Validates skill assignment preconditions and boundaries (0..10), because race outcome depends on skill.

**Inventory (cash)**
- `test_inventory_cash_add_remove_nonpositive_are_noops`: Ensures defensive behavior for bad inputs (0/negative) so cash doesn’t change unexpectedly.
- `test_inventory_remove_cash_exact_balance_to_zero`: Covers the boundary case where balance equals amount (should succeed).

**Race management**
- `test_create_race_rejects_duplicate_id_and_nonpositive_prize`: Validates race registry integrity and that prize money must be meaningful.
- `test_enter_race_rejects_missing_race_or_missing_car`: Validates error branches for missing dependencies before a race can be entered.
- `test_enter_race_rejects_registered_member_without_driver_role`: Validates the role gate when the member exists but is not a driver.
- `test_run_race_rejects_missing_race_and_missing_entry`: Validates run-time guards: you can’t run a race that doesn’t exist or has no entry.
- `test_run_race_win_records_result_updates_rankings_awards_prize_and_no_damage`: Full win-path integration: record result, add ranking points, credit prize cash, and confirm no damage on a win.
- `test_run_race_lose_records_result_updates_rankings_no_prize_and_damages_car`: Full lose-path integration: record result, add 1 point, no prize money, and apply car damage.

**Maintenance**
- `test_damage_and_repair_clamp_and_ignore_nonpositive`: Ensures damage/repair clamps within valid bounds (0..100) and ignores nonpositive inputs.

**Mission planning**
- `test_mission_create_rejects_unknown_type_and_duplicate_id`: Ensures mission type validation and prevents accidental overwrites.
- `test_assign_members_to_mission_requires_registered_members`: Ensures you cannot assign non-existent people to missions.
- `test_mission_start_respects_role_availability_and_sets_started`: Validates that starting a mission depends on role availability and that the mission state flips to started on success.

**Audit logging**
- `test_audit_log_records_events_via_manager`: Ensures `StreetRaceManager.audit()` produces an audit event (integration with the audit_log module).

## Errors detected and fixed

These integration tests were used to detect (and then verify fixes for) the following defects in the StreetRace Manager implementation.

- Missing registration guard in role assignment
	- Detected by: `test_register_then_assign_role_requires_registration`
	- Fix commit: `d2cd6b2` — integration: fix role assignment requires registration

- Race entry did not enforce driver-only rule
	- Detected by: `test_enter_race_rejects_non_driver`
	- Fix commit: `c8b1e1d` — integration: enforce driver role for race entry

- Prize money flow was incorrect (cash not credited on win)
	- Detected by: `test_race_win_updates_results_rankings_and_cash`
	- Fix commit: `836b178` — integration: fix prize money credits inventory

- Losing a race did not correctly damage the car
	- Detected by: `test_race_loss_damages_car`
	- Fix commit: `73922e1` — integration: fix race damage reduces car condition

- Mission start logic allowed starting when only some required roles were available
	- Detected by: `test_rescue_mission_requires_driver_and_mechanic_available`
	- Fix commit: `27b5be4` — integration: fix missions require all roles available

- Inventory allowed overdraft (could go negative)
	- Detected by: `test_inventory_remove_cash_cannot_overdraft`
	- Fix commit: `2b4b3da` — integration: prevent inventory cash overdraft

### Iteration 2 test expansion result

- Commit: `6b39eeb` — iteration 2 for testing
- Outcome: No new defects were detected by the expanded decision/edge-path suite (all integration tests pass).
