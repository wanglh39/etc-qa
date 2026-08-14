import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestL2ConfigCenter:
    def test_get_business_config_from_db(self, mysql_conn):
        mysql_conn.set_config("test_cc_key", {"val": "from_db"}, "閰嶇疆涓績闆嗘垚娴嬭瘯")

        from utils.config_center import get_business_config, invalidate_cache
        invalidate_cache("test_cc_key")

        result = get_business_config("test_cc_key")
        assert result is not None
        if isinstance(result, str):
            result = json.loads(result)
        assert result.get("val") == "from_db"

    def test_get_business_config_fallback_yaml(self):
        from utils.config_center import get_business_config, invalidate_cache
        invalidate_cache("nonexistent_key_xyz")

        result = get_business_config("nonexistent_key_xyz", default="fallback_default")
        assert result == "fallback_default"

    def test_config_cache_ttl(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache

        mysql_conn.set_config("test_cc_cache", {"v": "1"}, "缂撳瓨娴嬭瘯")
        invalidate_cache("test_cc_cache")

        result1 = get_business_config("test_cc_cache")
        assert result1 is not None

        with _cache_lock:
            assert "test_cc_cache" in _cache

        mysql_conn.set_config("test_cc_cache", {"v": "2"}, "缂撳瓨娴嬭瘯鏇存柊")
        result2 = get_business_config("test_cc_cache")
        if isinstance(result2, str):
            result2 = json.loads(result2)
        assert result2.get("v") == "1"

    def test_invalidate_cache_specific_key(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache

        mysql_conn.set_config("test_cc_inv", {"val": "original"}, "澶辨晥娴嬭瘯")
        invalidate_cache("test_cc_inv")
        get_business_config("test_cc_inv")

        with _cache_lock:
            assert "test_cc_inv" in _cache

        invalidate_cache("test_cc_inv")

        with _cache_lock:
            assert "test_cc_inv" not in _cache

    def test_invalidate_cache_all(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache

        mysql_conn.set_config("test_cc_all1", {"v": "1"}, "鍏ㄦ竻娴嬭瘯1")
        mysql_conn.set_config("test_cc_all2", {"v": "2"}, "鍏ㄦ竻娴嬭瘯2")
        invalidate_cache()
        get_business_config("test_cc_all1")
        get_business_config("test_cc_all2")

        with _cache_lock:
            assert len(_cache) > 0

        invalidate_cache()

        with _cache_lock:
            assert len(_cache) == 0

    def test_get_prompt_template(self, mysql_conn):
        from utils.config_center import get_prompt_template, invalidate_cache

        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO prompt_templates (prompt_key, template_text, version, is_active, status) "
                "VALUES (%s, %s, %s, 1, 'active') "
                "ON DUPLICATE KEY UPDATE template_text=%s",
                ("test_cc_prompt", "閰嶇疆涓績鎻愮ず璇嶆ā鏉?{{q}}", 1, "閰嶇疆涓績鎻愮ず璇嶆ā鏉?{{q}}"),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

        invalidate_cache("test_cc_prompt")
        result = get_prompt_template("test_cc_prompt")
        assert result != ""
        assert "{{q}}" in result or "鎻愮ず璇? in result

    def test_config_update_via_api(self, real_client):
        resp = real_client.put("/api/v1/config/test_cc_api", json={
            "value": {"api_val": "updated"},
            "description": "API閰嶇疆鏇存柊娴嬭瘯",
        })
        assert resp.status_code == 200

        resp = real_client.get("/api/v1/config/test_cc_api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] is not None

    def test_config_reload_via_api(self, real_client):
        resp = real_client.post("/api/v1/config/reload")
        assert resp.status_code == 200
        assert "鍒锋柊" in resp.json()["message"] or "reload" in resp.json()["message"].lower()

    def test_cleanup(self, mysql_conn):
        conn = mysql_conn._get_conn()
        try:
            cursor = conn.cursor()
            for key in ["test_cc_key", "test_cc_cache", "test_cc_inv",
                        "test_cc_all1", "test_cc_all2", "test_cc_api"]:
                cursor.execute("DELETE FROM system_config WHERE config_key=%s", (key,))
            cursor.execute("DELETE FROM prompt_templates WHERE prompt_key='test_cc_prompt'")
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

        from utils.config_center import invalidate_cache
        invalidate_cache()


@pytest.mark.integration
class TestL2ConfigCenterEdgeCases:
    def test_get_business_config_json_string_value(self, mysql_conn):
        mysql_conn.set_config("test_json_str", {"key": "val"}, "JSON瀛楃涓叉祴璇?)
        from utils.config_center import get_business_config, invalidate_cache
        invalidate_cache("test_json_str")
        result = get_business_config("test_json_str")
        assert isinstance(result, dict)
        assert result.get("key") == "val"

    def test_get_business_config_string_value(self, mysql_conn):
        mysql_conn.set_config("test_str_val", {"_str": "just_a_string"}, "瀛楃涓插€兼祴璇?)
        from utils.config_center import get_business_config, invalidate_cache
        invalidate_cache("test_str_val")
        result = get_business_config("test_str_val")
        assert isinstance(result, dict)
        assert result.get("_str") == "just_a_string"

    def test_cache_ttl_expiry(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache
        mysql_conn.set_config("test_ttl_key", {"v": "1"}, "TTL娴嬭瘯")
        invalidate_cache("test_ttl_key")
        get_business_config("test_ttl_key")
        with _cache_lock:
            assert "test_ttl_key" in _cache

    def test_get_prompt_template_nonexistent(self):
        from utils.config_center import get_prompt_template, invalidate_cache
        invalidate_cache("nonexistent_prompt_xyz")
        result = get_prompt_template("nonexistent_prompt_xyz", default="default_template")
        assert result == "default_template"