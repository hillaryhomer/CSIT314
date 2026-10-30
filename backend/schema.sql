-- Keep the schema compatible with the previous implementation so existing data remains usable.
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
PRAGMA user_version = 1;
