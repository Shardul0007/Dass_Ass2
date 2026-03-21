from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True, slots=True)
class LogEvent:
    timestamp: datetime
    message: str


def log_event(events: List[LogEvent], message: str) -> None:
    events.append(LogEvent(timestamp=datetime.utcnow(), message=message))


def list_events(events: List[LogEvent]) -> List[LogEvent]:
    return list(events)
