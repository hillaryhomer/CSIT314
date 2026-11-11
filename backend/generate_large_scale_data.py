"""Large-scale test data generation script for CSIT314 Interior Designer Platform.
Generates 100+ valid records for every entity in the database to verify system scalability,
indexing, search performance, and data integrity under volume.
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import connect_database, initialize_database, Repository
from backend.models import UserAccount, UserProfile
from backend.validation import hash_password, normalize, clean

# Fixed reusable hash for bulk generation speed (Bcrypt rounds=12 is computationally heavy)
SAMPLE_PASSWORD = "Password123!"
BULK_PASSWORD_HASH = hash_password(SAMPLE_PASSWORD)

DESIGN_STYLES = [
    "Modern", "Minimalist", "Scandinavian", "Industrial", "Japandi",
    "Contemporary", "Mid-Century Modern", "Bohemian", "Art Deco", "Rustic",
    "Traditional", "Transitional", "Coastal", "Mediterranean", "Eclectic",
    "Bauhaus", "Brutalist", "Zen", "Tropical", "Victorian"
]

ROOM_TYPES = [
    "Living Room", "Master Bedroom", "Kitchen", "Dining Area", "Home Office",
    "Penthouse Suite", "Studio Apartment", "Villa", "Boutique Cafe",
    "Executive Boardroom", "Co-Working Space", "Balcony Garden", "Bathroom",
    "Walk-In Wardrobe", "Library", "Foyer", "Sunroom", "Loft", "Terrace", "Courtyard"
]

CITIES = [
    "Singapore", "Kuala Lumpur", "Jakarta", "Sydney", "Melbourne",
    "Tokyo", "London", "New York", "San Francisco", "Vancouver"
]

def generate_large_scale_data(database_path: str = "data/large_scale.sqlite", min_count: int = 100):
    print(f"Initializing database at: {database_path}")
    initialize_database(database_path)
    connection = connect_database(database_path)
    repository = Repository(connection)

    now = datetime.now(timezone.utc)
    base_time = now - timedelta(days=90)

    try:
        with repository.transaction():
            print(f"\n[1/7] Generating {min_count}+ User Profiles...")
            roles = ["admin", "designer", "customer", "manager"]
            role_permissions = {
                "admin": ["profiles:read", "profiles:write", "accounts:read", "accounts:write"],
                "designer": ["projects:manage"],
                "customer": ["projects:discover"],
                "manager": ["reports:read", "categories:manage"]
            }
            profiles = []
            for i in range(1, min_count + 15):
                role = roles[(i - 1) % len(roles)]
                profile_id = f"UP-PERF-{i:04d}"
                name = f"Profile Tier {i:03d} {role.capitalize()}"
                perms = role_permissions[role]
                status = "Active" if i % 10 != 0 else "Suspended"
                profile = UserProfile(profile_id, name, role, perms, status)
                repository.create_profile(profile)
                profiles.append(profile)

            print(f"[2/7] Generating {min_count}+ User Accounts...")
            accounts = []
            designer_accounts = []
            customer_accounts = []
            for i in range(1, min_count + 30):
                assigned_profile = profiles[(i - 1) % len(profiles)]
                account_id = f"UA-PERF-{i:04d}"
                username = f"user.{assigned_profile.role}.{i:04d}"
                email = f"user{i:04d}.{assigned_profile.role}@benchmark.test"
                status = "Active" if i % 15 != 0 else "Suspended"
                acc = UserAccount(
                    account_id=account_id,
                    username=username,
                    email=email,
                    password_hash=BULK_PASSWORD_HASH,
                    profile_id=assigned_profile.profile_id,
                    status=status
                )
                repository.create_account(acc)
                accounts.append(acc)
                if assigned_profile.role == "designer":
                    designer_accounts.append(acc)
                elif assigned_profile.role == "customer":
                    customer_accounts.append(acc)

            # Ensure we have at least min_count designers and customers for downstream entities
            extra_idx = len(accounts) + 1
            while len(designer_accounts) < min_count:
                prof = [p for p in profiles if p.role == "designer"][0]
                account_id = f"UA-PERF-{extra_idx:04d}"
                username = f"designer.extra.{extra_idx:04d}"
                email = f"designer{extra_idx:04d}@benchmark.test"
                acc = UserAccount(account_id, username, email, BULK_PASSWORD_HASH, prof.profile_id, "Active")
                repository.create_account(acc)
                accounts.append(acc)
                designer_accounts.append(acc)
                extra_idx += 1

            while len(customer_accounts) < min_count:
                prof = [p for p in profiles if p.role == "customer"][0]
                account_id = f"UA-PERF-{extra_idx:04d}"
                username = f"customer.extra.{extra_idx:04d}"
                email = f"customer{extra_idx:04d}@benchmark.test"
                acc = UserAccount(account_id, username, email, BULK_PASSWORD_HASH, prof.profile_id, "Active")
                repository.create_account(acc)
                accounts.append(acc)
                customer_accounts.append(acc)
                extra_idx += 1

            print(f"[3/7] Generating {min_count}+ Companies...")
            companies = []
            for idx, designer in enumerate(designer_accounts[:min_count + 10], 1):
                company_id = f"CO-PERF-{idx:04d}"
                city = CITIES[(idx - 1) % len(CITIES)]
                name = clean(f"Studio {idx:03d} Architectural Design")
                address = clean(f"{idx * 12} Design Avenue, Level {idx % 20 + 1}, {city}")
                contact = f"contact@studio{idx:03d}.design"
                desc = clean(f"Award-winning boutique interior architectural firm based in {city}. Specializing in bespoke spaces.")
                connection.execute(
                    "INSERT INTO companies (company_id, owner_id, name, reg_number, address, contact, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (company_id, designer.account_id, name, f"REG-{idx:06d}", address, contact, desc)
                )
                companies.append({"companyId": company_id, "ownerId": designer.account_id})

            print(f"[4/7] Generating {min_count}+ IDP Categories...")
            categories = []
            for i in range(1, min_count + 10):
                cat_id = f"CAT-PERF-{i:04d}"
                room = ROOM_TYPES[(i - 1) % len(ROOM_TYPES)]
                style = DESIGN_STYLES[(i - 1) % len(DESIGN_STYLES)]
                cat_name = clean(f"Concept {i:03d} {style} {room}")
                cat_desc = clean(f"Design specifications and architectural solutions for {style.lower()} {room.lower()} environments.")
                cat_status = "Active" if i % 12 != 0 else "Suspended"
                ts = (base_time + timedelta(hours=i * 2)).isoformat()
                connection.execute(
                    "INSERT INTO project_categories (category_id, name, description, status, name_key, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cat_id, cat_name, cat_desc, cat_status, normalize(cat_name), ts, ts)
                )
                categories.append(cat_id)

            print(f"[5/7] Generating {min_count}+ Interior Design Projects (Current & Past)...")
            projects = []
            for i in range(1, min_count + 25):
                proj_id = f"PROJ-PERF-{i:04d}"
                designer = designer_accounts[(i - 1) % len(designer_accounts)]
                comp = [c for c in companies if c["ownerId"] == designer.account_id]
                comp_id = comp[0]["companyId"] if comp else None
                cat_id = categories[(i - 1) % len(categories)]
                style = DESIGN_STYLES[(i - 1) % len(DESIGN_STYLES)]
                room = ROOM_TYPES[(i - 1) % len(ROOM_TYPES)]
                status = "Current" if i % 2 == 1 else "Past"
                title = clean(f"Project {i:03d} {style} {room} Showcase")
                desc = clean(f"Comprehensive renovation of a {style.lower()} {room.lower()} featuring custom cabinetry, integrated ambient lighting, and sustainable finishes.")
                created_ts = (base_time + timedelta(days=(i % 60), hours=(i % 24))).isoformat()
                updated_ts = created_ts
                connection.execute(
                    "INSERT INTO interior_design_projects (project_id, owner_account_id, company_id, title, description, category_id, style, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (proj_id, designer.account_id, comp_id, title, desc, cat_id, style, status, created_ts, updated_ts)
                )
                projects.append(proj_id)

            print(f"[6/7] Generating {min_count}+ Customer Favourites...")
            favourites = set()
            fav_count = min_count + 35
            while len(favourites) < fav_count:
                cust = random.choice(customer_accounts)
                proj = random.choice(projects)
                pair = (cust.account_id, proj)
                if pair not in favourites:
                    favourites.add(pair)
                    fav_time = (now - timedelta(days=random.randint(1, 30), minutes=random.randint(1, 1440))).isoformat()
                    connection.execute(
                        "INSERT INTO favourites (customer_account_id, project_id, created_at) VALUES (?, ?, ?)",
                        (cust.account_id, proj, fav_time)
                    )

            print(f"[7/7] Generating {min_count}+ Project Views (Analytics Events)...")
            view_count = min_count + 50
            for i in range(1, view_count + 1):
                proj = random.choice(projects)
                event_id = f"view-event-{i:05d}-{uuid4().hex[:12]}"
                view_time = (now - timedelta(days=random.randint(0, 45), minutes=random.randint(1, 1440))).isoformat()
                connection.execute(
                    "INSERT INTO project_views (project_id, event_id, occurred_at) VALUES (?, ?, ?)",
                    (proj, event_id, view_time)
                )

        print("\nVerifying database foreign keys and integrity...")
        fk_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_violations:
            raise RuntimeError(f"Foreign key violations detected: {fk_violations}")

        # Summary of generated records per entity
        entities = [
            ("User Profile (UP)", "user_profiles"),
            ("User Account (UA)", "user_accounts"),
            ("Company Information (CI)", "companies"),
            ("IDP Category (IDPC)", "project_categories"),
            ("Interior Design Project (IDP)", "interior_design_projects"),
            ("Favourite List (FAV)", "favourites"),
            ("Project View / Activity (PV)", "project_views"),
            ("Report Event (Report Log)", "report_events"),
        ]

        print("\n" + "=" * 65)
        print(f"{'Entity Name':<30} | {'Table Name':<25} | {'Count':<7}")
        print("=" * 65)
        all_passed = True
        for entity_name, table_name in entities:
            count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            status = "✓ PASS (>= 100)" if count >= min_count else "✗ FAIL"
            print(f"{entity_name:<30} | {table_name:<25} | {count:<7} {status}")
            if count < min_count:
                all_passed = False
        print("=" * 65)

        if all_passed:
            print("\nSUCCESS: All entities successfully populated with 100+ records!")
        else:
            print("\nWARNING: Some entities have fewer than 100 records.")

    finally:
        connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 100+ records per entity for CSIT314")
    parser.add_argument("--database", default="data/large_scale.sqlite", help="Path to SQLite database file")
    parser.add_argument("--count", type=int, default=100, help="Minimum record count per entity (default: 100)")
    args = parser.parse_args()
    generate_large_scale_data(args.database, args.count)

