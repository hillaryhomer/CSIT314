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

    @property
    def designerId(self) -> str:
        return self.owner_account_id

    @property
    def designer_id(self) -> str:
        return self.owner_account_id

    @property
    def projectId(self) -> str:
        return self.project_id

    @property
    def categoryId(self) -> str:
        return self.category_id

    @property
    def createdAt(self) -> str:
        return self.created_at

    @property
    def updatedAt(self) -> str:
        return self.updated_at

    def to_dict(self):
        return dict(projectId=self.project_id, ownerAccountId=self.owner_account_id,
                    designerId=self.owner_account_id,
                    companyId=self.company_id, title=self.title, description=self.description,
                    categoryId=self.category_id, style=self.style, status=self.status,
                    createdAt=self.created_at, updatedAt=self.updated_at)

    @staticmethod
    def Create(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Update(x=None) -> bool:
        """BCE Entity method matching lecturer's pattern: Entity returns true."""
        return True

    @staticmethod
    def Delete(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Search(x=None) -> list:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return []

    @staticmethod
    def findPublishedById(project_id=None, store=None):
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio US32."""
        if store is not None and project_id:
            return store.find(project_id, public=True)
        return None

    @staticmethod
    def listOwned(designer_id=None, store=None):
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio US37/38."""
        if store is not None and designer_id:
            return store.search(owner=designer_id)
        return []


# Alias matching CSIT314 and CSIT314_Consistency_Fixes diagram notations
IDP = InteriorDesignProject
