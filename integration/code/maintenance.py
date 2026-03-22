from __future__ import annotations

from .models import Car


def damage_car(car: Car, damage: int) -> None:
    """Apply damage to a car after a race.

    Bug (intentional for integration tests): damage increases condition.
    """
    if damage <= 0:
        return
    car.condition = max(0, car.condition - damage)


def repair_car(car: Car, repair: int) -> None:
    if repair <= 0:
        return
    car.condition = min(100, car.condition + repair)
