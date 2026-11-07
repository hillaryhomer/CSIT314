"""A unique customer/project relationship, without persistence or display logic."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Favourite:
    customer_account_id: str
    project_id: str
    created_at: str

    @property
    def customerId(self) -> str:
        return self.customer_account_id

    @property
    def designerId(self) -> str:
        return self.customer_account_id

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def savedAt(self) -> str:
        return self.created_at

    @staticmethod
    def Add(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio US32."""
        return True

    @staticmethod
    def exists(customer_id=None, project_id=None, store=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio US32."""
        if store is not None and customer_id and project_id:
            return store.exists(customer_id, project_id)
        return False

    @staticmethod
    def Search(x=None) -> list:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return []

    @staticmethod
    def countByProject(project_ids=None, store=None) -> int:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio US38."""
        if store is not None and project_ids:
            return store.count_by_project(project_ids)
        return 0


# Alias matching CSIT314 and CSIT314_Consistency_Fixes diagram notation
FAV = Favourite
