"""Project state only; no persistence or display methods on entities."""
from dataclasses import dataclass


@dataclass
class InteriorDesignProject:
    project_id: str
    owner_account_id: str
    company_id: str | None
    title: str
    description: str
    category_id: str
    style: str
    status: str
    created_at: str
    updated_at: str

    def to_dict(self):
        return dict(projectId=self.project_id, ownerAccountId=self.owner_account_id,
                    companyId=self.company_id, title=self.title, description=self.description,
                    categoryId=self.category_id, style=self.style, status=self.status,
                    createdAt=self.created_at, updatedAt=self.updated_at)
