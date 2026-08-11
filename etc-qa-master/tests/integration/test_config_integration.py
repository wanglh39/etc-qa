import json

import pytest


@pytest.mark.integration
class TestL2ConfigCenter:
    def test_get_business_config_from_db(self, mysql_conn):
        mysql_conn.set_config("test_cc_key", {"val": "from_db"}, "配置中心集成测试")

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

        mysql_conn.set_config("test_cc_cache", {"v": "1"}, "缓存测试")
        invalidate_cache("test_cc_cache")

        result1 = get_business_config("test_cc_cache")
        assert result1 is not None

        with _cache_lock:
            assert "test_cc_cache" in _cache

        mysql_conn.set_config("test_cc_cache", {"v": "2"}, "缓存测试更新")
        result2 = get_business_config("test_cc_cache")
        if isinstance(result2, str):
            result2 = json.loads(result2)
        assert result2.get("v") == "1"

    def test_invalidate_cache_specific_key(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache

        mysql_conn.set_config("test_cc_inv", {"val": "original"}, "失效测试")
        invalidate_cache("test_cc_inv")
        get_business_config("test_cc_inv")

        with _cache_lock:
            assert "test_cc_inv" in _cache

        invalidate_cache("test_cc_inv")

        with _cache_lock:
            assert "test_cc_inv" not in _cache

    def test_invalidate_cache_all(self, mysql_conn):
        from utils.config_center import _cache, _cache_lock, get_business_config, invalidate_cache

        mysql_conn.set_config("test_cc_all1", {"v": "1"}, "全清测试1")
        mysql_conn.set_config("test_cc_all2", {"v": "2"}, "全清测试2")
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
                ("test_cc_prompt", "配置中心提示词模板 {{q}}", 1, "配置中心提示词模板 {{q}}"),
            )
            conn.commit()
            cursor.close()
        except Exception:
            conn.rollback()
            mysql_conn._reset_conn()

        invalidate_cache("test_cc_prompt")
        result = get_prompt_template("test_cc_prompt")
        assert result != ""
        assert "{{q}}" in result or "提示词" in result

    def test_config_update_via_api(self, real_client):
        resp = real_client.put("/api/v1/config/test_cc_api", json={
            "value": {"api_val": "updated"},
            "description": "API配置更新测试",
        })
        assert resp.status_code == 200

        resp = real_client.get("/api/v1/config/test_cc_api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] is not None

    def test_config_reload_via_api(self, real_client):
        resp = real_client.post("/api/v1/config/reload")
        assert resp.status_code == 200
        assert "刷新" in resp.json()["message"] or "reload" in resp.json()["message"].lower()

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
