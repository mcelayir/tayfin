"""Tests for tayfin_screener_jobs.cli.main."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from tayfin_screener_jobs.cli.main import app

runner = CliRunner()


class TestJobsList:
    """Tests for ``jobs list`` command."""

    def test_list_shows_vcp_screen(self):
        result = runner.invoke(app, ["jobs", "list"])
        assert result.exit_code == 0
        assert "vcp_screen" in result.output

    def test_list_shows_target(self):
        result = runner.invoke(app, ["jobs", "list"])
        assert "nasdaq-100" in result.output
        assert "NDX" in result.output


class TestJobsRun:
    """Tests for ``jobs run`` command."""

    def test_unknown_job_exits_1(self):
        result = runner.invoke(app, ["jobs", "run", "bogus", "nasdaq-100"])
        assert result.exit_code == 1

    def test_unknown_target_exits_1(self):
        result = runner.invoke(app, ["jobs", "run", "vcp_screen", "nonexistent"])
        assert result.exit_code == 1

    @patch("tayfin_screener_jobs.cli.main.get_job_class")
    def test_run_dispatches_to_job(self, mock_get):
        mock_job_cls = MagicMock()
        mock_instance = MagicMock()
        mock_job_cls.from_config.return_value = mock_instance
        mock_get.return_value = mock_job_cls

        result = runner.invoke(app, ["jobs", "run", "vcp_screen", "nasdaq-100"])

        assert result.exit_code == 0
        mock_get.assert_called_once_with("vcp_screen")
        mock_job_cls.from_config.assert_called_once()
        mock_instance.run.assert_called_once()

    @patch("tayfin_screener_jobs.cli.main.get_job_class")
    def test_run_passes_ticker_and_limit(self, mock_get):
        mock_job_cls = MagicMock()
        mock_instance = MagicMock()
        mock_job_cls.from_config.return_value = mock_instance
        mock_get.return_value = mock_job_cls

        result = runner.invoke(app, [
            "jobs", "run", "vcp_screen", "nasdaq-100",
            "--ticker", "AAPL", "--limit", "5",
        ])

        assert result.exit_code == 0
        mock_instance.run.assert_called_once_with(ticker="AAPL", limit=5)

    @patch("tayfin_screener_jobs.cli.main.get_job_class")
    def test_import_error_handled(self, mock_get):
        mock_get.side_effect = ImportError("no module")
        result = runner.invoke(app, ["jobs", "run", "vcp_screen", "nasdaq-100"])
        assert result.exit_code == 1
        assert "Failed to load" in result.output
