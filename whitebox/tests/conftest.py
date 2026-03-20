import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import pytest


# Ensure imports like `import game`, `import player`, etc. resolve.
_CODE_MONEYPOLY_DIR = Path(__file__).resolve().parents[1] / "code" / "moneypoly"
sys.path.insert(0, str(_CODE_MONEYPOLY_DIR))


@dataclass
class StubProperty:
    name: str = "Prop"
    price: int = 100
    owner: Any = None
    is_mortgaged: bool = False
    mortgage_value: int = 50

    def get_rent(self) -> int:
        return 10


@dataclass
class StubPlayer:
    name: str
    balance: int = 1500
    position: int = 0
    in_jail: bool = False
    jail_turns: int = 0
    get_out_of_jail_cards: int = 0
    is_eliminated: bool = False
    properties: list = field(default_factory=list)

    def add_money(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot add negative")
        self.balance += amount

    def deduct_money(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot deduct negative")
        self.balance -= amount

    def is_bankrupt(self) -> bool:
        return self.balance <= 0

    def net_worth(self) -> int:
        return self.balance

    def move(self, steps: int) -> int:
        self.position = (self.position + steps) % 40
        return self.position

    def go_to_jail(self) -> None:
        self.position = 10
        self.in_jail = True
        self.jail_turns = 0

    def add_property(self, prop: Any) -> None:
        if prop not in self.properties:
            self.properties.append(prop)

    def remove_property(self, prop: Any) -> None:
        if prop in self.properties:
            self.properties.remove(prop)

    def count_properties(self) -> int:
        return len(self.properties)


@dataclass
class StubDice:
    roll_value: int = 7
    doubles_streak: int = 0
    doubles: bool = False

    def roll(self) -> int:
        return self.roll_value

    def describe(self) -> str:
        return "stub"

    def is_doubles(self) -> bool:
        return self.doubles


@dataclass
class StubBank:
    collected: int = 0
    payouts: list[int] = field(default_factory=list)

    def collect(self, amount: int) -> None:
        self.collected += amount

    def pay_out(self, amount: int) -> int:
        self.payouts.append(amount)
        return amount


@dataclass
class StubDeck:
    card: Optional[dict] = None

    def draw(self) -> Optional[dict]:
        return self.card


@dataclass
class StubBoard:
    tile: str = "blank"
    prop: Optional[StubProperty] = None

    def get_tile_type(self, position: int) -> str:
        return self.tile

    def get_property_at(self, position: int) -> Optional[StubProperty]:
        return self.prop


class StubUI:
    def __init__(self):
        self.banners: list[str] = []
        self.standings_calls: int = 0
        self.board_ownership_calls: int = 0
        self.confirm_answers: list[bool] = []
        self.int_answers: list[int] = []

    def print_banner(self, title: str) -> None:
        self.banners.append(title)

    def print_standings(self, players: list) -> None:
        self.standings_calls += 1

    def print_board_ownership(self, board: Any) -> None:
        self.board_ownership_calls += 1

    def confirm(self, prompt: str) -> bool:
        if self.confirm_answers:
            return self.confirm_answers.pop(0)
        return False

    def safe_int_input(self, prompt: str, default: int = 0) -> int:
        if self.int_answers:
            return self.int_answers.pop(0)
        return default


@pytest.fixture
def stub_ui() -> StubUI:
    return StubUI()
