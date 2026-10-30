# Handoff to Member 2

Use the shared Python backend and **data/member1.sqlite** database. Do not create a second account store.

## Model and Repository

`backend/models.py` contains UserProfile and UserAccount. Python attributes use snake_case; React JSON uses camelCase.

- Profile: profile_id, name, role, permissions (list), status.
- Account: account_id, username, email, password_hash, profile_id, status.
- Stable IDs: UP-UUID and UA-UUID. Accounts refer to profile IDs, not profile names.
- `account.to_dict(profile)` returns public data without passwords or hashes.

`Repository` in `backend/database.py` provides find_profile, profile_with_name, search_profiles, create_profile, update_profile, find_account, account_with_username, account_with_email, list_accounts, create_account, and update_account. Use `with repository.transaction():` for related changes. update_account changes only username, email, and profile_id; it does not change the password hash or status.

Profile names, usernames, and email addresses are compared after NFKC normalization, trimming, and lowercase conversion. Email is stored lowercase. Profile search is an unbounded name substring search with no wildcards. Usernames allow 3-40 ASCII letters, digits, dots, underscores, or hyphens.

## Passwords and Login

`backend/validation.py` provides `hash_password(password)` and `verify_password(password, password_hash)`. The format remains bcrypt **$2b$, cost 12**, compatible with accounts from the previous backend. Passwords must contain at least 12 characters, at most 72 UTF-8 bytes, and cannot be whitespace-only. Passwords are not trimmed or normalized before hashing.

Member 2 must replace `AuthenticatedContext.resolve(request)` in `backend/app.py` to return an account ID from a verified session or None. Install it through `create_app(database_path, auth_context=...)`. Never trust an ID, role, or permission from the request body, query, browser headers, or role selector.

After password verification and for every protected request, call:

```python
from backend.controllers import effective_access
account, profile = effective_access(repository, account_id)
```

Both the account and profile must be Active. **An account whose profile is Suspended cannot access protected functions; the account status itself does not change.** Checks read the latest database state, so profile or permission changes apply on the next request. This implementation does not revoke existing sessions; session login/logout remains Member 2 work.

Member 1 controllers require the admin role and profile or account read/write permissions according to the operation. Account forms also require profiles:read permission for profile assignment options.

## Rules to Preserve

- Profile updates preserve the ID, status, and account relationships. Suspension does not delete a profile.
- Account updates preserve the ID, password hash, and status. New assignments must target an active profile.
- Accounts can remain assigned to a suspended profile when username or email is changed, without automatic reactivation.
- Administrators cannot suspend their own profile, remove their own admin role or permissions, or move their account to a profile that removes their access.
- DevelopmentContext is development-only; the default AuthenticatedContext rejects access.
- Member 2 owns sessions, cookies, expiry, logout/invalidation, and session CSRF protection. APIs require JSON and reject origins that do not match APP_ORIGIN.

## Error Response

Format: `{error: {code, message, fields}}`. VALIDATION=400, UNAUTHENTICATED=401, FORBIDDEN=403, NOT_FOUND=404, DUPLICATE/ALREADY_SUSPENDED=409, PERSISTENCE=500. SQL details are not sent to the browser.

The real login/session integration has not been tested because Member 2's implementation is not yet present. Member 1 tests cover the repository, bcrypt, and effective_access, including rejection of suspended profiles.
