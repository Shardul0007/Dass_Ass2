from __future__ import annotations

from typing import Dict

from . import crew_management
from .models import CrewMember, Mission


MISSION_REQUIREMENTS = {
    "delivery": ["driver"],
    "rescue": ["driver", "mechanic"],
    "scout": ["strategist"],
}


def create_mission(missions: Dict[str, Mission], mission_id: str, mission_type: str) -> Mission:
    if mission_id in missions:
        raise ValueError(f"Mission already exists: {mission_id}")
    if mission_type not in MISSION_REQUIREMENTS:
        raise ValueError("Unknown mission type")

    mission = Mission(mission_id=mission_id, mission_type=mission_type, required_roles=MISSION_REQUIREMENTS[mission_type])
    missions[mission_id] = mission
    return mission


def assign_members_to_mission(registry: Dict[str, CrewMember], mission: Mission, member_names: list[str]) -> None:
    for name in member_names:
        member = registry.get(name)
        if member is None:
            raise ValueError("Crew member must be registered before assignment")
        mission.assigned_members.append(name)


def can_start_mission(registry: Dict[str, CrewMember], mission: Mission) -> bool:
    """Verify required roles are available.

    Bug (intentional for integration tests): uses ANY role rather than ALL.
    """
    required = mission.required_roles
    return all(crew_management.is_available_for_role(registry, r) for r in required)


def start_mission(registry: Dict[str, CrewMember], mission: Mission) -> None:
    if not can_start_mission(registry, mission):
        raise ValueError("Mission cannot start: required roles unavailable")
    mission.started = True
