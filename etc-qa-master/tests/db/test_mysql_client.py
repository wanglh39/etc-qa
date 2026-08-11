from unittest.mock import MagicMock, patch

from db.mysql_client import MySQLClient


class TestMySQLClient:
    def setup_method(self):
        self.mock_config = {
            "mysql": {"host": "localhost", "port": 3360, "user": "root", "password": "123456", "database": "etc_qa"},
        }
        import utils.config as cfg_module
        self._original_get = getattr(cfg_module, "get_config", None)
        cfg_module.get_config = lambda: self.mock_config

    def teardown_method(self):
        import utils.config as cfg_module
        if self._original_get:
            cfg_module.get_config = self._original_get

    @patch("db.mysql_client.pymysql.connect")
    def test_get_by_ids_returns_rows(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "账单问题", "category_l2": "ETC扣费", "internal_process": "", "feedback_dept": ""},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_by_ids([1])
        assert len(result) == 1
        assert result[0]["question"] == "ETC扣费异常"

    @patch("db.mysql_client.pymysql.connect")
    def test_get_by_ids_empty_list(self, mock_connect):
        client = MySQLClient()
        result = client.get_by_ids([])
        assert result == []
        mock_connect.assert_not_called()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_by_id_returns_single(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "账单问题", "category_l2": "ETC扣费", "internal_process": "", "feedback_dept": ""},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_by_id(1)
        assert result["id"] == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_get_by_id_not_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_by_id(999)
        assert result is None

    @patch("db.mysql_client.pymysql.connect")
    def test_insert_qa_returns_id(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        qa_id = client.insert_qa("ETC扣费异常", "核实退款")
        assert qa_id == 42
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_all_questions(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "账单问题", "category_l2": "ETC扣费"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_all_questions()
        assert len(result) == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_update_qa_status(self, mock_connect):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.update_qa_status(1, "deprecated")
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_active_ids(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_active_ids()
        assert result == [1, 2, 3]

    @patch("db.mysql_client.pymysql.connect")
    def test_get_by_ids_filters_inactive(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "账单问题", "category_l2": "ETC扣费", "internal_process": "", "feedback_dept": ""},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_by_ids([1, 2], only_active=True)
        assert len(result) == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_get_qa_list(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"cnt": 1}
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "账单问题",
             "category_l2": "ETC扣费", "status": "active", "created_at": "2024-01-01", "updated_at": "2024-01-01"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_qa_list(page=1, page_size=20)
        assert result["total"] == 1
        assert len(result["items"]) == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_search_qa(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"cnt": 1}
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "ETC扣费异常", "answer": "核实退款", "category_l1": "账单问题",
             "category_l2": "ETC扣费", "status": "active", "created_at": "2024-01-01", "updated_at": "2024-01-01"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.search_qa(keyword="ETC")
        assert result["total"] == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_count_qa(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"status": "active", "cnt": 10},
            {"status": "deprecated", "cnt": 2},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.count_qa()
        assert result["active"] == 10
        assert result["deprecated"] == 2
        assert result["total"] == 12

    @patch("db.mysql_client.pymysql.connect")
    def test_count_work_orders(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"status": "submitted", "cnt": 5},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.count_work_orders()
        assert result["submitted"] == 5
        assert result["total"] == 5

    @patch("db.mysql_client.pymysql.connect")
    def test_get_category_stats(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"category_l1": "账单问题", "cnt": 15},
            {"category_l1": "设备问题", "cnt": 8},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_category_stats()
        assert result["账单问题"] == 15
        assert result["设备问题"] == 8

    @patch("db.mysql_client.pymysql.connect")
    def test_get_qa_detail(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "question": "ETC扣费异常", "answer": "核实退款",
            "category_l1": "账单问题", "category_l2": "ETC扣费",
            "internal_process": "核实", "feedback_dept": "账单组",
            "status": "active", "created_at": "2024-01-01", "updated_at": "2024-01-01",
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_qa_detail(1)
        assert result["id"] == 1
        assert result["question"] == "ETC扣费异常"

    @patch("db.mysql_client.pymysql.connect")
    def test_delete_qa(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.delete_qa(1)
        assert result is True

    @patch("db.mysql_client.pymysql.connect")
    def test_get_category_tree(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"category_l1": "账单问题", "category_l2": "ETC扣费"},
            {"category_l1": "账单问题", "category_l2": "发票问题"},
            {"category_l1": "设备问题", "category_l2": "OBU故障"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_category_tree()
        assert "账单问题" in result
        assert "ETC扣费" in result["账单问题"]

    @patch("db.mysql_client.pymysql.connect")
    def test_get_work_order_list(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"cnt": 3}
        mock_cursor.fetchall.return_value = [
            {"id": 1, "external_id": "WO1", "raw_data": "test", "status": "submitted",
             "created_at": "2024-01-01", "updated_at": "2024-01-01"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_work_order_list()
        assert result["total"] == 3


class TestMySQLClientNewBranches:
    def setup_method(self):
        self.mock_config = {
            "mysql": {"host": "localhost", "port": 3360, "user": "root", "password": "123456", "database": "etc_qa"},
        }
        import utils.config as cfg_module
        self._original_get = getattr(cfg_module, "get_config", None)
        cfg_module.get_config = lambda: self.mock_config

    def teardown_method(self):
        import utils.config as cfg_module
        if self._original_get:
            cfg_module.get_config = self._original_get

    @patch("db.mysql_client.pymysql.connect")
    def test_get_conn_existing_alive(self, mock_connect):
        mock_conn = MagicMock()
        mock_conn.ping.return_value = None
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client._local.conn = mock_conn
        conn = client._get_conn()
        assert conn is mock_conn
        mock_connect.assert_not_called()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_conn_existing_dead_reconnects(self, mock_connect):
        dead_conn = MagicMock()
        dead_conn.ping.side_effect = Exception("connection lost")
        new_conn = MagicMock()
        mock_connect.return_value = new_conn

        client = MySQLClient()
        client._local.conn = dead_conn
        conn = client._get_conn()
        assert conn is new_conn

    @patch("db.mysql_client.pymysql.connect")
    def test_insert_qa_exception_rollback(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("insert error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.insert_qa("q", "a")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_all_questions_exception_resets(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("query error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.get_all_questions()
            assert False
        except Exception:
            pass
        assert client._local.conn is None

    @patch("db.mysql_client.pymysql.connect")
    def test_insert_work_order(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 10
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        wo_id = client.insert_work_order("EXT-001", "问题文本")
        assert wo_id == 10
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_insert_work_order_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("wo insert error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.insert_work_order("EXT-001", "问题")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_update_work_order(self, mock_connect):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.update_work_order("EXT-001", "更新数据", "processed")
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_update_work_order_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("update wo error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.update_work_order("EXT-001", "data", "status")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_work_orders_by_status(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "external_id": "WO1", "raw_data": "test", "status": "submitted"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_work_orders_by_status("submitted")
        assert len(result) == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_delete_work_orders_by_status(self, mock_connect):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.delete_work_orders_by_status(["processed", "failed"])
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_update_qa_status_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("update status error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.update_qa_status(1, "deprecated")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_active_ids_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("active ids error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.get_active_ids()
            assert False
        except Exception:
            pass

    @patch("db.mysql_client.pymysql.connect")
    def test_get_qa_list_with_filters(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"cnt": 5}
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_qa_list(page=2, page_size=10, category_l1="售后业务", status="active")
        assert result["total"] == 5
        assert result["page"] == 2

    @patch("db.mysql_client.pymysql.connect")
    def test_search_qa_with_filters(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"cnt": 3}
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.search_qa(keyword="ETC", category_l1="售后业务", status="active")
        assert result["total"] == 3

    @patch("db.mysql_client.pymysql.connect")
    def test_count_qa_with_archived(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"status": "active", "cnt": 10},
            {"status": "archived", "cnt": 3},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.count_qa()
        assert result["archived"] == 3
        assert result["total"] == 13

    @patch("db.mysql_client.pymysql.connect")
    def test_get_qa_detail_not_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_qa_detail(999)
        assert result is None

    @patch("db.mysql_client.pymysql.connect")
    def test_delete_qa_not_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.delete_qa(999)
        assert result is False

    @patch("db.mysql_client.pymysql.connect")
    def test_delete_qa_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("delete error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.delete_qa(1)
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_work_order_list_with_status(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"cnt": 2}
        mock_cursor.fetchall.return_value = [
            {"id": 1, "external_id": "WO1", "raw_data": "test", "status": "submitted",
             "created_at": "2024-01-01", "updated_at": "2024-01-01"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_work_order_list(status="submitted")
        assert result["total"] == 2

    @patch("db.mysql_client.pymysql.connect")
    def test_get_category_tree_empty_l2(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"category_l1": "其他", "category_l2": ""},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_category_tree()
        assert "其他" in result
        assert result["其他"] == []

    @patch("db.mysql_client.pymysql.connect")
    def test_get_config_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"config_value": "value_from_db"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_config("test_key")
        assert result == "value_from_db"

    @patch("db.mysql_client.pymysql.connect")
    def test_get_config_not_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_config("missing_key", "default_val")
        assert result == "default_val"

    @patch("db.mysql_client.pymysql.connect")
    def test_get_config_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("config error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_config("bad_key", "fallback")
        assert result == "fallback"

    @patch("db.mysql_client.pymysql.connect")
    def test_set_config_string_value(self, mock_connect):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.set_config("key1", "simple_string", "desc")
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_set_config_dict_value(self, mock_connect):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.set_config("key2", {"a": 1}, "desc")
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_set_config_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("set config error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.set_config("bad_key", "val")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_get_prompt_template_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"template_text": "模板内容"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_prompt_template("judge")
        assert result == "模板内容"

    @patch("db.mysql_client.pymysql.connect")
    def test_get_prompt_template_not_found(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_prompt_template("missing")
        assert result == ""

    @patch("db.mysql_client.pymysql.connect")
    def test_get_prompt_template_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("prompt error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_prompt_template("bad_key")
        assert result == ""

    @patch("db.mysql_client.pymysql.connect")
    def test_set_prompt_template(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (3,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.set_prompt_template("judge", "新模板", "v4")
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_set_prompt_template_first_version(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client.set_prompt_template("new_key", "首个模板", "v1")
        mock_conn.commit.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_set_prompt_template_exception(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"max_ver": 1}
        mock_cursor.execute.side_effect = [None, None, Exception("set prompt error")]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        try:
            client.set_prompt_template("judge", "模板", "desc")
            assert False
        except Exception:
            pass
        mock_conn.rollback.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_reset_conn(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client._local.conn = mock_conn
        client._reset_conn()
        assert client._local.conn is None
        mock_conn.close.assert_called_once()

    @patch("db.mysql_client.pymysql.connect")
    def test_reset_conn_close_exception(self, mock_connect):
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("close error")
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        client._local.conn = mock_conn
        client._reset_conn()
        assert client._local.conn is None

    @patch("db.mysql_client.pymysql.connect")
    def test_reset_conn_no_existing(self, mock_connect):
        client = MySQLClient()
        client._local.conn = None
        client._reset_conn()
        assert client._local.conn is None

    @patch("db.mysql_client.pymysql.connect")
    def test_get_by_ids_no_active_filter(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "q", "answer": "a", "category_l1": "c1", "category_l2": "c2", "internal_process": "", "feedback_dept": ""},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_by_ids([1], only_active=False)
        assert len(result) == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_get_all_questions_no_active_filter(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "q", "answer": "a", "category_l1": "c1", "category_l2": "c2"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_all_questions(only_active=False)
        assert len(result) == 1

    @patch("db.mysql_client.pymysql.connect")
    def test_get_category_tree_duplicate_l2(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"category_l1": "售后", "category_l2": "账单"},
            {"category_l1": "售后", "category_l2": "账单"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        client = MySQLClient()
        result = client.get_category_tree()
        assert result["售后"] == ["账单"]
