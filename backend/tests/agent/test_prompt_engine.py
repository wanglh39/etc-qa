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


class TestPromptEngineEdgeCases:
    def setup_method(self):
        _clear_cache()

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

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_render_template_syntax_error_degrades(self, mock_mysql_cls, mock_cfg):
        from jinja2 import TemplateSyntaxError

        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        with patch.object(engine._env, "from_string", side_effect=TemplateSyntaxError("syntax error", 1)):
            result = engine.render("bad_syntax_key", "fallback: {enterprise_name}", enterprise_name="ETC")
        assert "ETC" in result


class TestPromptEngineFileTemplate:
    def setup_method(self):
        _clear_cache()

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_load_file_template_success(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        text = engine._load_file_template("judge")
        assert text != ""
        assert "{{enterprise_name}}" in text
        assert "{{question}}" in text

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_load_file_template_not_found(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        text = engine._load_file_template("nonexistent_key_xyz")
        assert text == ""

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_file_template_takes_priority_over_db(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "DB模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("judge", "fallback: {{enterprise_name}}")
        assert "DB模板" not in result
        assert "客服问题标准化助手" in result
        assert mock_mysql.get_prompt_template.call_count == 0

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_file_template_takes_priority_over_fallback(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("judge", "fallback: {{enterprise_name}}")
        assert "客服问题标准化助手" in result
        assert "fallback" not in result

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_db_used_when_file_not_found(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = "DB模板: {{enterprise_name}}"
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("custom_key_no_file", "fallback: {{enterprise_name}}")
        assert result == "DB模板: ETC"

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_fallback_used_when_neither_file_nor_db(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render("no_file_no_db", "fallback: {{enterprise_name}}")
        assert result == "fallback: ETC"

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_file_template_renders_with_variables(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: {
            "enterprise_name": "ETC",
            "brand_keywords": ["ETC", "etc"],
            "must_preserve_kws": [],
            "forbidden_new_kws": [],
        }.get(key, default)
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        result = engine.render(
            "judge",
            "fallback",
            question="我的ETC坏了",
            min_length=5,
            max_length=30,
            judge_no_rewrite_examples="示例",
            judge_rewrite_examples="示例",
        )
        assert "ETC" in result
        assert "我的ETC坏了" in result

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_file_template_cached_no_db_call(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql.get_prompt_template.return_value = ""
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        engine.render("judge", "fallback")
        engine.render("judge", "fallback")
        assert mock_mysql.get_prompt_template.call_count == 0

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_all_four_templates_loadable(self, mock_mysql_cls, mock_cfg):
        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        for key in ("judge", "hyde_judge", "hyde", "structure_ingest"):
            text = engine._load_file_template(key)
            assert text != "", f"{key}.j2应存在且非空"
            assert "{{enterprise_name}}" in text, f"{key}.j2应包含enterprise_name变量"

    @patch("agent.prompt_engine.get_business_config")
    @patch("agent.prompt_engine.MySQLClient")
    def test_load_file_template_read_exception(self, mock_mysql_cls, mock_cfg):
        from pathlib import Path

        mock_cfg.side_effect = lambda key, default=None: "ETC" if key == "enterprise_name" else default
        mock_mysql = MagicMock()
        mock_mysql_cls.return_value = mock_mysql

        engine = PromptEngine()
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "read_text", side_effect=OSError("read error")),
        ):
            text = engine._load_file_template("judge")
        assert text == ""


class TestGetPromptEngine:
    def test_singleton(self):
        _clear_cache()
        e1 = get_prompt_engine()
        e2 = get_prompt_engine()
        assert e1 is e2
