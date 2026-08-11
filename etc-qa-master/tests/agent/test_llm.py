from unittest.mock import MagicMock, patch

from agent.llm import _get_structured_method, _llm_cache, _structured_cache, get_llm, get_structured_llm


class TestGetLLM:
    def setup_method(self):
        _llm_cache.clear()
        _structured_cache.clear()

    @patch("agent.llm.get_config")
    @patch("agent.llm.ChatOpenAI")
    def test_creates_llm_with_config(self, mock_chat_cls, mock_cfg):
        mock_cfg.return_value = {
            "llm": {
                "enabled": True,
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "temperature": 0.1,
                "max_tokens": 1024,
            }
        }
        mock_chat = MagicMock()
        mock_chat_cls.return_value = mock_chat

        result = get_llm()
        assert result is mock_chat
        mock_chat_cls.assert_called_once_with(
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.deepseek.com",
            temperature=0.1,
            max_tokens=1024,
        )

    @patch("agent.llm.get_config")
    def test_raises_when_disabled(self, mock_cfg):
        mock_cfg.return_value = {
            "llm": {"enabled": False}
        }
        try:
            get_llm()
            assert False
        except RuntimeError as e:
            assert "LLM未启用" in str(e)

    @patch("agent.llm.get_config")
    @patch("agent.llm.ChatOpenAI")
    def test_caches_llm_instance(self, mock_chat_cls, mock_cfg):
        mock_cfg.return_value = {
            "llm": {
                "enabled": True,
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "temperature": 0.1,
                "max_tokens": 1024,
            }
        }
        mock_chat_cls.return_value = MagicMock()

        get_llm()
        get_llm()
        assert mock_chat_cls.call_count == 1


class TestGetStructuredMethod:
    @patch("agent.llm.get_config")
    def test_explicit_method(self, mock_cfg):
        mock_cfg.return_value = {"llm": {"structured_method": "json_schema"}, "llm_registry": {}}
        result = _get_structured_method("any-model")
        assert result == "json_schema"

    @patch("agent.llm.get_config")
    def test_explicit_none(self, mock_cfg):
        mock_cfg.return_value = {"llm": {"structured_method": "none"}, "llm_registry": {}}
        result = _get_structured_method("any-model")
        assert result is None

    @patch("agent.llm.get_config")
    def test_registry_method(self, mock_cfg):
        mock_cfg.return_value = {
            "llm": {},
            "llm_registry": {"deepseek-v4-flash": {"structured_method": "json_schema"}},
        }
        result = _get_structured_method("deepseek-v4-flash")
        assert result == "json_schema"

    @patch("agent.llm.get_config")
    def test_registry_none(self, mock_cfg):
        mock_cfg.return_value = {
            "llm": {},
            "llm_registry": {"some-model": {"structured_method": "none"}},
        }
        result = _get_structured_method("some-model")
        assert result is None

    @patch("agent.llm.get_config")
    def test_no_method_anywhere(self, mock_cfg):
        mock_cfg.return_value = {"llm": {}, "llm_registry": {}}
        result = _get_structured_method("unknown-model")
        assert result is None


class TestGetStructuredLLM:
    def setup_method(self):
        _llm_cache.clear()
        _structured_cache.clear()

    @patch("agent.llm.get_config")
    @patch("agent.llm.ChatOpenAI")
    def test_unsupported_returns_plain(self, mock_chat_cls, mock_cfg):
        mock_cfg.return_value = {
            "llm": {
                "enabled": True,
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            "llm_registry": {"deepseek-v4-flash": {"structured_method": "none"}},
        }
        mock_chat = MagicMock()
        mock_chat.model = "deepseek-v4-flash"
        mock_chat_cls.return_value = mock_chat

        from agent.output_schemas import StandardizeOutput
        llm, supported = get_structured_llm(StandardizeOutput)
        assert supported is False
        assert llm is mock_chat

    @patch("agent.llm.get_config")
    @patch("agent.llm.ChatOpenAI")
    def test_supported_returns_structured(self, mock_chat_cls, mock_cfg):
        mock_cfg.return_value = {
            "llm": {
                "enabled": True,
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com",
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            "llm_registry": {"gpt-4o": {"structured_method": "json_schema"}},
        }
        mock_chat = MagicMock()
        mock_chat.model = "gpt-4o"
        mock_structured = MagicMock()
        mock_chat.with_structured_output.return_value = mock_structured
        mock_chat_cls.return_value = mock_chat

        from agent.output_schemas import StandardizeOutput
        llm, supported = get_structured_llm(StandardizeOutput)
        assert supported is True
        assert llm is mock_structured

    @patch("agent.llm.get_config")
    @patch("agent.llm.ChatOpenAI")
    def test_structured_init_failure_degrades(self, mock_chat_cls, mock_cfg):
        mock_cfg.return_value = {
            "llm": {
                "enabled": True,
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com",
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            "llm_registry": {"gpt-4o": {"structured_method": "json_schema"}},
        }
        mock_chat = MagicMock()
        mock_chat.model = "gpt-4o"
        mock_chat.with_structured_output.side_effect = Exception("not supported")
        mock_chat_cls.return_value = mock_chat

        from agent.output_schemas import StandardizeOutput
        llm, supported = get_structured_llm(StandardizeOutput)
        assert supported is False
        assert llm is mock_chat

    @patch("agent.llm.get_config")
    @patch("agent.llm.ChatOpenAI")
    def test_cached_structured_llm(self, mock_chat_cls, mock_cfg):
        mock_cfg.return_value = {
            "llm": {
                "enabled": True,
                "provider": "deepseek",
                "model": "deepseek-v4-flash",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            "llm_registry": {"deepseek-v4-flash": {"structured_method": "none"}},
        }
        mock_chat = MagicMock()
        mock_chat.model = "deepseek-v4-flash"
        mock_chat_cls.return_value = mock_chat

        from agent.output_schemas import StandardizeOutput
        get_structured_llm(StandardizeOutput)
        get_structured_llm(StandardizeOutput)
        assert mock_chat.with_structured_output.call_count == 0
