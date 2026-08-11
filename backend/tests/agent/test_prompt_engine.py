import time
from unittest.mock import MagicMock, patch

from agent.prompt_engine import PromptEngine, _template_cache, get_prompt_engine


def _clear_cache():
    _template_cache.clear()


class TestPromptEngineRender:
    def setup_method(self):
        _clear_cache()

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_render_with_fallback(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: {
            "enterprise_name": "ETC",
            "brand_keywords": ["ETC"],
            "must_preserve_kws": [],
            "forbidden_new_kws": [],
        }.get(key, default)
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        fallback = "你好{{enterprise_name}}，品牌:{{brand_keywords_str}}"
        result = engine.render("test_key", fallback)

        assert "ETC" in result
        assert "品牌:ETC" in result

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_db_template_takes_priority(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "DB模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("test_key", "fallback: {{enterprise_name}}")
        assert result == "DB模板: ETC"

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_no_template_no_fallback_raises(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        try:
            engine.render("no_exist", "")
            assert False, "应抛ValueError"
        except ValueError:
            pass

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_overrides_replace_variables(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("key", "问题:{{question}}", question="我的ETC坏了")
        assert "问题:我的ETC坏了" in result

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_template_cache_hit(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "缓存模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        engine.render("cache_key", "fallback")
        engine.render("cache_key", "fallback")
        assert mock_mysql.get_prompt_template.call_count == 1

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_invalidate_cache_forces_reload(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        engine.render("inv_key", "fallback")
        PromptEngine.invalidate_cache("inv_key")
        engine.render("inv_key", "fallback")
        assert mock_mysql.get_prompt_template.call_count == 2

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_invalidate_all_cache(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        engine.render("key_a", "fallback")
        engine.render("key_b", "fallback")
        PromptEngine.invalidate_cache()
        assert len(_template_cache) == 0


class TestPromptEngineShadowAndEdgeCases:
    def setup_method(self):
        _clear_cache()

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_load_shadow_template_success(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        mock_vm = MagicMock()
        mock_vm.get_shadow_template.return_value = "shadow: {{enterprise_name}}"

        engine = PromptEngine()
        with patch("agent.prompt_engine.get_business_config", side_effect=mock_cfg), \
             patch("prompt.version_manager.get_version_manager", return_value=mock_vm):
            shadow_text = engine._load_shadow_template("judge")
        assert shadow_text == "shadow: {{enterprise_name}}"

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_load_shadow_template_exception(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        with patch("prompt.version_manager.get_version_manager", side_effect=ImportError("no module")):
            shadow_text = engine._load_shadow_template("judge")
        assert shadow_text == ""

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_template_syntax_error_fallback(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        with patch.object(engine._env, "from_string", side_effect=Exception("syntax error")):
            result = engine.render("bad_key", "fallback: {enterprise_name}", enterprise_name="ETC")
        assert "ETC" in result

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_render_exception_fallback(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        mock_template = MagicMock()
        mock_template.render.side_effect = Exception("render crash")
        with patch.object(engine._env, "from_string", return_value=mock_template):
            result = engine.render("err_key", "问题: {question}", question="测试")
        assert "测试" in result

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_shadow_enabled_runs_shadow(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: {
            "enterprise_name": "ETC",
            "brand_keywords": ["ETC"],
            "must_preserve_kws": [],
            "forbidden_new_kws": [],
        }.get(key, default)
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        mock_vm = MagicMock()
        mock_vm.get_shadow_template.return_value = "shadow: {{enterprise_name}}"

        with patch("prompt.version_manager.get_version_manager", return_value=mock_vm), \
             patch("prompt.shadow_recorder.record_shadow") as mock_record:
            engine = PromptEngine()
            engine.enable_shadow(True)
            result = engine.render("shadow_key", "主模板: {{enterprise_name}}")
            assert result == "主模板: ETC"
            mock_record.assert_called_once()

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_shadow_enabled_no_shadow_template(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: {
            "enterprise_name": "ETC",
            "brand_keywords": ["ETC"],
            "must_preserve_kws": [],
            "forbidden_new_kws": [],
        }.get(key, default)
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        mock_vm = MagicMock()
        mock_vm.get_shadow_template.return_value = ""

        with patch("prompt.version_manager.get_version_manager", return_value=mock_vm), \
             patch("prompt.shadow_recorder.record_shadow") as mock_record:
            engine = PromptEngine()
            engine.enable_shadow(True)
            result = engine.render("no_shadow_key", "主模板: {{enterprise_name}}")
            assert result == "主模板: ETC"
            mock_record.assert_not_called()

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_shadow_exception_does_not_break(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: {
            "enterprise_name": "ETC",
            "brand_keywords": ["ETC"],
            "must_preserve_kws": [],
            "forbidden_new_kws": [],
        }.get(key, default)
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        mock_vm = MagicMock()
        mock_vm.get_shadow_template.return_value = "shadow: {{enterprise_name}}"
        mock_vm.get_shadow_template.side_effect = Exception("vm error")

        with patch("prompt.version_manager.get_version_manager", return_value=mock_vm):
            engine = PromptEngine()
            engine.enable_shadow(True)
            result = engine.render("err_shadow_key", "主模板: {{enterprise_name}}")
            assert result == "主模板: ETC"

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_enable_shadow_toggle(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        assert engine._shadow_enabled is False
        engine.enable_shadow(True)
        assert engine._shadow_enabled is True
        engine.enable_shadow(False)
        assert engine._shadow_enabled is False

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_cache_expired_reloads(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        engine.render("ttl_key", "fallback")
        _template_cache["ttl_key"] = (_template_cache["ttl_key"][0], time.time() - 100)
        engine.render("ttl_key", "fallback")
        assert mock_mysql.get_prompt_template.call_count == 2

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_db_returns_empty_uses_fallback(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("empty_db_key", "fallback: {{enterprise_name}}")
        assert result == "fallback: ETC"


class TestGetPromptEngine:
    def test_singleton(self):
        _clear_cache()
        e1 = get_prompt_engine()
        e2 = get_prompt_engine()
        assert e1 is e2
