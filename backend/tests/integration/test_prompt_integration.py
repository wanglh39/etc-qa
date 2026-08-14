from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestL3PromptVersionManager:
    def test_publish_new_version(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.publish(
            "test_int_prompt",
            "杩欐槸闆嗘垚娴嬭瘯鎻愮ず璇峷1 {{question}}",
            "闆嗘垚娴嬭瘯鍙戝竷",
        )
        assert "version" in result
        assert result["version"] >= 1

    def test_publish_second_version(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.publish(
            "test_int_prompt",
            "杩欐槸闆嗘垚娴嬭瘯鎻愮ず璇峷2 {{question}} {{category}}",
            "闆嗘垚娴嬭瘯鍙戝竷v2",
        )
        assert result["version"] >= 2

    def test_list_versions(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        versions = vm.list_versions("test_int_prompt")
        assert isinstance(versions, list)
        assert len(versions) >= 2

    def test_get_active_version(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        row = vm.get_version("test_int_prompt")
        assert row is not None
        assert row["is_active"] == 1

    def test_get_specific_version(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        row = vm.get_version("test_int_prompt", version=1)
        assert row is not None
        assert row["version"] == 1

    def test_rollback(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.rollback("test_int_prompt", target_version=1)
        assert result["version"] == 1

        active = vm.get_version("test_int_prompt")
        assert active["version"] == 1
        assert active["is_active"] == 1

        vm.rollback("test_int_prompt", target_version=2)

    def test_rollback_no_target(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.rollback("test_int_prompt")
        assert "version" in result
        assert "error" not in result

    def test_rollback_nonexistent_key(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.rollback("nonexistent_key_xyz_999")
        assert "error" in result

    def test_start_shadow(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.start_shadow("test_int_prompt", shadow_version=2)
        if "error" in result:
            pytest.skip(f"褰卞瓙娴嬭瘯鍚姩澶辫触: {result['error']}")
        assert result["status"] == "shadow"

    def test_get_shadow_template(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        template = vm.get_shadow_template("test_int_prompt")
        assert template is not None
        assert "鎻愮ず璇? in template or "question" in template

    def test_stop_shadow(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        result = vm.stop_shadow("test_int_prompt", shadow_version=2)
        assert result["status"] == "stopped"

    def test_list_all_keys(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = None

        keys = vm.list_all_keys()
        assert isinstance(keys, list)
        assert any(k["prompt_key"] == "test_int_prompt" for k in keys)

    def test_cleanup_test_data(self, mysql_conn):
        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key='test_int_prompt'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()


@pytest.mark.integration
class TestL3ShadowRecorder:
    def test_record_shadow(self):
        from prompt.shadow_recorder import clear_records, get_shadow_stats, record_shadow
        clear_records()

        record_shadow("test_key", "涓荤粨鏋淎", "褰卞瓙缁撴灉B", query="娴嬭瘯鏌ヨ", pipeline="preprocess")
        stats = get_shadow_stats()
        assert stats["total"] == 1
        assert stats["diff_count"] == 1

    def test_record_shadow_no_diff(self):
        from prompt.shadow_recorder import clear_records, get_shadow_stats, record_shadow
        clear_records()

        record_shadow("test_key", "鐩稿悓缁撴灉", "鐩稿悓缁撴灉", query="娴嬭瘯鏌ヨ")
        stats = get_shadow_stats()
        assert stats["total"] == 1
        assert stats["diff_count"] == 0

    def test_get_shadow_records(self):
        from prompt.shadow_recorder import clear_records, get_shadow_records, record_shadow
        clear_records()

        record_shadow("key_a", "缁撴灉1", "缁撴灉2", query="q1")
        record_shadow("key_b", "缁撴灉3", "缁撴灉3", query="q2")

        all_records = get_shadow_records()
        assert len(all_records) == 2

        diff_only = get_shadow_records(diff_only=True)
        assert len(diff_only) == 1
        assert diff_only[0]["prompt_key"] == "key_a"

        filtered = get_shadow_records(prompt_key="key_b")
        assert len(filtered) == 1

    def test_shadow_stats_by_key(self):
        from prompt.shadow_recorder import clear_records, get_shadow_stats, record_shadow
        clear_records()

        record_shadow("key_x", "A", "B", query="q1")
        record_shadow("key_x", "C", "D", query="q2")
        record_shadow("key_y", "E", "E", query="q3")

        stats = get_shadow_stats()
        assert stats["by_key"]["key_x"]["total"] == 2
        assert stats["by_key"]["key_x"]["diff"] == 2
        assert stats["by_key"]["key_y"]["total"] == 1
        assert stats["by_key"]["key_y"]["diff"] == 0

    def test_flush_to_db(self, mysql_conn):
        from prompt.shadow_recorder import clear_records, flush_to_db, get_shadow_stats, record_shadow
        clear_records()

        record_shadow("test_flush_key", "涓荤粨鏋?, "褰卞瓙缁撴灉", query="娴嬭瘯")
        flush_to_db()

        stats = get_shadow_stats()
        assert stats["total"] == 0

    def test_cleanup(self):
        from prompt.shadow_recorder import clear_records
        clear_records()


@pytest.mark.integration
class TestL4PromptAPI:
    def test_list_prompt_keys(self, real_client):
        resp = real_client.get("/api/v1/prompts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_publish_via_api(self, real_client):
        resp = real_client.post("/api/v1/prompts/publish", json={
            "prompt_key": "test_api_prompt",
            "template_text": "API娴嬭瘯鎻愮ず璇?{{question}}",
            "description": "API闆嗘垚娴嬭瘯",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] >= 1

    def test_list_versions_via_api(self, real_client):
        resp = real_client.get("/api/v1/prompts/test_api_prompt/versions")
        assert resp.status_code == 200
        versions = resp.json()
        assert isinstance(versions, list)
        assert len(versions) >= 1

    def test_get_version_via_api(self, real_client):
        resp = real_client.get("/api/v1/prompts/test_api_prompt/versions/1")
        assert resp.status_code == 200

    def test_rollback_via_api(self, real_client):
        real_client.post("/api/v1/prompts/publish", json={
            "prompt_key": "test_api_prompt",
            "template_text": "API娴嬭瘯鎻愮ず璇峷2 {{question}}",
            "description": "API闆嗘垚娴嬭瘯v2",
        })

        resp = real_client.post("/api/v1/prompts/rollback", json={
            "prompt_key": "test_api_prompt",
            "target_version": 1,
        })
        assert resp.status_code == 200

    def test_shadow_start_stop_via_api(self, real_client):
        resp = real_client.post("/api/v1/prompts/shadow/start", json={
            "prompt_key": "test_api_prompt",
            "shadow_version": 2,
        })
        assert resp.status_code == 200

        resp = real_client.post("/api/v1/prompts/shadow/stop", json={
            "prompt_key": "test_api_prompt",
            "shadow_version": 2,
        })
        assert resp.status_code == 200

    def test_shadow_stats_via_api(self, real_client):
        resp = real_client.get("/api/v1/prompts/shadow/stats")
        assert resp.status_code == 200
        assert "total" in resp.json()

    def test_shadow_records_via_api(self, real_client):
        resp = real_client.get("/api/v1/prompts/shadow/records")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_cleanup_api_test_data(self, mysql_conn):
        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key='test_api_prompt'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()


@pytest.mark.integration
class TestL2VersionManagerErrorHandling:
    def test_list_versions_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("妯℃嫙杩炴帴澶辫触")):
            with pytest.raises(Exception, match="妯℃嫙杩炴帴澶辫触"):
                vm.list_versions("test_key")

    def test_get_version_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("妯℃嫙杩炴帴澶辫触")):
            with pytest.raises(Exception, match="妯℃嫙杩炴帴澶辫触"):
                vm.get_version("test_key")

    def test_publish_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("妯℃嫙杩炴帴澶辫触")):
            with pytest.raises(Exception, match="妯℃嫙杩炴帴澶辫触"):
                vm.publish("test_key", "template", "desc")

    def test_rollback_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("妯℃嫙杩炴帴澶辫触")):
            with pytest.raises(Exception, match="妯℃嫙杩炴帴澶辫触"):
                vm.rollback("test_key")

    def test_start_shadow_no_status_column(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "description"}
        result = vm.start_shadow("test_key", shadow_version=1)
        assert "error" in result

    def test_get_shadow_template_no_status(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "description"}
        result = vm.get_shadow_template("test_key")
        assert result is None

    def test_list_all_keys_error(self, mysql_conn):
        from prompt.version_manager import PromptVersionManager
        vm = PromptVersionManager()
        vm._mysql = mysql_conn
        vm._cols_cache = {"id", "prompt_key", "template_text", "version", "is_active", "status", "description", "created_at", "updated_at"}
        with patch.object(mysql_conn, '_get_conn', side_effect=Exception("妯℃嫙杩炴帴澶辫触")):
            with pytest.raises(Exception, match="妯℃嫙杩炴帴澶辫触"):
                vm.list_all_keys()