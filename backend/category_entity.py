"""Shared category domain state. Display remains in React Boundaries."""
from dataclasses import dataclass, asdict
from backend.models import AppError
from backend.validation import clean, check_object


@dataclass(frozen=True)
class IDPCategory:
    categoryId: str
    name: str
    description: str
    status: str
    createdAt: str | None
    updatedAt: str | None
    deletedAt: str | None

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def validate(data):
        check_object(data, {'name', 'description'})
        errors = {}
        name, description = clean(data.get('name')), clean(data.get('description', ''))
        if not name or len(name) > 100:
            errors['name'] = 'Enter a category name of 1-100 characters.'
        if not isinstance(data.get('description', ''), str) or len(description) > 2000:
            errors['description'] = 'Enter a description of at most 2000 characters.'
        if errors:
            raise AppError('VALIDATION', 'Please correct the category fields.', errors)
        return name, description


# Alias matching CSIT314 and CSIT314_Consistency_Fixes diagram notations
IDPC = IDPCategory
