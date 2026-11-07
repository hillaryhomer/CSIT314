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

    @staticmethod
    def Record(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def countByProject(project_ids=None, store=None) -> int:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio US37."""
        if store is not None and project_ids:
            return store.counts_by_project(project_ids)
        return 0


# Alias matching CSIT314 and CSIT314_Consistency_Fixes diagram notations
PV = ProjectView
