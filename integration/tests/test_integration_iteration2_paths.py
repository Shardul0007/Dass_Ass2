import pytest

from integration.code.models import Car
from integration.code.system import StreetRaceManager
from integration.code import (
    crew_management,
    inventory,
    maintenance,
    mission_planning,
    race_management,
    registration,
)


def _manager_with_cash_and_car(*, cash: int = 1000, car_condition: int = 100) -> StreetRaceManager:
    mgr = StreetRaceManager()
    inventory.add_cash(mgr.inventory, cash)
    inventory.add_car(mgr.inventory, Car(car_id="CAR1", model="RX-7", condition=car_condition))
    return mgr


def _create_basic_race(mgr: StreetRaceManager, *, race_id: str = "R1", prize: int = 500) -> None:
    race_management.create_race(mgr.races, race_id, "Industrial Docks", prize)


def _register_driver(mgr: StreetRaceManager, name: str, *, driving_skill: int | None = None) -> None:
    registration.register_member(mgr.crew_registry, name)
    crew_management.assign_role(mgr.crew_registry, name, "driver")
    if driving_skill is not None:
        crew_management.set_skill(mgr.crew_registry, name, "driving", driving_skill)


def _register_mechanic(mgr: StreetRaceManager, name: str, *, available: bool = True) -> None:
    registration.register_member(mgr.crew_registry, name)
    crew_management.assign_role(mgr.crew_registry, name, "mechanic")
    crew_management.set_availability(mgr.crew_registry, name, available)


def test_register_member_strips_whitespace_and_stores_member():
    mgr = StreetRaceManager()

    member = registration.register_member(mgr.crew_registry, "  Mia  ")

    assert member.name == "Mia"
    assert "Mia" in mgr.crew_registry


def test_register_member_rejects_blank_name():
    mgr = StreetRaceManager()

    with pytest.raises(ValueError):
        registration.register_member(mgr.crew_registry, "   ")


def test_register_member_rejects_duplicate_registration():
    mgr = StreetRaceManager()

    registration.register_member(mgr.crew_registry, "Mia")

    with pytest.raises(ValueError):
        registration.register_member(mgr.crew_registry, "Mia")


def test_assign_role_rejects_invalid_role():
    mgr = StreetRaceManager()

    registration.register_member(mgr.crew_registry, "Mia")

    with pytest.raises(ValueError):
        crew_management.assign_role(mgr.crew_registry, "Mia", "pilot")


def test_set_skill_requires_registration_and_range_checked():
    mgr = StreetRaceManager()

    with pytest.raises(ValueError):
        crew_management.set_skill(mgr.crew_registry, "Mia", "driving", 5)

    registration.register_member(mgr.crew_registry, "Mia")

    with pytest.raises(ValueError):
        crew_management.set_skill(mgr.crew_registry, "Mia", "driving", -1)

    with pytest.raises(ValueError):
        crew_management.set_skill(mgr.crew_registry, "Mia", "driving", 11)


def test_inventory_cash_add_remove_nonpositive_are_noops():
    mgr = StreetRaceManager()

    inventory.add_cash(mgr.inventory, 0)
    inventory.add_cash(mgr.inventory, -5)
    assert inventory.get_cash(mgr.inventory) == 0

    inventory.remove_cash(mgr.inventory, 0)
    inventory.remove_cash(mgr.inventory, -1)
    assert inventory.get_cash(mgr.inventory) == 0


def test_inventory_remove_cash_exact_balance_to_zero():
    mgr = StreetRaceManager()

    inventory.add_cash(mgr.inventory, 50)
    inventory.remove_cash(mgr.inventory, 50)

    assert inventory.get_cash(mgr.inventory) == 0


def test_create_race_rejects_duplicate_id_and_nonpositive_prize():
    mgr = StreetRaceManager()

    _create_basic_race(mgr, race_id="R1", prize=500)

    with pytest.raises(ValueError):
        race_management.create_race(mgr.races, "R1", "Same Place", 100)

    with pytest.raises(ValueError):
        race_management.create_race(mgr.races, "R2", "Place", 0)


