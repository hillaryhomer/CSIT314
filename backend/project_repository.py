"""One project/category source for designer, customer and future analytics adapters."""
from backend.project_entity import InteriorDesignProject
from backend.validation import normalize


class ProjectRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    def categories(self):
        return [dict(categoryId=r['category_id'], name=r['name'], description=r['description'], status=r['status'])
                for r in self.connection.execute('SELECT * FROM project_categories ORDER BY name')]

    def category(self, category_id):
        return self.connection.execute('SELECT * FROM project_categories WHERE category_id=?', (category_id,)).fetchone()

    def company_id(self, owner):
        row = self.connection.execute('SELECT company_id FROM companies WHERE owner_id=?', (owner,)).fetchone()
        return row[0] if row else None

    def serialize(self, row):
        if row is None:
            return None
        keys = InteriorDesignProject.__dataclass_fields__
        result = InteriorDesignProject(**{k: row[k] for k in keys}).to_dict()
        result.update(categoryName=row['category_name'], categoryStatus=row['category_status'],
                      companyName=row['company_name'], designerName=row['username'])
        result['images'] = [dict(imageId=r['image_id'], url='/api/project-images/' + r['image_id'])
                            for r in self.connection.execute('SELECT image_id FROM project_images WHERE project_id=? ORDER BY position', (row['project_id'],))]
        return result

    SELECT = '''SELECT p.*, c.name AS category_name, c.status AS category_status,
                       co.name AS company_name, a.username
                FROM interior_design_projects p
                JOIN project_categories c ON c.category_id=p.category_id
                JOIN user_accounts a ON a.account_id=p.owner_account_id
                JOIN user_profiles up ON up.profile_id=a.profile_id
                LEFT JOIN companies co ON co.company_id=p.company_id'''
    VISIBLE = "a.status='Active' AND up.status='Active' AND up.role='designer' AND EXISTS (SELECT 1 FROM json_each(up.permissions_json) permission WHERE permission.value='projects:manage')"

    def find(self, project_id, owner=None, status=None, public=False):
        clauses, args = ['p.project_id=?'], [project_id]
        if owner is not None:
            clauses.append('p.owner_account_id=?'); args.append(owner)
        if status is not None:
            clauses.append('p.status=?'); args.append(status)
        if public:
            clauses.append(self.VISIBLE)
        return self.serialize(self.connection.execute(self.SELECT + ' WHERE ' + ' AND '.join(clauses), args).fetchone())

    def search(self, status=None, owner=None, query='', category_id='', public=False):
        clauses, args = ['1=1'], []
        for column, value in [('p.status', status), ('p.owner_account_id', owner), ('p.category_id', category_id or None)]:
            if value is not None:
                clauses.append(column + '=?'); args.append(value)
        if public:
            clauses.append(self.VISIBLE)
        rows = self.connection.execute(self.SELECT + ' WHERE ' + ' AND '.join(clauses) + ' ORDER BY p.created_at DESC, p.project_id', args).fetchall()
        keyword = normalize(query)
        return [self.serialize(r) for r in rows if keyword in normalize(' '.join(r[k] or '' for k in ('title','description','style','category_name','company_name')))]

    def create(self, project):
        self.connection.execute('INSERT INTO interior_design_projects VALUES (?,?,?,?,?,?,?,?,?,?)',
            (project.project_id, project.owner_account_id, project.company_id, project.title, project.description,
             project.category_id, project.style, project.status, project.created_at, project.updated_at))

    def update(self, project, owner):
        self.connection.execute('UPDATE interior_design_projects SET title=?,description=?,category_id=?,style=?,updated_at=? WHERE project_id=? AND owner_account_id=?',
            (project['title'], project['description'], project['categoryId'], project['style'], project['updatedAt'], project['projectId'], owner))

    def image_content(self, image_id):
        return self.connection.execute('SELECT * FROM project_images WHERE image_id=?', (image_id,)).fetchone()

    def replace_images(self, project_id, images):
        # All images belong exclusively to this project; retained IDs are checked by the controller.
        self.connection.execute('DELETE FROM project_images WHERE project_id=?', (project_id,))
        self.connection.executemany('INSERT INTO project_images VALUES (?,?,?,?,?)',
            [(image['imageId'], project_id, position, image['mimeType'], image['content']) for position, image in enumerate(images)])

    def delete(self, project_id, owner):
        # Only images cascade. Account/company/category records are never deleted.
        self.connection.execute('DELETE FROM interior_design_projects WHERE project_id=? AND owner_account_id=?', (project_id, owner))
