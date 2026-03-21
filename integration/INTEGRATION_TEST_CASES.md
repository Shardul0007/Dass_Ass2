# Integration Test Design (StreetRace Manager)

Each case validates **data flow and business rules across modules**, not just isolated unit logic.

> Tip: after you run the tests, fill in **Actual Result** and note which bug-fix commit resolved it.

| ID | Scenario | Modules involved | Why needed | Expected result | Actual result (before fixes) | Errors / logical issues found |
|---:|---|---|---|---|---|---|
| IT-01 | Assign role without registration | Registration + Crew Management | Enforces rule: member must exist before role assignment | Rejects with `ValueError` | FAIL (observed: did not raise) | `assign_role` incorrectly creates a new member when missing |
| IT-02 | Register driver then enter race | Registration + Crew Management + Inventory + Race Management | Confirms the happy-path integration works end-to-end | Race entry saved with correct driver+car | TBD | None expected on happy path |
| IT-03 | Enter race with non-driver | Registration + Crew Management + Inventory + Race Management | Enforces rule: only drivers can race | Rejects with `ValueError` | FAIL (observed: did not raise) | `enter_race` does not validate role == driver |
| IT-04 | Win race updates rankings and cash | Race Management + Results + Inventory | Ensures results update multiple modules consistently | Rankings increase; cash increases by prize | FAIL (observed: cash not increased) | `award_prize` moves cash in wrong direction (debit vs credit) |
| IT-05 | Lose race damages car; rescue mission requires mechanic | Race Management + Maintenance + Mission Planning + Crew Management | Validates the “damage → mechanic requirement” workflow | Car condition decreases; mission cannot start without mechanic | FAIL (observed: condition unchanged; mission started) | `damage_car` increases condition; `can_start_mission` uses ANY instead of ALL roles |
| IT-06 | Prevent inventory overdraft | Inventory | Prevents inconsistent state that breaks downstream prize/cost logic | Rejects with `ValueError` | FAIL (observed: did not raise) | `remove_cash` allows overdraft silently |

## Planned intentional integration bugs (initial state)

Initial implementation intentionally includes **6 integration-relevant defects** so the integration tests can detect and drive fixes:

1. `crew_management.assign_role` allows assigning a role to an unregistered name.
2. `race_management.enter_race` does not enforce `driver` role.
3. `results.award_prize` debits cash instead of crediting it.
4. `mission_planning.can_start_mission` requires ANY role instead of ALL required roles.
5. `maintenance.damage_car` increases condition instead of decreasing it.
6. `inventory.remove_cash` allows overdraft instead of raising.
