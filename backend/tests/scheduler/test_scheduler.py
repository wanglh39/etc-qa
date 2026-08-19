from unittest.mock import MagicMock, patch

import pytest

from scheduler.scheduler import SchedulerManager


class TestSchedulerManager:
    def test_initial_state(self):
        mgr = SchedulerManager()
        assert mgr.is_running() is False

    def test_start_disabled(self):
        mgr = SchedulerManager()
        with patch("scheduler.scheduler.get_config") as mock_cfg:
            mock_cfg.return_value = {"scheduler": {"enabled": False}}
            mgr.start()
            assert mgr.is_running() is False

    @patch("scheduler.scheduler.get_config")
    def test_start_enabled(self, mock_cfg):
        mock_cfg.return_value = {
            "scheduler": {
                "enabled": True,
                "timezone": "Asia/Shanghai",
                "jobs": {
                    "sync_and_ingest": {"enabled": True, "schedule_type": "interval", "hours": 1},
                    "cleanup": {"enabled": True, "schedule_type": "interval", "hours": 24},
                },
            }
        }
        mgr = SchedulerManager()
        mgr.start()
        assert mgr.is_running() is True
        status = mgr.get_status()
        assert status["running"] is True
        assert len(status["jobs"]) == 3
        mgr.stop()
        assert mgr.is_running() is False

    @patch("scheduler.scheduler.get_config")
    def test_start_with_disabled_job(self, mock_cfg):
        mock_cfg.return_value = {
            "scheduler": {
                "enabled": True,
                "timezone": "Asia/Shanghai",
                "jobs": {
                    "sync_and_ingest": {"enabled": False, "schedule_type": "interval", "hours": 1},
                    "cleanup": {"enabled": True, "schedule_type": "interval", "hours": 24},
                },
            }
        }
        mgr = SchedulerManager()
        mgr.start()
        status = mgr.get_status()
        assert len(status["jobs"]) == 2
        mgr.stop()

    def test_stop_when_not_started(self):
        mgr = SchedulerManager()
        mgr.stop()
        assert mgr.is_running() is False

    @patch("scheduler.scheduler.get_config")
    def test_trigger_job_not_running(self, mock_cfg):
        mock_cfg.return_value = {"scheduler": {"enabled": True, "timezone": "Asia/Shanghai", "jobs": {}}}
        mgr = SchedulerManager()
        result = mgr.trigger_job("sync_and_ingest")
        assert "error" in result

    @patch("scheduler.scheduler.get_config")
    def test_trigger_nonexistent_job(self, mock_cfg):
        mock_cfg.return_value = {
            "scheduler": {
                "enabled": True,
                "timezone": "Asia/Shanghai",
                "jobs": {"sync_and_ingest": {"enabled": True, "schedule_type": "interval", "hours": 1}},
            }
        }
        mgr = SchedulerManager()
        mgr.start()
        result = mgr.trigger_job("nonexistent")
        assert "error" in result
        mgr.stop()

    def test_get_status_not_started(self):
        mgr = SchedulerManager()
        status = mgr.get_status()
        assert status["running"] is False
        assert status["jobs"] == []