"""Anonymous event state: no customer identity or display responsibilities."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectView:
    project_id: str
    event_id: str
    occurred_at: str

    @property
    def viewId(self) -> str:
        return self.event_id

    @property
    def view_id(self) -> str:
        return self.event_id

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def viewedAt(self) -> str:
        return self.occurred_at

    @property
    def viewed_at(self) -> str:
        return self.occurred_at


# Alias matching CSIT314 and CSIT314_Consistency_Fixes diagram notations
PV = ProjectView
