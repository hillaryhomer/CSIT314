-- Unified CSIT314 Schema: Interior Designer Platform (Atelier Match)
-- Contains all tables, indexes, and triggers across Sprints 1, 2, and 3.

-- 1. User Profiles (Sprint 2 - US01..US05)
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 80),
    name_key TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK(role IN ('admin', 'designer', 'customer', 'manager')),
    permissions_json TEXT NOT NULL CHECK(
        json_valid(permissions_json) AND json_type(permissions_json) = 'array'
        AND json_array_length(permissions_json) > 0
    ),
    status TEXT NOT NULL CHECK(status IN ('Active', 'Suspended'))
) STRICT;

-- 2. User Accounts (Sprint 2 - US06..US10)
CREATE TABLE IF NOT EXISTS user_accounts (
    account_id TEXT PRIMARY KEY,
    username TEXT NOT NULL CHECK(length(username) BETWEEN 3 AND 40),
    username_key TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL CHECK(length(email) BETWEEN 3 AND 254),
    email_key TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL CHECK(
        length(password_hash) = 60 AND substr(password_hash, 1, 4) = '$2b$'
    ),
    profile_id TEXT NOT NULL REFERENCES user_profiles(profile_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK(status IN ('Active', 'Suspended'))
) STRICT;

CREATE INDEX IF NOT EXISTS accounts_profile_id ON user_accounts(profile_id);

-- 3. Authentication Sessions (Sprint 1 - US11..US12, US18..US19, US35..US36, US47..US48)
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES user_accounts(account_id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS sessions_account ON auth_sessions(account_id);

-- 4. Company Information (Sprint 2 - US13..US17)
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL UNIQUE REFERENCES user_accounts(account_id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),
    reg_number TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL CHECK(length(trim(address)) BETWEEN 1 AND 500),
    contact TEXT NOT NULL CHECK(length(trim(contact)) BETWEEN 1 AND 254),
    description TEXT NOT NULL DEFAULT '' CHECK(length(description) <= 4000)
) STRICT;

-- 5. IDP Categories (Sprint 3 - US39..US43)
CREATE TABLE IF NOT EXISTS project_categories (
    category_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    name_key TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Suspended')),
    created_at TEXT,
    updated_at TEXT,
    deleted_at TEXT
) STRICT;

CREATE UNIQUE INDEX IF NOT EXISTS category_normalized_name ON project_categories(name_key);

INSERT OR IGNORE INTO project_categories(category_id, name, name_key, description) VALUES
('CAT001', 'Residential', 'residential', 'Homes and apartments'),
('CAT002', 'Commercial', 'commercial', 'Offices and retail'),
('CAT003', 'Hospitality', 'hospitality', 'Cafes, restaurants and boutique hotels');

-- 6. Interior Design Projects (Sprint 2 & 3 - US20..US29, US30..US31)
CREATE TABLE IF NOT EXISTS interior_design_projects (
    project_id TEXT PRIMARY KEY,
    owner_account_id TEXT NOT NULL REFERENCES user_accounts(account_id) ON DELETE RESTRICT,
    company_id TEXT REFERENCES companies(company_id) ON DELETE SET NULL,
    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 160),
    description TEXT NOT NULL CHECK(length(trim(description)) BETWEEN 1 AND 6000),
    category_id TEXT NOT NULL REFERENCES project_categories(category_id) ON DELETE RESTRICT,
    style TEXT NOT NULL CHECK(length(trim(style)) BETWEEN 1 AND 100),
    status TEXT NOT NULL CHECK(status IN ('Current','Past')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS projects_owner_status ON interior_design_projects(owner_account_id, status);

-- 7. Project Images (Sprint 2 - US20..US29)
CREATE TABLE IF NOT EXISTS project_images (
    image_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES interior_design_projects(project_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK(position BETWEEN 0 AND 4),
    mime_type TEXT NOT NULL CHECK(mime_type IN ('image/jpeg','image/png','image/webp')),
    content BLOB NOT NULL,
    UNIQUE(project_id, position)
) STRICT;

-- 8. Customer Favourites (Sprint 3 - US32..US34)
CREATE TABLE IF NOT EXISTS favourites (
    customer_account_id TEXT NOT NULL REFERENCES user_accounts(account_id) ON DELETE RESTRICT,
    project_id TEXT NOT NULL REFERENCES interior_design_projects(project_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(customer_account_id, project_id)
) STRICT;

CREATE INDEX IF NOT EXISTS favourites_project ON favourites(project_id);

-- 9. Project Views Analytics (Sprint 3 - US31, US37)
CREATE TABLE IF NOT EXISTS project_views (
    project_id TEXT NOT NULL REFERENCES interior_design_projects(project_id) ON DELETE CASCADE,
    event_id TEXT NOT NULL CHECK(length(event_id) BETWEEN 16 AND 100),
    occurred_at TEXT NOT NULL,
    PRIMARY KEY(project_id, event_id)
) STRICT;

CREATE INDEX IF NOT EXISTS project_views_time ON project_views(occurred_at, project_id);

-- 10. Platform Report Ledger (Sprint 3 - US44..US46)
CREATE TABLE IF NOT EXISTS report_events (
    kind TEXT NOT NULL CHECK(kind IN ('project_created','project_view')),
    event_key TEXT NOT NULL,
    project_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    PRIMARY KEY(kind, event_key)
) STRICT;

CREATE INDEX IF NOT EXISTS report_events_period ON report_events(kind, occurred_at);

CREATE TABLE IF NOT EXISTS report_coverage (
    retained_since TEXT NOT NULL
) STRICT;

INSERT OR IGNORE INTO report_coverage VALUES (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'));

-- Automated Triggers for Platform Reporting
CREATE TRIGGER IF NOT EXISTS report_project_created AFTER INSERT ON interior_design_projects
BEGIN
    INSERT OR IGNORE INTO report_events VALUES ('project_created', NEW.project_id, NEW.project_id, utc_timestamp(NEW.created_at));
END;

CREATE TRIGGER IF NOT EXISTS report_project_view AFTER INSERT ON project_views
BEGIN
    INSERT OR IGNORE INTO report_events VALUES ('project_view', json_array(NEW.project_id, NEW.event_id), NEW.project_id, utc_timestamp(NEW.occurred_at));
END;

PRAGMA user_version = 6;
