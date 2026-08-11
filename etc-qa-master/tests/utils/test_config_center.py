from unittest.mock import MagicMock, patch

from utils.config_center import _cache, _cache_ts, get_business_config, get_prompt_template, invalidate_cache


class TestConfigCenter:
    def setup_method(self):
        invalidate_cache()

    @patch("utils.config_center.MySQLClient")
    @patch("utils.config_center.get_config")
    def test_returns_yaml_fallback_when_db_empty(self, mock_cfg, mock_mysql_cls):
        mock_cfg.return_value = {"prompts": {"brand_keywords": ["ETC", "etc"]}}
        mock_mysql = MagicMock()
        mock_mysql.get_config.return_value = None
        mock_mysql_cls.return_value = mock_mysql

        result = get_business_config("brand_keywords")
        assert result == ["ETC", "etc"]

    @patch("utils.config_center.MySQLClient")
    @patch("utils.config_center.get_config")
    def test_returns_db_value_when_available(self, mock_cfg, mock_mysql_cls):
        mock_cfg.return_value = {"prompts": {"brand_keywords": ["ETC"]}}
        mock_mysql = MagicMock()
        mock_mysql.get_config.return_value = '["ETC", "etc", "新品牌"]'
        mock_mysql_cls.return_value = mock_mysql

        result = get_business_config("brand_keywords")
        assert result == ["ETC", "etc", "新品牌"]

    @patch("utils.config_center.MySQLClient")
    @patch("utils.config_center.get_config")
    def test_returns_default_when_both_empty(self, mock_cfg, mock_mysql_cls):
        mock_cfg.return_value = {}
        mock_mysql = MagicMock()
        mock_mysql.get_config.return_value = None
        mock_mysql_cls.return_value = mock_mysql

        result = get_business_config("nonexistent_key", default="fallback")
        assert result == "fallback"

    @patch("utils.config_center.MySQLClient")
    def test_get_prompt_template_from_db(self, mock_mysql_cls):
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "你是ETC客服..."
        mock_mysql_cls.return_value = mock_mysql

        result = get_prompt_template("structure_ingest")
        assert result == "你是ETC客服..."

    @patch("utils.config_center.MySQLClient")
    def test_get_prompt_template_returns_default(self, mock_mysql_cls):
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        result = get_prompt_template("nonexistent", default="默认模板")
        assert result == "默认模板"

    def test_invalidate_cache_clears_all(self):
        _cache["test_key"] = "test_value"
        _cache_ts["test_key"] = 999
        invalidate_cache()
        assert len(_cache) == 0
        assert len(_cache_ts) == 0

    def test_invalidate_cache_clears_specific_key(self):
        _cache["key_a"] = "val_a"
        _cache["key_b"] = "val_b"
        invalidate_cache("key_a")
        assert "key_a" not in _cache
        assert "key_b" in _cache
