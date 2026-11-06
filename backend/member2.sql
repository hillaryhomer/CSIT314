CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES user_accounts(account_id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS sessions_account ON auth_sessions(account_id);
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL UNIQUE REFERENCES user_accounts(account_id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),
    reg_number TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL CHECK(length(trim(address)) BETWEEN 1 AND 500),
    contact TEXT NOT NULL CHECK(length(trim(contact)) BETWEEN 1 AND 254),
    description TEXT NOT NULL DEFAULT '' CHECK(length(description) <= 4000)
) STRICT;
PRAGMA user_version = 2;
