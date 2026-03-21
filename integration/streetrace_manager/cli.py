from __future__ import annotations

import argparse

from . import crew_management, inventory, mission_planning, race_management, registration
from .models import Car
from .system import StreetRaceManager


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="streetrace", description="StreetRace Manager")
    sub = p.add_subparsers(dest="cmd", required=True)

    reg = sub.add_parser("register", help="Register a new crew member")
    reg.add_argument("name")
    reg.add_argument("--role", default=None)

    role = sub.add_parser("role", help="Assign a role to a crew member")
    role.add_argument("name")
    role.add_argument("role")

    skill = sub.add_parser("skill", help="Set a crew member skill")
    skill.add_argument("name")
    skill.add_argument("skill")
    skill.add_argument("level", type=int)

    car = sub.add_parser("add-car", help="Add a car to inventory")
    car.add_argument("car_id")
    car.add_argument("model")
    car.add_argument("--condition", type=int, default=100)

    cash = sub.add_parser("cash", help="Add cash to inventory")
    cash.add_argument("amount", type=int)

    make_race = sub.add_parser("create-race", help="Create a race")
    make_race.add_argument("race_id")
    make_race.add_argument("location")
    make_race.add_argument("prize_money", type=int)

    enter = sub.add_parser("enter-race", help="Enter a race")
    enter.add_argument("race_id")
    enter.add_argument("driver_name")
    enter.add_argument("car_id")

    run = sub.add_parser("run-race", help="Run a race")
    run.add_argument("race_id")

    mk_mission = sub.add_parser("create-mission", help="Create a mission")
    mk_mission.add_argument("mission_id")
    mk_mission.add_argument("mission_type")

    start = sub.add_parser("start-mission", help="Start a mission")
    start.add_argument("mission_id")

    return p


def main(argv: list[str] | None = None) -> int:
    mgr = StreetRaceManager()
    args = build_parser().parse_args(argv)

    if args.cmd == "register":
        member = registration.register_member(mgr.crew_registry, args.name, role=args.role)
        mgr.audit(f"registered {member.name}")
        print(f"Registered: {member.name}")
        return 0

    if args.cmd == "role":
        crew_management.assign_role(mgr.crew_registry, args.name, args.role)
        mgr.audit(f"role {args.role} -> {args.name}")
        print("Role assigned")
        return 0

    if args.cmd == "skill":
        crew_management.set_skill(mgr.crew_registry, args.name, args.skill, args.level)
        mgr.audit(f"skill {args.skill}={args.level} -> {args.name}")
        print("Skill updated")
        return 0

    if args.cmd == "add-car":
        inventory.add_car(mgr.inventory, Car(car_id=args.car_id, model=args.model, condition=args.condition))
        mgr.audit(f"car added {args.car_id}")
        print("Car added")
        return 0

    if args.cmd == "cash":
        inventory.add_cash(mgr.inventory, args.amount)
        mgr.audit(f"cash added {args.amount}")
        print(f"Cash: {inventory.get_cash(mgr.inventory)}")
        return 0

    if args.cmd == "create-race":
        race_management.create_race(mgr.races, args.race_id, args.location, args.prize_money)
        mgr.audit(f"race created {args.race_id}")
        print("Race created")
        return 0

    if args.cmd == "enter-race":
        race_management.enter_race(mgr.crew_registry, mgr.inventory, mgr.races, args.race_id, args.driver_name, args.car_id)
        mgr.audit(f"race entry {args.race_id} driver={args.driver_name} car={args.car_id}")
        print("Race entry saved")
        return 0

    if args.cmd == "run-race":
        res = race_management.run_race(mgr.crew_registry, mgr.inventory, mgr.races, mgr.results, mgr.rankings, args.race_id)
        mgr.audit(f"race ran {args.race_id} outcome={res.outcome}")
        print(f"Outcome: {res.outcome}")
        return 0

    if args.cmd == "create-mission":
        mission_planning.create_mission(mgr.missions, args.mission_id, args.mission_type)
        mgr.audit(f"mission created {args.mission_id}")
        print("Mission created")
        return 0

    if args.cmd == "start-mission":
        mission = mgr.missions.get(args.mission_id)
        if mission is None:
            raise SystemExit("Mission not found")
        mission_planning.start_mission(mgr.crew_registry, mission)
        mgr.audit(f"mission started {args.mission_id}")
        print("Mission started")
        return 0

    raise SystemExit("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
