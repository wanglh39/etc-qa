from unittest.mock import MagicMock, patch

from prompt.shadow_recorder import clear_records, flush_to_db, get_shadow_records, get_shadow_stats, record_shadow


class TestShadowRecorder:
    def setup_method(self):
        clear_records()

    def teardown_method(self):
        clear_records()

    def test_record_no_diff(self):
        record_shadow("judge", "result A", "result A", query="ETC扣费异常")
        stats = get_shadow_stats()
        assert stats["total"] == 1
        assert stats["diff_count"] == 0
        assert stats["diff_rate"] == 0.0

    def test_record_with_diff(self):
        record_shadow("judge", "result A", "result B", query="ETC扣费异常")
        stats = get_shadow_stats()
        assert stats["total"] == 1
        assert stats["diff_count"] == 1
        assert stats["diff_rate"] == 1.0

    def test_multiple_records(self):
        record_shadow("judge", "A", "A", query="q1")
        record_shadow("judge", "B", "C", query="q2")
        record_shadow("hyde", "D", "D", query="q3")
        stats = get_shadow_stats()
        assert stats["total"] == 3
        assert stats["diff_count"] == 1
        assert stats["diff_rate"] == 1 / 3

    def test_stats_by_key(self):
        record_shadow("judge", "A", "B", query="q1")
        record_shadow("judge", "C", "C", query="q2")
        record_shadow("hyde", "D", "E", query="q3")
        stats = get_shadow_stats()
        assert stats["by_key"]["judge"]["total"] == 2
        assert stats["by_key"]["judge"]["diff"] == 1
        assert stats["by_key"]["hyde"]["total"] == 1
        assert stats["by_key"]["hyde"]["diff"] == 1

    def test_get_records_all(self):
        record_shadow("judge", "A", "A", query="q1")
        record_shadow("judge", "B", "C", query="q2")
        records = get_shadow_records()
        assert len(records) == 2

    def test_get_records_diff_only(self):
        record_shadow("judge", "A", "A", query="q1")
        record_shadow("judge", "B", "C", query="q2")
        records = get_shadow_records(diff_only=True)
        assert len(records) == 1
        assert records[0]["diff"] is True

    def test_get_records_by_key(self):
        record_shadow("judge", "A", "A", query="q1")
        record_shadow("hyde", "B", "C", query="q2")
        records = get_shadow_records(prompt_key="hyde")
        assert len(records) == 1

    def test_get_records_limit(self):
        for i in range(10):
            record_shadow("judge", f"A{i}", f"B{i}", query=f"q{i}")
        records = get_shadow_records(limit=3)
        assert len(records) == 3

    def test_clear_records(self):
        record_shadow("judge", "A", "B", query="q1")
        clear_records()
        stats = get_shadow_stats()
        assert stats["total"] == 0

    def test_record_truncates_long_text(self):
        long_primary = "A" * 600
        long_shadow = "B" * 600
        long_query = "Q" * 300
        record_shadow("judge", long_primary, long_shadow, query=long_query)
        records = get_shadow_records()
        assert len(records[0]["primary_result"]) == 500
        assert len(records[0]["shadow_result"]) == 500
        assert len(records[0]["query"]) == 200

    def test_stats_empty(self):
        stats = get_shadow_stats()
        assert stats["total"] == 0
        assert stats["diff_rate"] == 0.0

    @patch("prompt.shadow_recorder.MySQLClient")
    def test_flush_to_db_success(self, mock_mysql_cls):
        record_shadow("judge", "A", "B", query="q1")
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        flush_to_db()
        assert mock_conn.commit.call_count >= 1

    @patch("prompt.shadow_recorder.MySQLClient")
    def test_flush_to_db_exception(self, mock_mysql_cls):
        record_shadow("judge", "A", "B", query="q1")
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("db error")
        mock_mysql._get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        flush_to_db()
        mock_mysql._reset_conn.assert_called_once()
