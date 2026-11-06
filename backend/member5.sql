CREATE TABLE project_views (
    project_id TEXT NOT NULL REFERENCES interior_design_projects(project_id) ON DELETE CASCADE,
    event_id TEXT NOT NULL CHECK(length(event_id) BETWEEN 16 AND 100),
    occurred_at TEXT NOT NULL,
    PRIMARY KEY(project_id,event_id)
) STRICT;
CREATE INDEX project_views_time ON project_views(occurred_at,project_id);
PRAGMA user_version = 5;
