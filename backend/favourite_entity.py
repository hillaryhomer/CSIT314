"""A unique customer/project relationship, without persistence or display logic."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Favourite:
    customer_account_id: str
    project_id: str
    created_at: str
