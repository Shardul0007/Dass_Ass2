# StreetRace Manager (Integration Testing)

Command-line system for managing underground street races, crew members, vehicles, inventory, results, and missions.

## Required modules

- **Registration module**: `streetrace_manager/registration.py`
- **Crew Management module**: `streetrace_manager/crew_management.py`
- **Inventory module**: `streetrace_manager/inventory.py`
- **Race Management module**: `streetrace_manager/race_management.py`
- **Results module**: `streetrace_manager/results.py`
- **Mission Planning module**: `streetrace_manager/mission_planning.py`

## CLI

Run from the repo root:

- `python -m integration.streetrace_manager register "Mia" --role driver`
- `python -m integration.streetrace_manager add-car CAR1 "Nissan Skyline" --condition 100`
- `python -m integration.streetrace_manager create-race R1 "Docks" 500`

(Integration tests primarily call the module functions directly.)
