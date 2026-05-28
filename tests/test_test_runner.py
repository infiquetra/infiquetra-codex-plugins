"""Unit tests for the test-suite runner."""

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO_ROOT
    / "plugins"
    / "test-suite"
    / "skills"
    / "run-quality-checks"
    / "scripts"
    / "test_runner.py"
)

spec = importlib.util.spec_from_file_location("test_runner", RUNNER_PATH)
test_runner = importlib.util.module_from_spec(spec)
sys.modules["test_runner"] = test_runner
assert spec.loader is not None
spec.loader.exec_module(test_runner)

CheckResult = test_runner.CheckResult
QualityCheckRunner = test_runner.QualityCheckRunner


class TestQualityCheckRunner:
    def test_init_default_values(self):
        runner = QualityCheckRunner()

        assert runner.coverage_threshold == 80
        assert runner.test_dir == Path("tests")
        assert runner.source_dir == Path("src")
        assert runner.fail_fast is False
        assert runner.verbose is False
        assert runner.dry_run is False

    def test_init_custom_values(self):
        runner = QualityCheckRunner(
            coverage_threshold=85,
            test_dir="test",
            source_dir="source",
            fail_fast=True,
            verbose=True,
            dry_run=True,
        )

        assert runner.coverage_threshold == 85
        assert runner.test_dir == Path("test")
        assert runner.source_dir == Path("source")
        assert runner.fail_fast is True
        assert runner.verbose is True
        assert runner.dry_run is True

    def test_run_check_success(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "All tests passed"
        mock_subprocess_run.return_value.stderr = ""

        runner = QualityCheckRunner()
        result = runner.run_check("pytest", ["pytest", "tests/"])

        assert result.name == "pytest"
        assert result.status == "passed"
        assert result.duration >= 0
        assert "All tests passed" in result.output

    def test_run_check_failure(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stdout = ""
        mock_subprocess_run.return_value.stderr = "Test failed"

        runner = QualityCheckRunner()
        result = runner.run_check("pytest", ["pytest", "tests/"])

        assert result.name == "pytest"
        assert result.status == "failed"
        assert "Test failed" in result.output

    def test_run_check_dry_run_does_not_call_subprocess(self, mock_subprocess_run):
        runner = QualityCheckRunner(dry_run=True)
        result = runner.run_check("ruff", ["ruff", "check", "src"])

        assert result.status == "passed"
        assert result.details["dry_run"] is True
        assert result.details["command"] == ["ruff", "check", "src"]
        mock_subprocess_run.assert_not_called()

    def test_normalize_checks_keeps_stable_order(self):
        runner = QualityCheckRunner()

        assert runner.normalize_checks(["mypy", "pytest"]) == ["pytest", "mypy"]

    def test_normalize_checks_rejects_unknown(self):
        runner = QualityCheckRunner()

        try:
            runner.normalize_checks(["pytest", "unknown"])
        except ValueError as exc:
            assert "unknown" in str(exc)
        else:
            raise AssertionError("expected ValueError")

    def test_run_all_checks_uses_selected_checks(self, mock_subprocess_run):
        runner = QualityCheckRunner(dry_run=True)

        results = runner.run_all_checks(["ruff", "pytest"])

        assert [result.name for result in results] == ["pytest", "ruff"]
        mock_subprocess_run.assert_not_called()

    def test_run_pytest_parses_coverage(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = """
        ---------- coverage: platform linux ----------
        Name                 Stmts   Miss  Cover
        ----------------------------------------
        src/module.py           100     15    85%
        ----------------------------------------
        TOTAL                   100     15    85%
        """
        mock_subprocess_run.return_value.stderr = ""

        runner = QualityCheckRunner(coverage_threshold=80)
        result = runner.run_pytest()

        assert result.status == "passed"
        assert result.details["coverage"] == 85.0
        assert result.details["threshold_met"] is True

    def test_run_pytest_below_threshold(self, mock_subprocess_run):
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "TOTAL                   100     30    70%"
        mock_subprocess_run.return_value.stderr = ""

        runner = QualityCheckRunner(coverage_threshold=80)
        result = runner.run_pytest()

        assert result.status == "failed"
        assert result.details["coverage"] == 70.0
        assert result.details["threshold_met"] is False

    def test_generate_json_output(self):
        runner = QualityCheckRunner()
        results = [
            CheckResult(
                name="pytest",
                status="passed",
                duration=12.3,
                output="All tests passed",
                details={"tests_passed": 45, "tests_failed": 0, "coverage": 82.0},
            ),
            CheckResult(
                name="ruff",
                status="passed",
                duration=1.8,
                output="No issues",
                details={"issues": 0},
            ),
        ]

        json_output = runner.generate_json_output(results)

        assert json_output["summary"]["total_checks"] == 2
        assert json_output["summary"]["passed"] == 2
        assert json_output["summary"]["failed"] == 0
        assert json_output["checks"]["pytest"]["status"] == "passed"
        assert json_output["checks"]["pytest"]["coverage"] == 82.0
        assert json_output["checks"]["ruff"]["issues"] == 0


def test_check_result_creation():
    result = CheckResult(
        name="test",
        status="passed",
        duration=1.5,
        output="output",
        details={"key": "value"},
    )

    assert result.name == "test"
    assert result.status == "passed"
    assert result.duration == 1.5
    assert result.output == "output"
    assert result.details == {"key": "value"}
