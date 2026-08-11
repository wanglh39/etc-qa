import json
import threading
import time

from db.mysql_client import MySQLClient
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("utils.config_center")

_cache = {}
_cache_ts = {}
_cache_lock = threading.Lock()
_ttl = get_config().get("cache", {}).get("config_ttl", 60)


def get_business_config(key: str, default=None):
    now = time.time()
    with _cache_lock:
        if key in _cache and (now - _cache_ts.get(key, 0)) < _ttl:
            return _cache[key]

    yaml_value = get_config().get("prompts", {}).get(key, get_config().get(key))

    try:
        mysql = MySQLClient()
        db_value = mysql.get_config(key)
        if db_value is not None:
            if isinstance(db_value, str):
                try:
                    db_value = json.loads(db_value)
                except (json.JSONDecodeError, TypeError):
                    pass
            with _cache_lock:
                _cache[key] = db_value
                _cache_ts[key] = now
            return db_value
    except Exception as e:
        logger.debug(f"DB config read failed for {key}: {e}, using yaml fallback")

    with _cache_lock:
        _cache[key] = yaml_value
        _cache_ts[key] = now
    return yaml_value if yaml_value is not None else default


def get_prompt_template(key: str, default: str = "") -> str:
    cache_key = f"__prompt__{key}"
    now = time.time()
    with _cache_lock:
        if cache_key in _cache and (now - _cache_ts.get(cache_key, 0)) < _ttl:
            return _cache[cache_key]

    try:
        mysql = MySQLClient()
        db_value = mysql.get_prompt_template(key)
        if db_value:
            with _cache_lock:
                _cache[cache_key] = db_value
                _cache_ts[cache_key] = now
            return db_value
    except Exception as e:
        logger.debug(f"DB prompt read failed for {key}: {e}, using default")

    with _cache_lock:
        _cache[cache_key] = default
        _cache_ts[cache_key] = now
    return default


def invalidate_cache(key: str = None):
    with _cache_lock:
        if key is None:
            _cache.clear()
            _cache_ts.clear()
        else:
            _cache.pop(key, None)
            _cache_ts.pop(key, None)
            _cache.pop(f"__prompt__{key}", None)
            _cache_ts.pop(f"__prompt__{key}", None)
