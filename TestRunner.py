"""Run the legacy scenario suite and display grouped test results."""
from datetime import datetime
from pathlib import Path
import re
import shutil
import textwrap
import sys
import time
import unittest

# Ensure UTF-8 output encoding for clean box drawing on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Scenario groups used by the legacy test runner.
SPRINT_CONFIG = [
    {
        "title": "SPRINT 1 : LOGIN AND SHARED AUTHENTICATION (US11, US12, US18, US19, US35, US36, US47, US48)",
        "us_list": [
            ("US11", "Us11UserAdminLoginTest"),
            ("US12", "Us12UserAdminLogoutTest"),
            ("US18", "Us18InteriorDesignerLoginTest"),
            ("US19", "Us19InteriorDesignerLogoutTest"),
            ("US35", "Us35CustomerLoginTest"),
            ("US36", "Us36CustomerLogoutTest"),
            ("US47", "Us47PlatformManagerLoginTest"),
            ("US48", "Us48PlatformManagerLogoutTest"),
        ]
    },
    {
        "title": "SPRINT 2 : USER PROFILES, USER ACCOUNTS & INTERIOR DESIGN PROJECTS (US01-10, US13-17, US20-29)",
        "us_list": [
            ("US01", "Us01CreateUserProfileTest"),
            ("US02", "Us02ViewUserProfileTest"),
            ("US03", "Us03UpdateUserProfileTest"),
            ("US04", "Us04SuspendUserProfileTest"),
            ("US05", "Us05SearchUserProfileTest"),
            ("US06", "Us06CreateUserAccountTest"),
            ("US07", "Us07ViewUserAccountTest"),
            ("US08", "Us08UpdateUserAccountTest"),
            ("US09", "Us09SuspendUserAccountTest"),
            ("US10", "Us10SearchUserAccountsTest"),
            ("US13", "Us13CreateCompanyProfileTest"),
            ("US14", "Us14ViewCompanyInformationTest"),
            ("US15", "Us15UpdateCompanyInformationTest"),
            ("US16", "Us16DeleteCompanyInformationTest"),
            ("US17", "Us17SearchCompanyInformationTest"),
            ("US20", "Us20CreateCurrentProjectTest"),
            ("US21", "Us21ViewCurrentProjectTest"),
            ("US22", "Us22UpdateCurrentProjectTest"),
            ("US23", "Us23DeleteCurrentProjectTest"),
            ("US24", "Us24SearchCurrentProjectsTest"),
            ("US25", "Us25CreatePastProjectTest"),
            ("US26", "Us26ViewPastProjectTest"),
            ("US27", "Us27UpdatePastProjectTest"),
            ("US28", "Us28DeletePastProjectTest"),
            ("US29", "Us29SearchPastProjectsTest"),
        ]
    },
    {
        "title": "SPRINT 3 : CUSTOMER DISCOVERY, FAVOURITES, ANALYTICS & REPORTS (US30-34, US37-46)",
        "us_list": [
            ("US30", "Us30SearchInteriorDesignProjectsTest"),
            ("US31", "Us31ViewInteriorDesignProjectTest"),
            ("US32", "Us32SaveInteriorDesignProjectTest"),
            ("US33", "Us33SearchShortlistedProjectsTest"),
            ("US34", "Us34ViewShortlistedProjectsTest"),
            ("US37", "Us37ViewProjectViewCountsTest"),
            ("US38", "Us38ViewProjectShortlistCountsTest"),
            ("US39", "Us39CreateProjectCategoryTest"),
            ("US40", "Us40ViewProjectCategoriesTest"),
            ("US41", "Us41UpdateProjectCategoryTest"),
            ("US42", "Us42DeleteProjectCategoryTest"),
            ("US43", "Us43SearchProjectCategoriesTest"),
            ("US44", "Us44GenerateDailyReportTest"),
            ("US45", "Us45GenerateWeeklyReportTest"),
            ("US46", "Us46GenerateMonthlyReportTest"),
        ]
    }
]


def table_width():
    # Leave one terminal column free to prevent automatic line wrapping.
    return max(50, min(110, shutil.get_terminal_size((111, 30)).columns - 1))


def detail_widths():
    remaining = table_width() - 21
    scenario = int(remaining * 0.55)
    return [4, 4, scenario, remaining - scenario]


def border(widths, left, join, right):
    print(left + join.join("─" * (width + 2) for width in widths) + right)


def cells(values, widths, align=None):
    wrapped = [textwrap.wrap(str(value), width=width) or [""]
               for value, width in zip(values, widths)]
    align = align or ["left"] * len(widths)
    for line in range(max(map(len, wrapped))):
        content = []
        for lines, width, alignment in zip(wrapped, widths, align):
            value = lines[line] if line < len(lines) else ""
            value = value.rjust(width) if alignment == "right" else value.ljust(width)
            content.append(" " + value + " ")
        print("│" + "│".join(content) + "│")


def print_banner(now_str: str):
    width = table_width() - 4
    border([width], "┌", "┬", "┐")
    for title in ["INTERIOR DESIGNER PLATFORM (ATELIER MATCH) - CSIT314",
                  "TEST SUITE RUNNER",
                  f"Timestamp: {now_str} | Isolated SQLite"]:
        for line in textwrap.wrap(title, width):
            cells([line.center(width)], [width])
    border([width], "└", "┴", "┘")
    print()


