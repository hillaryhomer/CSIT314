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


# Alias matching CSIT314 and CSIT314_Consistency_Fixes diagram notation
FAV = Favourite