def test_enter_race_rejects_missing_race_or_missing_car():
    mgr = _manager_with_cash_and_car()
    _register_driver(mgr, "Mia")

    with pytest.raises(ValueError):
        race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R404", "Mia", "CAR1")

    _create_basic_race(mgr, race_id="R1")

    with pytest.raises(ValueError):
        race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Mia", "CAR404")


def test_enter_race_rejects_registered_member_without_driver_role():
    mgr = _manager_with_cash_and_car()
    _create_basic_race(mgr)

    registration.register_member(mgr.crew_registry, "Tej")
    crew_management.assign_role(mgr.crew_registry, "Tej", "mechanic")

    with pytest.raises(ValueError):
        race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Tej", "CAR1")


def test_run_race_rejects_missing_race_and_missing_entry():
    mgr = _manager_with_cash_and_car()

    with pytest.raises(ValueError):
        race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, "R404")

    _create_basic_race(mgr, race_id="R1")

    with pytest.raises(ValueError):
        race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, "R1")


def test_run_race_win_records_result_updates_rankings_awards_prize_and_no_damage():
    mgr = _manager_with_cash_and_car(cash=100, car_condition=100)
    _create_basic_race(mgr, prize=250)
    _register_driver(mgr, "Mia", driving_skill=10)

    race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Mia", "CAR1")

    before_cash = inventory.get_cash(mgr.inventory)
    before_condition = mgr.inventory.cars["CAR1"].condition

    result = race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, "R1")

    assert result.outcome == "win"
    assert len(mgr.results) == 1
    assert mgr.rankings["Mia"] == 3
    assert inventory.get_cash(mgr.inventory) == before_cash + 250
    assert mgr.inventory.cars["CAR1"].condition == before_condition


def test_run_race_lose_records_result_updates_rankings_no_prize_and_damages_car():
    mgr = _manager_with_cash_and_car(cash=100, car_condition=100)
    _create_basic_race(mgr, prize=250)
    _register_driver(mgr, "Dom", driving_skill=0)

    race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, "R1", "Dom", "CAR1")

    before_cash = inventory.get_cash(mgr.inventory)

    result = race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, "R1")

    assert result.outcome == "lose"
    assert len(mgr.results) == 1
    assert mgr.rankings["Dom"] == 1
    assert inventory.get_cash(mgr.inventory) == before_cash
    assert mgr.inventory.cars["CAR1"].condition == 80


def test_damage_and_repair_clamp_and_ignore_nonpositive():
    car = Car(car_id="C1", model="Test", condition=10)

    maintenance.damage_car(car, -5)
    assert car.condition == 10

    maintenance.damage_car(car, 50)
    assert car.condition == 0

    maintenance.repair_car(car, 0)
    assert car.condition == 0

    maintenance.repair_car(car, 150)
    assert car.condition == 100


def test_mission_create_rejects_unknown_type_and_duplicate_id():
    mgr = StreetRaceManager()

    with pytest.raises(ValueError):
        mission_planning.create_mission(mgr.missions, "M1", "unknown")

    mission_planning.create_mission(mgr.missions, "M1", "delivery")

    with pytest.raises(ValueError):
        mission_planning.create_mission(mgr.missions, "M1", "delivery")


def test_assign_members_to_mission_requires_registered_members():
    mgr = StreetRaceManager()
    mission = mission_planning.create_mission(mgr.missions, "M1", "delivery")

    with pytest.raises(ValueError):
        mission_planning.assign_members_to_mission(mgr.crew_registry, mission, ["Mia"])


def test_mission_start_respects_role_availability_and_sets_started():
    mgr = StreetRaceManager()

    _register_driver(mgr, "Mia")
    _register_mechanic(mgr, "Tej", available=False)

    mission = mission_planning.create_mission(mgr.missions, "M1", "rescue")

    with pytest.raises(ValueError):
        mission_planning.start_mission(mgr.crew_registry, mission)

    crew_management.set_availability(mgr.crew_registry, "Tej", True)

    mission_planning.start_mission(mgr.crew_registry, mission)

    assert mission.started is True


def test_audit_log_records_events_via_manager():
    mgr = StreetRaceManager()

    assert mgr.events == []
    mgr.audit("created manager")

    assert len(mgr.events) == 1
    assert mgr.events[0].message == "created manager"
