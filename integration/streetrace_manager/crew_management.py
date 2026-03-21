from __future__ import annotations

from typing import Dict

from .models import CrewMember


VALID_ROLES = {"driver", "mechanic", "strategist"}


def assign_role(registry: Dict[str, CrewMember], name: str, role: str) -> None:
    """Assign a role to a crew member.

    Bug (intentional for integration tests): missing registration check.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    member = registry.get(name)
    if member is None:
        raise ValueError("Crew member must be registered before assigning a role")
    member.role = role
    registry[name] = member


def set_skill(registry: Dict[str, CrewMember], name: str, skill: str, level: int) -> None:
    if level < 0 or level > 10:
        raise ValueError("Skill level must be 0..10")

    member = registry.get(name)
    if member is None:
        raise ValueError("Crew member must be registered before setting skills")

    member.skills[skill] = level


def get_role(registry: Dict[str, CrewMember], name: str) -> str | None:
    member = registry.get(name)
    if member is None:
        return None
    return member.role


def set_availability(registry: Dict[str, CrewMember], name: str, available: bool) -> None:
    member = registry.get(name)
    if member is None:
        raise ValueError("Crew member must be registered")
    member.available = available


def is_available_for_role(registry: Dict[str, CrewMember], role: str) -> bool:
    return any(m.available and m.role == role for m in registry.values())
