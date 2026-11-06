CREATE TABLE IF NOT EXISTS project_categories (
    category_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Suspended'))
) STRICT;
INSERT OR IGNORE INTO project_categories(category_id,name,description) VALUES
('CAT001','Residential','Homes and apartments'),
('CAT002','Commercial','Offices and retail'),
('CAT003','Hospitality','Cafes, restaurants and boutique hotels');
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
CREATE INDEX IF NOT EXISTS projects_owner_status ON interior_design_projects(owner_account_id,status);
CREATE TABLE IF NOT EXISTS project_images (
    image_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES interior_design_projects(project_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK(position BETWEEN 0 AND 4),
    mime_type TEXT NOT NULL CHECK(mime_type IN ('image/jpeg','image/png','image/webp')),
    content BLOB NOT NULL,
    UNIQUE(project_id,position)
) STRICT;
PRAGMA user_version = 3;
