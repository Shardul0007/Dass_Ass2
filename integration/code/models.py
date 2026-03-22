from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class CrewMember:
    name: str
    role: Optional[str] = None
    skills: Dict[str, int] = field(default_factory=dict)
    available: bool = True


@dataclass(slots=True)
class Car:
    car_id: str
    model: str
    condition: int = 100  # 0..100

    @property
    def is_drivable(self) -> bool:
        return self.condition > 0


@dataclass(slots=True)
class Race:
    race_id: str
    location: str
    prize_money: int
    driver_name: Optional[str] = None
    car_id: Optional[str] = None


@dataclass(slots=True)
class RaceResult:
    race_id: str
    driver_name: str
    car_id: str
    outcome: str  # "win" | "lose" | "dnf"


@dataclass(slots=True)
class Mission:
    mission_id: str
    mission_type: str
    required_roles: List[str]
    assigned_members: List[str] = field(default_factory=list)
    started: bool = False
