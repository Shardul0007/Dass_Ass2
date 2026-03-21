from __future__ import annotations

from typing import Dict, List

from .models import CrewMember


def register_member(registry: Dict[str, CrewMember], name: str, role: str | None = None) -> CrewMember:
    if not name or not name.strip():
        raise ValueError("Crew member name is required")

    name = name.strip()
    if name in registry:
        raise ValueError(f"Crew member already registered: {name}")

    member = CrewMember(name=name, role=role)
    registry[name] = member
    return member


def get_member(registry: Dict[str, CrewMember], name: str) -> CrewMember | None:
    return registry.get(name)


def list_members(registry: Dict[str, CrewMember]) -> List[CrewMember]:
    return list(registry.values())
