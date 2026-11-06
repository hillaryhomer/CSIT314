"""Independent event aggregates avoid multiplicative project/favourite joins."""
class ReportRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    def aggregate(self, start, end):
        # Coverage and events come from the same SQLite snapshot in one statement.
        rows = self.connection.execute('''SELECT c.retained_since,e.kind,COUNT(e.event_key) AS total
            FROM report_coverage c LEFT JOIN report_events e ON e.occurred_at>=? AND e.occurred_at<?
            GROUP BY c.retained_since,e.kind''', (start, end)).fetchall()
        return {r['kind']: r['total'] for r in rows if r['kind']}, rows[0]['retained_since']
