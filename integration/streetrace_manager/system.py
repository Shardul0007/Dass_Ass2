from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .inventory import Inventory
from .models import CrewMember, Mission, Race, RaceResult


@dataclass(slots=True)
class StreetRaceManager:
    crew_registry: Dict[str, CrewMember] = field(default_factory=dict)
    inventory: Inventory = field(default_factory=Inventory)
    races: Dict[str, Race] = field(default_factory=dict)
    results: List[RaceResult] = field(default_factory=list)
    rankings: Dict[str, int] = field(default_factory=dict)
    missions: Dict[str, Mission] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)

    def audit(self, message: str) -> None:
        self.events.append(message)
