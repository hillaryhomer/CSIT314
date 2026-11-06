ALTER TABLE project_categories ADD COLUMN name_key TEXT NOT NULL DEFAULT '';
ALTER TABLE project_categories ADD COLUMN created_at TEXT;
ALTER TABLE project_categories ADD COLUMN updated_at TEXT;
ALTER TABLE project_categories ADD COLUMN deleted_at TEXT;
UPDATE project_categories SET name_key=normalize(name);
CREATE UNIQUE INDEX category_normalized_name ON project_categories(name_key);
CREATE TRIGGER category_validate_insert BEFORE INSERT ON project_categories
WHEN length(trim(NEW.name)) NOT BETWEEN 1 AND 100 OR length(NEW.description)>2000
 OR NEW.name_key<>normalize(NEW.name) OR NEW.name<>clean(NEW.name)
BEGIN SELECT RAISE(ABORT,'Invalid category fields'); END;
CREATE TRIGGER category_validate_update BEFORE UPDATE ON project_categories
WHEN length(trim(NEW.name)) NOT BETWEEN 1 AND 100 OR length(NEW.description)>2000
 OR NEW.name_key<>normalize(NEW.name) OR NEW.name<>clean(NEW.name)
BEGIN SELECT RAISE(ABORT,'Invalid category fields'); END;

-- An anonymous historical ledger survives project deletion. IDs are event references,
-- not foreign keys to live projects; no customer/account data is copied.
CREATE TABLE report_events (
    kind TEXT NOT NULL CHECK(kind IN ('project_created','project_view')),
    event_key TEXT NOT NULL,
    project_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    PRIMARY KEY(kind,event_key)
) STRICT;
CREATE INDEX report_events_period ON report_events(kind,occurred_at);
CREATE TABLE report_coverage (retained_since TEXT NOT NULL) STRICT;
INSERT INTO report_coverage VALUES (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'));
INSERT INTO report_events SELECT 'project_created',project_id,project_id,utc_timestamp(created_at) FROM interior_design_projects;
INSERT INTO report_events SELECT 'project_view',json_array(project_id,event_id),project_id,utc_timestamp(occurred_at) FROM project_views;
CREATE TRIGGER report_project_created AFTER INSERT ON interior_design_projects
BEGIN INSERT INTO report_events VALUES ('project_created',NEW.project_id,NEW.project_id,utc_timestamp(NEW.created_at)); END;
CREATE TRIGGER report_project_view AFTER INSERT ON project_views
BEGIN INSERT INTO report_events VALUES ('project_view',json_array(NEW.project_id,NEW.event_id),NEW.project_id,utc_timestamp(NEW.occurred_at)); END;
PRAGMA user_version = 6;
