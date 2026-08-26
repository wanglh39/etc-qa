import os
import re

import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG = None
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def _resolve_env_vars(obj):
    if isinstance(obj, str):

        def _replace(match):
            var_name = match.group(1)
            default = match.group(2)
            value = os.environ.get(var_name)
            if value is not None:
                return value
            if default is not None:
                return default
            return match.group(0)

        return _ENV_VAR_PATTERN.sub(_replace, obj)
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _flatten_env_config(raw: dict, env: str) -> dict:
    flat = {}
    for key, value in raw.items():
        if isinstance(value, dict) and any(k in value for k in ("dev", "test", "prod")):
            flat[key] = value.get(env, value.get("dev", {}))
        else:
            flat[key] = value
    return flat


def load_config(config_path=None):
    global _CONFIG
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw = _resolve_env_vars(raw)
    env = os.environ.get("ETC_QA_ENV", raw.get("env", "dev"))

    merged = {"env": env}
    includes = raw.pop("includes", [])

    merged = _deep_merge(merged, _flatten_env_config(raw, env))

    config_dir = os.path.dirname(os.path.abspath(config_path))
    for inc_path in includes:
        abs_inc = os.path.join(config_dir, inc_path)
        if not os.path.exists(abs_inc):
            continue
        with open(abs_inc, encoding="utf-8") as f:
            inc_raw = yaml.safe_load(f) or {}
        inc_raw = _resolve_env_vars(inc_raw)
        merged = _deep_merge(merged, _flatten_env_config(inc_raw, env))

    _CONFIG = merged
    return _CONFIG


def validate_config() -> list:
    from config.schemas import validate_config as _validate

    cfg = get_config()
    return _validate(cfg)


def get_config():
    global _CONFIG
    if _CONFIG is None:
        load_config()
    return _CONFIG
