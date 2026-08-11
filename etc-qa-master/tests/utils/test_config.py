import os

from utils.config import _resolve_env_vars, get_config, load_config


class TestConfig:
    def setup_method(self):
        os.environ.pop("ETC_QA_ENV", None)

    def test_resolve_env_vars_no_substitution(self):
        result = _resolve_env_vars("hello")
        assert result == "hello"

    def test_resolve_env_vars_with_env(self):
        os.environ["TEST_VAR_123"] = "world"
        result = _resolve_env_vars("${TEST_VAR_123}")
        assert result == "world"
        os.environ.pop("TEST_VAR_123", None)

    def test_resolve_env_vars_with_default(self):
        os.environ.pop("NONEXIST_VAR_XYZ", None)
        result = _resolve_env_vars("${NONEXIST_VAR_XYZ:default_val}")
        assert result == "default_val"

    def test_resolve_env_vars_env_overrides_default(self):
        os.environ["EXIST_VAR_456"] = "from_env"
        result = _resolve_env_vars("${EXIST_VAR_456:default}")
        assert result == "from_env"
        os.environ.pop("EXIST_VAR_456", None)

    def test_load_config_returns_dict(self):
        cfg = load_config()
        assert isinstance(cfg, dict)
        assert "mysql" in cfg
        assert "milvus" in cfg

    def test_get_config_caches(self):
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2
