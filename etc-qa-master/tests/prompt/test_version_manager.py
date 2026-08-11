from unittest.mock import MagicMock, patch

import prompt.version_manager as vm_module
from prompt.version_manager import PromptVersionManager, _detect_columns, _select_fields, get_version_manager


class TestDetectColumns:
    def test_returns_columns(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("id",), ("prompt_key",), ("status",)]
        mock_conn.cursor.return_value = mock_cursor
        cols = _detect_columns(mock_conn)
        assert "id" in cols
        assert "prompt_key" in cols
        assert "status" in cols

    def test_exception_returns_empty(self):
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("db error")
        cols = _detect_columns(mock_conn)
        assert cols == set()


class TestSelectFields:
    def test_base_fields(self):
        fields = _select_fields(set())
        assert "prompt_key" in fields
        assert "template_text" in fields

    def test_with_id(self):
        fields = _select_fields({"id"})
        parts = fields.split(", ")
        assert parts[0] == "id"

    def test_with_status(self):
        fields = _select_fields({"status"})
        assert "status" in fields

    def test_with_created_at(self):
        fields = _select_fields({"created_at"})
        assert "created_at" in fields

    def test_with_updated_at(self):
        fields = _select_fields({"updated_at"})
        assert "updated_at" in fields


class TestPromptVersionManager:
    @patch("prompt.version_manager.MySQLClient")
    def test_list_versions(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"id": 1, "prompt_key": "judge", "template_text": "v1", "version": 1,
             "is_active": 0, "status": "active", "description": "", "created_at": None, "updated_at": None},
            {"id": 2, "prompt_key": "judge", "template_text": "v2", "version": 2,
             "is_active": 1, "status": "active", "description": "", "created_at": None, "updated_at": None},
        ]

        result = vm.list_versions("judge")
        assert len(result) == 2

    @patch("prompt.version_manager.MySQLClient")
    def test_list_versions_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.side_effect = Exception("db error")

        try:
            vm.list_versions("judge")
            assert False
        except Exception:
            pass
        mock_mysql._reset_conn.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_get_version_active(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"prompt_key": "judge", "version": 2, "template_text": "active"}

        result = vm.get_version("judge")
        assert result["version"] == 2

    @patch("prompt.version_manager.MySQLClient")
    def test_get_version_specific(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"prompt_key": "judge", "version": 1, "template_text": "v1"}

        result = vm.get_version("judge", version=1)
        assert result["version"] == 1

    @patch("prompt.version_manager.MySQLClient")
    def test_get_version_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = Exception("db error")

        try:
            vm.get_version("judge")
            assert False
        except Exception:
            pass
        mock_mysql._reset_conn.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_publish_new_version(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"max_ver": 2}

        result = vm.publish("judge", "new template text", "test publish")
        assert result["version"] == 3
        assert result["status"] == "active"
        mock_conn.commit.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_publish_first_version(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"max_ver": None}

        result = vm.publish("new_key", "first template", "initial")
        assert result["version"] == 1

    @patch("prompt.version_manager.MySQLClient")
    def test_publish_no_status_column(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"prompt_key", "template_text", "version", "is_active", "description"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"max_ver": 1}

        result = vm.publish("judge", "no status template", "test")
        assert result["version"] == 2

    @patch("prompt.version_manager.MySQLClient")
    def test_publish_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = Exception("publish error")

        try:
            vm.publish("judge", "template", "desc")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_rollback_to_previous(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"status", "prompt_key"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"version": 2}

        result = vm.rollback("judge")
        assert result["version"] == 2
        assert result["status"] == "rolled_back"

    @patch("prompt.version_manager.MySQLClient")
    def test_rollback_no_available_version(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"status", "prompt_key"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = vm.rollback("judge")
        assert "error" in result

    @patch("prompt.version_manager.MySQLClient")
    def test_rollback_to_specific_version(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = vm.rollback("judge", target_version=1)
        assert result["version"] == 1

    @patch("prompt.version_manager.MySQLClient")
    def test_rollback_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("rollback error")

        try:
            vm.rollback("judge", target_version=1)
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_start_shadow(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": 1, "template_text": "shadow text", "version": 2
        }

        result = vm.start_shadow("judge", 2)
        assert result["status"] == "shadow"
        assert result["shadow_version"] == 2

    @patch("prompt.version_manager.MySQLClient")
    def test_start_shadow_no_status_column(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"prompt_key", "template_text", "version"}

        result = vm.start_shadow("judge", 2)
        assert "error" in result

    @patch("prompt.version_manager.MySQLClient")
    def test_start_shadow_nonexistent_version(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = vm.start_shadow("judge", 99)
        assert "error" in result

    @patch("prompt.version_manager.MySQLClient")
    def test_start_shadow_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = Exception("shadow error")

        try:
            vm.start_shadow("judge", 2)
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_stop_shadow(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = vm.stop_shadow("judge", 2)
        assert result["status"] == "stopped"

    @patch("prompt.version_manager.MySQLClient")
    def test_stop_shadow_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("stop shadow error")

        try:
            vm.stop_shadow("judge", 2)
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_get_shadow_template(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"template_text": "shadow template"}

        result = vm.get_shadow_template("judge")
        assert result == "shadow template"

    @patch("prompt.version_manager.MySQLClient")
    def test_get_shadow_template_none(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = vm.get_shadow_template("judge")
        assert result is None

    @patch("prompt.version_manager.MySQLClient")
    def test_get_shadow_template_no_status(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"prompt_key", "template_text", "version"}

        result = vm.get_shadow_template("judge")
        assert result is None

    @patch("prompt.version_manager.MySQLClient")
    def test_get_shadow_template_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "created_at"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("shadow template error")

        result = vm.get_shadow_template("judge")
        assert result is None
        mock_mysql._reset_conn.assert_called_once()

    @patch("prompt.version_manager.MySQLClient")
    def test_list_all_keys(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"id", "prompt_key", "status"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"prompt_key": "judge", "latest_version": 3, "active_count": 1, "shadow_count": 0},
        ]

        result = vm.list_all_keys()
        assert len(result) == 1

    @patch("prompt.version_manager.MySQLClient")
    def test_list_all_keys_exception(self, mock_mysql_cls):
        vm = PromptVersionManager()
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        vm._mysql = mock_mysql
        vm._cols_cache = {"prompt_key"}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.side_effect = Exception("list keys error")

        try:
            vm.list_all_keys()
            assert False
        except Exception:
            pass
        mock_mysql._reset_conn.assert_called_once()


class TestGetVersionManager:
    def test_singleton(self):
        vm_module._version_manager = None
        v1 = get_version_manager()
        v2 = get_version_manager()
        assert v1 is v2