def print_table_header(title: str):
    widths = detail_widths()
    title_width = table_width() - 4
    border([title_width], "┌", "┬", "┐")
    cells([title], [title_width])
    border(widths, "├", "┬", "┤")
    cells(["STAT", "US", "TEST SCENARIO", "EXPECTED RESULT / MESSAGE"], widths)
    border(widths, "├", "┼", "┤")


def print_table_row(status: str, us_id: str, scenario: str, msg: str):
    cells([status, us_id, scenario, msg], detail_widths())


def print_table_footer():
    border(detail_widths(), "└", "┴", "┘")
    print()


def print_summary(summaries, total_tests, total_dur, failed_tests):
    widths = [table_width() - 41, 6, 9, 13]
    title_width = table_width() - 4
    border([title_width], "┌", "┬", "┐")
    cells(["TEST SUITE EXECUTION SUMMARY"], [title_width])
    border(widths, "├", "┬", "┤")
    cells(["SPRINT / TEST DOMAIN", "TESTS", "TIME (s)", "STATUS"], widths)
    border(widths, "├", "┼", "┤")
    for summary in summaries:
        rate = int(summary['passed'] / summary['tests'] * 100) if summary['tests'] else 0
        status = f"{'PASS' if summary['failed'] == 0 else 'FAIL'} ({rate}%)"
        cells([summary['name'], summary['tests'], f"{summary['duration']:.2f}", status],
              widths, ["left", "right", "right", "left"])
        border(widths, "├", "┼", "┤")
    status = "PASS (100%)" if failed_tests == 0 else f"FAIL ({failed_tests})"
    cells(["TOTAL - ALL USER STORIES + BENCHMARK", total_tests, f"{total_dur:.2f}", status],
          widths, ["left", "right", "right", "left"])
    border(widths, "└", "┴", "┘")
    print()


def run_tests():
    start_all = time.time()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_banner(now_str)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    sprint_summaries = []

    for sprint in SPRINT_CONFIG:
        sprint_start = time.time()
        print_table_header(sprint["title"])
        s_total = 0
        s_passed = 0
        s_failed = 0

        for us_id, class_name in sprint["us_list"]:
            try:
                import tests.test_all as test_module
                cls = getattr(test_module, class_name)
                suite = unittest.TestLoader().loadTestsFromTestCase(cls)

                for test in suite:
                    method_name = test._testMethodName
                    method = getattr(test, method_name)
                    doc = method.__doc__ or ""

                    match = re.search(r'(?:PASS|FAIL)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*\"([^\"]+)\"', doc)
                    if match:
                        scenario = match.group(2).strip()
                        msg = match.group(3).strip()
                    else:
                        scenario = method_name.replace("test_", "").replace("_", " ").title()
                        msg = "Test executed successfully."

                    result = unittest.TestResult()
                    test.run(result)
                    total_tests += 1
                    s_total += 1

                    if result.wasSuccessful():
                        passed_tests += 1
                        s_passed += 1
                        status = "PASS"
                    else:
                        failed_tests += 1
                        s_failed += 1
                        status = "FAIL"

                    print_table_row(status, us_id, scenario, msg)
            except Exception as e:
                failed_tests += 1
                s_failed += 1
                total_tests += 1
                s_total += 1
                print_table_row("FAIL", us_id, f"Execution Error: {str(e)}", "Error")

        print_table_footer()
        s_duration = time.time() - sprint_start
        sprint_summaries.append({
            "name": sprint["title"].split(":")[0].strip() + ": " + sprint["title"].split(":")[1].split("(")[0].strip(),
            "tests": s_total,
            "passed": s_passed,
            "failed": s_failed,
            "duration": s_duration
        })

    # Benchmark section in table format
    nfr_start = time.time()
    nfr_title = "NON-FUNCTIONAL REQUIREMENT (NFR-01) : LARGE-SCALE TEST DATA GENERATION (100+ RECORDS PER ENTITY)"
    print_table_header(nfr_title)
    try:
        import io
        from contextlib import redirect_stdout
        from tests.test_all import TestDataLoaderTest
        res = unittest.TestResult()
        with redirect_stdout(io.StringIO()):
            TestDataLoaderTest("test_data_loader_generates_minimum_100_records_per_entity").run(res)
        total_tests += 1
        nfr_dur = time.time() - nfr_start
        if res.wasSuccessful():
            passed_tests += 1
            print_table_row("PASS", "NFR", "Populate >= 100 records for all 8 entities", "Record-count assertions passed.")
            sprint_summaries.append({
                "name": "NFR-01: Large-Scale Test Data Generation (100+ per Entity)",
                "tests": 1,
                "passed": 1,
                "failed": 0,
                "duration": nfr_dur
            })
        else:
            failed_tests += 1
            print_table_row("FAIL", "NFR", "Populate >= 100 records for all 8 entities", "Benchmark failed.")
            sprint_summaries.append({
                "name": "NFR-01: Large-Scale Test Data Generation (100+ per Entity)",
                "tests": 1,
                "passed": 0,
                "failed": 1,
                "duration": nfr_dur
            })
    except Exception as e:
        failed_tests += 1
        total_tests += 1
        print_table_row("FAIL", "NFR", f"Benchmark Error: {str(e)}", "Error")
    print_table_footer()

    total_dur = time.time() - start_all

    print_summary(sprint_summaries, total_tests, total_dur, failed_tests)

    if failed_tests == 0:
        print("✓ TEST RUN PASSED — All scheduled tests completed successfully.\n")
        return 0
    else:
        print(f"✗ TEST RUN FAILED — {failed_tests} test(s) failed.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
