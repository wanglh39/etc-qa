import sys
from unittest.mock import MagicMock, patch

from fastapi import APIRouter


class TestMainModule:
    @patch("app.create_service")
    @patch("utils.config.get_config")
    def test_app_created(self, mock_cfg, mock_create):
        mock_cfg.return_value = {"server": {"title": "test", "version": "1.0"}}
        mock_create.return_value = MagicMock()
        mock_router = APIRouter()
        mock_mod = MagicMock()
        mock_mod.router = mock_router
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            if "main" in sys.modules:
                del sys.modules["main"]
            import main
        assert main.app is not None
        assert main.service is not None

    @patch("app.create_service")
    @patch("utils.config.get_config")
    def test_app_title_from_config(self, mock_cfg, mock_create):
        mock_cfg.return_value = {"server": {"title": "鑷畾涔夋爣棰?, "version": "2.0"}}
        mock_create.return_value = MagicMock()
        mock_router = APIRouter()
        mock_mod = MagicMock()
        mock_mod.router = mock_router
        with patch.dict(sys.modules, {"api.routes": mock_mod}):
            if "main" in sys.modules:
                del sys.modules["main"]
            import main
        assert "鑷畾涔夋爣棰? in main.app.title