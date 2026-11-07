"""Calendar report ranges in Asia/Makassar (UTC+8 since 2000)."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import re
from backend.models import AppError

REPORT_ZONE = timezone(timedelta(hours=8), 'Asia/Makassar')


def utc_timestamp(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat(timespec='microseconds')


@dataclass(frozen=True)
class ReportPeriod:
    kind: str
    start: datetime
    end: datetime

    @classmethod
    def parse(cls, kind, value):
        try:
            if not isinstance(value, str):
                raise ValueError()
            if kind == 'monthly':
                if not re.fullmatch(r'\d{4}-\d{2}', value):
                    raise ValueError()
                selected = date.fromisoformat(value + '-01')
            else:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError()
                selected = date.fromisoformat(value)
            if not 2000 <= selected.year <= 9998:
                raise ValueError()
            if kind == 'daily':
                start, end = selected, selected + timedelta(days=1)
            elif kind == 'weekly':
                start = selected - timedelta(days=selected.weekday())
                end = start + timedelta(days=7)
            elif kind == 'monthly':
                start = selected
                end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
            else:
                raise ValueError()
            return cls(kind, datetime.combine(start, datetime.min.time(), REPORT_ZONE),
                       datetime.combine(end, datetime.min.time(), REPORT_ZONE))
        except (ValueError, TypeError, OverflowError):
            raise AppError('VALIDATION', 'Select a valid calendar period (years 2000-9998).')


class ReportService:
    def __init__(self, store):
        self.store = store

    def generate(self, kind, value, now=None):
        period = ReportPeriod.parse(kind, value)
        now = now or datetime.now(timezone.utc)
        start, end = utc_timestamp(period.start.isoformat()), utc_timestamp(period.end.isoformat())
        cutoff = min(period.end, now)
        counts, retained_since = self.store.aggregate(start, utc_timestamp(cutoff.isoformat()))
        return {'period': kind, 'timezone': 'Asia/Makassar (UTC+08:00)',
                'startInclusive': period.start.isoformat(), 'endExclusive': period.end.isoformat(),
                'startUtc': start, 'endUtc': end, 'generatedAt': now.isoformat(),
                'partial': period.start <= now < period.end, 'future': now < period.start,
                'metrics': {'projectsCreated': counts.get('project_created', 0), 'viewEvents': counts.get('project_view', 0)},
                'coverage': {'retainedSince': retained_since, 'complete': start >= utc_timestamp(retained_since),
                    'note': 'Before retention began, only surviving project/view records could be imported; deleted activity and visits before view tracking are unavailable.'}}


@dataclass
class Report:
    """Report entity matching Class Model 2 in CSIT314_Consistency_Fixes.drawio."""
    period_start: str
    period_end: str
    generated_at: str
    metrics: dict

    @property
    def periodStart(self) -> str:
        return self.period_start

    @property
    def periodEnd(self) -> str:
        return self.period_end

    @property
    def generatedAt(self) -> str:
        return self.generated_at
