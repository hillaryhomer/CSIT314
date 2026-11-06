"""Reproducible synthetic demo, restricted to an explicitly named new database."""
import argparse
import os
from pathlib import Path
from backend.database import initialize_database, connect_database, Repository
from backend.models import UserAccount, UserProfile
from backend.validation import hash_password
from backend.member2 import CompanyController
from backend.project_entity import InteriorDesignProject
from backend.project_repository import ProjectRepository
from backend.customer_controllers import AddFavouriteController
from backend.activity_controllers import RecordIDPViewController

PASSWORD = 'Synthetic demo password 5'


def generate(filename, environment, seed=5):
    path = Path(filename).resolve()
    if environment not in ('development', 'test') or os.getenv('APP_ENV') == 'production' or os.getenv('NODE_ENV') == 'production':
        raise ValueError('Seed requires development/test environment.')
    if path.exists() or path == Path('data/member1.sqlite').resolve():
        raise ValueError('Choose a NEW dedicated demo/test database; existing files are never reset.')
    initialize_database(str(path))
    connection = connect_database(str(path))
    try:
        repository = Repository(connection)
        hashed = hash_password(PASSWORD)
        for role, permission in [('designer', 'projects:manage'), ('customer', 'projects:discover')]:
            repository.create_profile(UserProfile(role, 'Synthetic ' + role, role, [permission]))
            for index in ((1, 2, 3) if role == 'designer' else (1, 2)):
                name = f'{role}{index}'
                repository.create_account(UserAccount(name, name, name + '@example.test', hashed, role))
        now = '2026-01-01T00:00:00+00:00'
        for index in (1, 2):
            owner = f'designer{index}'
            CompanyController(repository, owner).create({'name': f'Synthetic Studio {index}', 'address': 'Demo Street', 'contact': 'studio@example.test'})
            for status in ('Current', 'Past'):
                project_id = f'DEMO-{seed}-{index}-{status}'
                with repository.transaction():
                    ProjectRepository(repository).create(InteriorDesignProject(project_id, owner,
                        ProjectRepository(repository).company_id(owner), f'Demo {status} {index}',
                        'Synthetic reproducible interiors', 'CAT001', 'Modern', status, now, now))
        project_id = f'DEMO-{seed}-1-Current'
        for customer in ('customer1', 'customer2'):
            AddFavouriteController(repository, customer).execute({'projectId': project_id})
        for index in range(3):
            RecordIDPViewController(repository, 'customer1').execute(project_id, {'eventId': f'demo-event-{seed:08d}-{index:08d}'})
        return project_id
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--environment', required=True, choices=['development', 'test'])
    parser.add_argument('--seed', type=int, default=5)
    args = parser.parse_args()
    project = generate(args.database, args.environment, args.seed)
    print(f'{project}: 3 views, 2 shortlists; other projects: 0/0. designer3 has no projects.')
    print(f'Logins: designer1/designer2/designer3/customer1/customer2; synthetic password: {PASSWORD}')
