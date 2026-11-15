"""Script to seed rich, realistic demo data into data/atelier_match.sqlite
specifically designed for live lecturer presentations across all 4 system roles.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import (
    Repository, CategoryRepository, ProjectRepository,
    CompanyRepository, FavouriteRepository, ActivityRepository,
    connect_database, initialize_database
)
from backend.models import (
    UserAccount, UserProfile, IDPCategory,
    InteriorDesignProject, ProjectImage, Favourite, ProjectView
)
from backend.validation import hash_password, normalize

PASSWORD = "123456"

# Load real interior photo bytes for realistic presentation
IMG_DIR = PROJECT_ROOT / "public" / "images"
def get_photo_bytes(filename: str) -> bytes:
    p = IMG_DIR / filename
    return p.read_bytes() if p.exists() else b""

def seed_demo_presentation(database_path: str = "data/atelier_match.sqlite"):
    print(f"Seeding rich presentation demo data into: {database_path}")
    initialize_database(database_path)
    connection = connect_database(database_path)
    repo = Repository(connection)
    now = datetime.now(timezone.utc)
    hashed_pw = hash_password(PASSWORD)

    try:
        with repo.transaction():
            # 1. Profiles
            profiles = [
                UserProfile("dev-profile-admin", "User Admin", "admin",
                            ["profiles:read", "profiles:write", "accounts:read", "accounts:write"]),
                UserProfile("profile-designer", "Interior Designer", "designer", ["projects:manage"]),
                UserProfile("profile-customer", "Customer", "customer", ["projects:discover"]),
                UserProfile("profile-manager", "Platform Manager", "manager", ["reports:read", "categories:manage"]),
            ]
            for p in profiles:
                if not repo.profile_with_id(p.profile_id) and not repo.profile_with_name(p.name):
                    repo.create_profile(p)

            # Ensure profile IDs
            p_admin = repo.profile_with_name("User Admin").profile_id
            p_designer = repo.profile_with_name("Interior Designer").profile_id
            p_customer = repo.profile_with_name("Customer").profile_id
            p_manager = repo.profile_with_name("Platform Manager").profile_id

            # 2. User Accounts
            accounts_data = [
                ("dev-admin", "dev.admin", "dev.admin@example.test", p_admin, "Active"),
                ("UA-demo-designer", "designer", "designer@example.com", p_designer, "Active"),
                ("UA-demo-designer-2", "designer.clara", "clara@forma-studio.test", p_designer, "Active"),
                ("UA-demo-customer", "customer", "customer@example.com", p_customer, "Active"),
                ("UA-demo-customer-2", "customer.sarah", "sarah@homestyle.test", p_customer, "Active"),
                ("UA-demo-manager", "manager", "manager@example.com", p_manager, "Active"),
                ("UA-demo-suspended", "suspended.user", "suspended@example.test", p_customer, "Suspended"),
            ]
            for acc_id, uname, email, prof_id, status in accounts_data:
                existing = repo.account_with_id(acc_id) or repo.account_with_username(uname)
                if not existing:
                    repo.create_account(UserAccount(
                        account_id=acc_id,
                        username=uname,
                        email=email,
                        password_hash=hashed_pw,
                        profile_id=prof_id,
                        status=status
                    ))

            # 3. Companies / Studios
            co_repo = CompanyRepository(repo)
            companies_data = [
                ("CO-DEMO-01", "UA-demo-designer", "Atelier Luminary Design", "REG-2024-0012A", "12 Marina Boulevard, Marina Bay Financial Centre, Singapore", "contact@atelierluminary.test", "Bespoke high-end residential and luxury commercial design studio."),
                ("CO-DEMO-02", "UA-demo-designer-2", "Studio Forma Interiors", "REG-2023-9988B", "88 Orchard Road, Ngee Ann City Tower B, Singapore", "hello@studioforma.test", "Modern architectural interior design focusing on sustainable Japandi aesthetics."),
            ]
            for co_id, owner_id, name, reg_num, addr, contact, desc in companies_data:
                if not co_repo.company(owner_id):
                    co_repo.create_company(co_id, owner_id, {
                        'name': name,
                        'regNumber': reg_num,
                        'address': addr,
                        'contact': contact,
                        'description': desc
                    })

            # Retrieve actual company IDs
            proj_repo = ProjectRepository(repo)
            co_1 = proj_repo.company_id("UA-demo-designer")
            co_2 = proj_repo.company_id("UA-demo-designer-2")

            # 4. IDP Categories
            cat_repo = CategoryRepository(repo)
            categories_data = [
                ("CAT-001", "Modern Residential", "High-floor urban apartments, penthouses, and bespoke family residences."),
                ("CAT-002", "Minimalist Living", "Functional, clutter-free Japandi and Scandinavian living environments."),
                ("CAT-003", "Commercial & Studio", "Dynamic collaborative workspaces, tech hubs, and corporate executive suites."),
                ("CAT-004", "Luxury Hospitality", "Boutique hotel lounges, high-end cafe concepts, and luxury wellness retreats."),
            ]
            for cat_id, name, desc in categories_data:
                if not cat_repo.find(cat_id):
                    cat_repo.save(IDPCategory(
                        categoryId=cat_id,
                        name=name,
                        description=desc,
                        status="Active",
                        createdAt=(now - timedelta(days=90)).isoformat(),
                        updatedAt=(now - timedelta(days=5)).isoformat(),
                        deletedAt=None
                    ), new=True)

            # 5. Projects
            proj_repo = ProjectRepository(repo)
            projects_data = [
                ("PROJ-001", "UA-demo-designer", co_1, "CAT-001", "Serene Skyline Penthouse", "Current", "Minimalist",
                 "A calm, high-floor urban residence featuring custom natural woodwork, concealed storage, and floor-to-ceiling panoramic light.",
                 get_photo_bytes("interior-1.jpg")),
                ("PROJ-002", "UA-demo-designer", co_1, "CAT-002", "Nordic Heritage Loft", "Past", "Scandinavian",
                 "Award-winning refurbishment of a 1930s heritage shophouse with warm oak textures, exposed rafters, and an indoor courtyard.",
                 get_photo_bytes("interior-2.jpg")),
                ("PROJ-003", "UA-demo-designer", co_1, "CAT-004", "Zenith Coastal Villa", "Current", "Contemporary",
                 "Bespoke tropical retreat blending indoor-outdoor living, travertine stone surfaces, and custom organic furnishings.",
                 get_photo_bytes("interior-3.jpg")),
                ("PROJ-004", "UA-demo-designer-2", co_2, "CAT-003", "Komorebi Tech Hub Studio", "Current", "Industrial",
                 "Biophilic workspace engineered for cross-disciplinary agile teams, acoustic zoning, and integrated smart lighting.",
                 get_photo_bytes("interior-1.jpg")),
                ("PROJ-005", "UA-demo-designer-2", co_2, "CAT-001", "Monochrome Artisan Residence", "Past", "Modern",
                 "Bold architectural contrasts with monolithic concrete kitchen islands, fluted glass partitions, and sculptural lighting.",
                 get_photo_bytes("interior-2.jpg")),
            ]
            for p_id, owner_id, c_id, cat_id, title, status, style, desc, img_bytes in projects_data:
                existing_p = proj_repo.find(p_id, public=False)
                if not existing_p:
                    created_time = (now - timedelta(days=30)).isoformat()
                    proj_repo.save(InteriorDesignProject(
                        project_id=p_id,
                        owner_account_id=owner_id,
                        company_id=c_id,
                        title=title,
                        description=desc,
                        category_id=cat_id,
                        style=style,
                        status=status,
                        created_at=created_time,
                        updated_at=created_time
                    ), [ProjectImage(f"IMG-{p_id}-01", p_id, 0, "image/jpeg", img_bytes)], new=True)
                else:
                    # Ensure real image bytes exist for existing project
                    proj_repo.save(InteriorDesignProject(
                        project_id=existing_p["projectId"],
                        owner_account_id=existing_p["ownerAccountId"],
                        company_id=existing_p["companyId"],
                        title=existing_p["title"],
                        description=existing_p["description"],
                        category_id=existing_p["categoryId"],
                        style=existing_p["style"],
                        status=existing_p["status"],
                        created_at=existing_p["createdAt"],
                        updated_at=existing_p["updatedAt"]
                    ), [ProjectImage(f"IMG-{p_id}-01", p_id, 0, "image/jpeg", img_bytes)], new=False)

            # 6. Customer Favourites
            fav_repo = FavouriteRepository(repo)
            favourites_data = [
                ("UA-demo-customer", "PROJ-001", (now - timedelta(days=5)).isoformat()),
                ("UA-demo-customer", "PROJ-003", (now - timedelta(days=2)).isoformat()),
                ("UA-demo-customer-2", "PROJ-001", (now - timedelta(days=3)).isoformat()),
                ("UA-demo-customer-2", "PROJ-004", (now - timedelta(days=1)).isoformat()),
            ]
            for cust_id, p_id, fav_time in favourites_data:
                if not fav_repo.exists(cust_id, p_id):
                    fav_repo.add(Favourite(cust_id, p_id, fav_time))

            # 7. Project Views / Analytics (Triggers will automatically populate report_events)
            act_repo = ActivityRepository(repo)
            for i in range(1, 35):
                view_time = (now - timedelta(days=i % 14, hours=i % 24)).isoformat()
                p_id = "PROJ-001" if i % 2 == 0 else ("PROJ-003" if i % 3 == 0 else "PROJ-004")
                act_repo.record(ProjectView(p_id, f"demo-view-event-{i:03d}-{uuid4().hex[:8]}", view_time))

        print("SUCCESS: Rich presentation demo data seeded successfully into data/atelier_match.sqlite!")

    finally:
        connection.close()

if __name__ == "__main__":
    seed_demo_presentation()
