CREATE TABLE IF NOT EXISTS favourites (
    customer_account_id TEXT NOT NULL REFERENCES user_accounts(account_id) ON DELETE RESTRICT,
    project_id TEXT NOT NULL REFERENCES interior_design_projects(project_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(customer_account_id, project_id)
) STRICT;
CREATE INDEX IF NOT EXISTS favourites_project ON favourites(project_id);
PRAGMA user_version = 4;
