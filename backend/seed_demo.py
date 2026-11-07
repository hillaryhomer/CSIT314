"""Seed sample accounts and data for all 4 roles into data/member1.sqlite."""
import os
import sqlite3
from datetime import datetime, timezone
from backend.database import connect_database, initialize_database, Repository
from backend.models import UserAccount, UserProfile
from backend.validation import hash_password
from backend.category_repository import CategoryRepository
from backend.category_entity import IDPCategory
from backend.project_entity import InteriorDesignProject
from backend.project_repository import ProjectRepository
from backend.member2 import CompanyController
from backend.member2_repository import Member2Repository
from backend.customer_controllers import AddFavouriteController
from backend.activity_controllers import RecordIDPViewController

PASSWORD = "123456"

def seed_demo_accounts(database_path: str = "data/member1.sqlite"):
    initialize_database(database_path)
    connection = connect_database(database_path)
    try:
        repo = Repository(connection)
        now = datetime.now(timezone.utc).isoformat()
        hashed = hash_password(PASSWORD)

        # 1. Ensure profiles exist
        profiles = [
            UserProfile("profile-designer", "Interior Designer", "designer", ["projects:manage"]),
            UserProfile("profile-customer", "Customer", "customer", ["projects:discover"]),
            UserProfile("profile-manager", "Platform Manager", "manager", ["reports:read", "categories:manage"]),
        ]
        with repo.transaction():
            for p in profiles:
                if not repo.find_profile(p.profile_id):
                    repo.create_profile(p)

            # 2. Ensure accounts exist
            demo_accounts = [
                ("designer", "designer@example.com", "profile-designer"),
                ("customer", "customer@example.com", "profile-customer"),
                ("manager", "manager@example.com", "profile-manager"),
            ]
            for username, email, prof_id in demo_accounts:
                if not repo.account_with_username(username):
                    repo.create_account(UserAccount(
                        account_id=f"UA-demo-{username}",
                        username=username,
                        email=email,
                        password_hash=hashed,
                        profile_id=prof_id,
                        status="Active",
                    ))

        # 3. Ensure categories exist
        cat_repo = CategoryRepository(repo)
        demo_cats = [
            ("CAT-001", "Modern Residential", "Modern home, apartment, and condo design."),
            ("CAT-002", "Minimalist Living", "Clean, functional minimalist spaces."),
            ("CAT-003", "Commercial Office", "Workplaces, studios, and corporate interiors."),
        ]
        with repo.transaction():
            for cat_id, name, desc in demo_cats:
                if not cat_repo.find(cat_id):
                    cat_repo.save(IDPCategory(cat_id, name, desc, "Active", now, now, None), new=True)

        # 4. Ensure Company exists for designer
        designer_id = repo.account_with_username("designer").account_id
        m2_repo = Member2Repository(repo)
        if not m2_repo.company(designer_id):
            CompanyController(repo, designer_id).create({
                "name": "Atelier Design Studio",
                "address": "12 Marina Boulevard #08-01",
                "contact": "contact@atelier.design",
                "description": "Specializing in refined residential and commercial interior environments.",
            })

        # 5. Ensure Projects exist for designer
        proj_repo = ProjectRepository(repo)
        company = m2_repo.company(designer_id)
        comp_id = company["companyId"] if company else None

        if not proj_repo.search(owner=designer_id):
            with repo.transaction():
                proj_repo.create(InteriorDesignProject(
                    project_id="PROJ-001",
                    owner_account_id=designer_id,
                    company_id=comp_id,
                    title="Serene Skyline Penthouse",
                    description="A calm, high-floor urban residence featuring custom woodwork and panoramic natural light.",
                    category_id="CAT-001",
                    style="Minimalist",
                    status="Current",
                    created_at=now,
                    updated_at=now,
                ))
                proj_repo.create(InteriorDesignProject(
                    project_id="PROJ-002",
                    owner_account_id=designer_id,
                    company_id=comp_id,
                    title="Nordic Heritage Loft",
                    description="Completed renovation blending Scandinavian warmth with raw exposed architectural elements.",
                    category_id="CAT-002",
                    style="Scandinavian",
                    status="Past",
                    created_at=now,
                    updated_at=now,
                ))

        # 6. Seed a view and favourite from customer for analytics demo
        customer_id = repo.account_with_username("customer").account_id
        try:
            AddFavouriteController(repo, customer_id).execute({"projectId": "PROJ-001"})
        except Exception:
            pass
        try:
            RecordIDPViewController(repo, customer_id).execute("PROJ-001", {"eventId": f"view-{customer_id}-PROJ-001"})
            RecordIDPViewController(repo, customer_id).execute("PROJ-002", {"eventId": f"view-{customer_id}-PROJ-002"})
        except Exception:
            pass

        print("Demo data seeded successfully:")
        print("  - Interior Designer : username 'designer' | password '123456'")
        print("  - Customer          : username 'customer' | password '123456'")
        print("  - Platform Manager  : username 'manager'  | password '123456'")
        print("  - User Admin        : your existing admin '123456'")
    finally:
        connection.close()

if __name__ == "__main__":
    seed_demo_accounts()
