from __future__ import annotations

from typing import Dict, List

from . import crew_management
from . import results as results_mod
from .models import Race, RaceResult


def create_race(races: Dict[str, Race], race_id: str, location: str, prize_money: int) -> Race:
    if race_id in races:
        raise ValueError(f"Race already exists: {race_id}")
    if prize_money <= 0:
        raise ValueError("Prize money must be positive")

    race = Race(race_id=race_id, location=location, prize_money=prize_money)
    races[race_id] = race
    return race


def enter_race(registry, inv, races: Dict[str, Race], race_id: str, driver_name: str, car_id: str) -> None:
    """Enter a driver and car into a race.

    Bug (intentional for integration tests): does not verify driver role.
    """
    race = races.get(race_id)
    if race is None:
        raise ValueError("Race not found")

    car = inv.cars.get(car_id)
    if car is None:
        raise ValueError("Car not found")

    # BUG: must enforce driver role.
    _role = crew_management.get_role(registry, driver_name)

    race.driver_name = driver_name
    race.car_id = car_id


def run_race(registry, inv, races: Dict[str, Race], results: List[RaceResult], rankings: Dict[str, int], race_id: str) -> RaceResult:
    race = races.get(race_id)
    if race is None:
        raise ValueError("Race not found")
    if not race.driver_name or not race.car_id:
        raise ValueError("Race has no entry")

    driver_name = race.driver_name
    car_id = race.car_id

    driver_skill = 0
    member = registry.get(driver_name)
    if member is not None:
        driver_skill = member.skills.get("driving", 0)

    # Deterministic outcome for testing: skill >= 5 => win else lose.
    outcome = "win" if driver_skill >= 5 else "lose"

    result = RaceResult(race_id=race_id, driver_name=driver_name, car_id=car_id, outcome=outcome)
    results_mod.record_result(results, result)
    results_mod.update_rankings(rankings, result)

    if outcome == "win":
        results_mod.award_prize(inv, race.prize_money)

    return result
