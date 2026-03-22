import pytest

from integration.code.models import Car
from integration.code.system import StreetRaceManager
from integration.code import (
    crew_management,
    inventory,
    mission_planning,
    race_management,
    registration,
)


def _setup_basic_manager() -> StreetRaceManager:
    mgr = StreetRaceManager()
    inventory.add_cash(mgr.inventory, 1000)
    inventory.add_car(mgr.inventory, Car(car_id="CAR1", model="RX-7", condition=100))
    race_management.create_race(mgr.races, "R1", "Industrial Docks", 500)
    return mgr


def test_register_then_assign_role_requires_registration():
    mgr = StreetRaceManager()

    # Integration rule: must register before assigning role.
    with pytest.raises(ValueError):
        crew_management.assign_role(mgr.crew_registry, "Mia", "driver")


def test_register_driver_then_enter_race_success():
    mgr = _setup_basic_manager()

    registration.register_member(mgr.crew_registry, "Mia")
    crew_management.assign_role(mgr.crew_registry, "Mia", "driver")

    race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Mia", "CAR1")

    assert mgr.races["R1"].driver_name == "Mia"
    assert mgr.races["R1"].car_id == "CAR1"


def test_enter_race_rejects_non_driver():
    mgr = _setup_basic_manager()

    registration.register_member(mgr.crew_registry, "Tej")
    crew_management.assign_role(mgr.crew_registry, "Tej", "mechanic")

    # Integration rule: only drivers may be entered.
    with pytest.raises(ValueError):
        race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Tej", "CAR1")


def test_race_win_updates_results_rankings_and_cash():
    mgr = _setup_basic_manager()

    registration.register_member(mgr.crew_registry, "Mia")
    crew_management.assign_role(mgr.crew_registry, "Mia", "driver")
    crew_management.set_skill(mgr.crew_registry, "Mia", "driving", 7)

    race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Mia", "CAR1")

    before_cash = inventory.get_cash(mgr.inventory)
    result = race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, "R1")

    assert result.outcome == "win"
    assert mgr.rankings["Mia"] >= 3
    assert inventory.get_cash(mgr.inventory) == before_cash + 500


def test_race_loss_damages_car():
    mgr = _setup_basic_manager()

    registration.register_member(mgr.crew_registry, "Dom")
    crew_management.assign_role(mgr.crew_registry, "Dom", "driver")
    crew_management.set_skill(mgr.crew_registry, "Dom", "driving", 0)

    race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Dom", "CAR1")
    result = race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, "R1")

    assert result.outcome == "lose"
    assert mgr.inventory.cars["CAR1"].condition == 80


def test_rescue_mission_requires_driver_and_mechanic_available():
    mgr = StreetRaceManager()

    registration.register_member(mgr.crew_registry, "Dom")
    crew_management.assign_role(mgr.crew_registry, "Dom", "driver")

    mission = mission_planning.create_mission(mgr.missions, "M1", "rescue")

    # Only a driver exists; rescue requires driver + mechanic.
    with pytest.raises(ValueError):
        mission_planning.start_mission(mgr.crew_registry, mission)

    mission = mission_planning.create_mission(mgr.missions, "M2", "rescue")

    # Only a driver exists; rescue requires driver + mechanic.
    with pytest.raises(ValueError):
        mission_planning.start_mission(mgr.crew_registry, mission)


def test_inventory_remove_cash_cannot_overdraft():
    mgr = StreetRaceManager()
    inventory.add_cash(mgr.inventory, 10)

    with pytest.raises(ValueError):
        inventory.remove_cash(mgr.inventory, 11)
