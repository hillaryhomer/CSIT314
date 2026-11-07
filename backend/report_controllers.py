"""US44-46 share aggregation and calendar rules; manager permission stays server-side."""
from backend.category_controllers import ManagerController
from backend.report_repository import ReportRepository
from backend.report_service import ReportService


class GenerateDailyReportController(ManagerController):
    kind = 'daily'

    def execute(self, value):
        self.require('reports:read')
        return ReportService(ReportRepository(self.repository)).generate(self.kind, value)


class GenerateWeeklyReportController(GenerateDailyReportController):
    kind = 'weekly'


class GenerateMonthlyReportController(GenerateDailyReportController):
    kind = 'monthly'


# BCE Aliases matching CSIT314 diagram notations
GenerateDailyReportC = GenerateDailyReportController
GenerateWeeklyReportC = GenerateWeeklyReportController
GenerateMonthlyReportC = GenerateMonthlyReportController
