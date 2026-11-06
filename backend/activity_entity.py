"""Anonymous event state: no customer identity or display responsibilities."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectView:
    project_id: str
    event_id: str
    occurred_at: str
