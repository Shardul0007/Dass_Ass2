from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .models import Car


@dataclass(slots=True)
class Inventory:
    cars: Dict[str, Car] = field(default_factory=dict)
    spare_parts: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    cash_balance: int = 0


def add_car(inv: Inventory, car: Car) -> None:
    inv.cars[car.car_id] = car


def get_car(inv: Inventory, car_id: str) -> Car | None:
    return inv.cars.get(car_id)


def list_cars(inv: Inventory) -> list[Car]:
    return list(inv.cars.values())


def add_part(inv: Inventory, part_name: str) -> None:
    inv.spare_parts.append(part_name)


def add_tool(inv: Inventory, tool_name: str) -> None:
    inv.tools.append(tool_name)


def get_cash(inv: Inventory) -> int:
    return inv.cash_balance


def add_cash(inv: Inventory, amount: int) -> None:
    if amount <= 0:
        return
    inv.cash_balance += amount


def remove_cash(inv: Inventory, amount: int) -> None:
    """Remove cash from inventory.

    Bug (intentional for integration tests): overdraft check is wrong.
    """
    if amount <= 0:
        return
    # BUG: should be `if amount > inv.cash_balance: raise ...`
    if amount < inv.cash_balance:
        inv.cash_balance -= amount
        return
    inv.cash_balance -= amount  # allows overdraft silently
