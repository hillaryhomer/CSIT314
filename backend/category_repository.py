"""Category persistence uses the same table as designer projects and discovery."""
from backend.category_entity import IDPCategory
from backend.validation import normalize


class CategoryRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    @staticmethod
    def entity(row):
        return IDPCategory(row['category_id'], row['name'], row['description'], row['status'],
                           row['created_at'], row['updated_at'], row['deleted_at']) if row else None

    def find(self, category_id):
        return self.entity(self.connection.execute(
            'SELECT * FROM project_categories WHERE category_id=? AND deleted_at IS NULL', (category_id,)).fetchone())

    def search(self, query):
        return [self.entity(row).to_dict() for row in self.connection.execute('''
            SELECT * FROM project_categories WHERE deleted_at IS NULL
            AND instr(normalize(name || ' ' || description),?)>0 ORDER BY name_key,category_id
        ''', (normalize(query),))]

    def duplicate(self, name, excluding=None):
        return self.connection.execute('SELECT 1 FROM project_categories WHERE name_key=? AND category_id<>?',
                                       (normalize(name), excluding or '')).fetchone() is not None

    def save(self, category, new=False):
        if new:
            self.connection.execute('''INSERT INTO project_categories
                (category_id,name,description,status,name_key,created_at,updated_at,deleted_at) VALUES (?,?,?,?,?,?,?,?)''',
                (category.categoryId, category.name, category.description, category.status, normalize(category.name),
                 category.createdAt, category.updatedAt, category.deletedAt))
        else:
            self.connection.execute('''UPDATE project_categories SET name=?,name_key=?,description=?,status=?,
                updated_at=?,deleted_at=? WHERE category_id=?''',
                (category.name, normalize(category.name), category.description, category.status,
                 category.updatedAt, category.deletedAt, category.categoryId))
