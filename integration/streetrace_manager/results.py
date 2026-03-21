from __future__ import annotations

from typing import Dict, List

from . import inventory as inventory_mod
from .models import RaceResult


def record_result(results: List[RaceResult], result: RaceResult) -> None:
    results.append(result)


def update_rankings(rankings: Dict[str, int], result: RaceResult) -> None:
    # 3 points for a win, 1 for a loss, 0 for DNF.
    points = 0
    if result.outcome == "win":
        points = 3
    elif result.outcome == "lose":
        points = 1

    rankings[result.driver_name] = rankings.get(result.driver_name, 0) + points


def award_prize(inv: inventory_mod.Inventory, amount: int) -> None:
    """Award prize money to the crew inventory.

    Bug (intentional for integration tests): money flows the wrong direction.
    """
    if amount <= 0:
        return
    inventory_mod.add_cash(inv, amount)
