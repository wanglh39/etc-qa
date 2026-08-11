import threading
import time

from jinja2 import BaseLoader, Environment, TemplateSyntaxError

from db.mysql_client import MySQLClient
from utils.config_center import get_business_config
from utils.logger import get_logger

logger = get_logger("agent.prompt_engine")

_template_cache = {}
_cache_lock = threading.Lock()
_cache_ttl = 60


class PromptEngine:
    def __init__(self):
        self._env = Environment(loader=BaseLoader())
        self._mysql = None
        self._shadow_enabled = False

    def _get_mysql(self) -> MySQLClient:
        if self._mysql is None:
            self._mysql = MySQLClient()
        return self._mysql

    def _load_template(self, prompt_key: str) -> str:
        now = time.time()
        with _cache_lock:
            if prompt_key in _template_cache:
                text, ts = _template_cache[prompt_key]
                if now - ts < _cache_ttl:
                    return text


        mysql = self._get_mysql()
        text = mysql.get_prompt_template(prompt_key)
        if text:
            with _cache_lock:
                _template_cache[prompt_key] = (text, now)
            return text
        return ""

    def _load_shadow_template(self, prompt_key: str) -> str:
        try:
            from prompt.version_manager import get_version_manager
            vm = get_version_manager()
            return vm.get_shadow_template(prompt_key) or ""
        except Exception:
            return ""

    def render(self, prompt_key: str, fallback: str = "", **overrides) -> str:
        template_text = self._load_template(prompt_key)
        if not template_text:
            template_text = fallback
        if not template_text:
            raise ValueError(f"模板{prompt_key}不存在且无fallback")

        variables = self._resolve_variables(**overrides)

        try:
            template = self._env.from_string(template_text)
            rendered = template.render(**variables)
        except TemplateSyntaxError as e:
            logger.error(f"模板{prompt_key}语法错误: {e}")
            rendered = template_text.format(**{k: str(v) for k, v in variables.items()})
        except Exception as e:
            logger.error(f"模板{prompt_key}渲染失败: {e}")
            rendered = template_text.format(**{k: str(v) for k, v in variables.items()})

        if self._shadow_enabled:
            self._run_shadow(prompt_key, variables, rendered)

        return rendered

    def _run_shadow(self, prompt_key: str, variables: dict, primary_result: str):
        try:
            shadow_text = self._load_shadow_template(prompt_key)
            if not shadow_text:
                return
            template = self._env.from_string(shadow_text)
            shadow_result = template.render(**variables)
            from prompt.shadow_recorder import record_shadow
            query = variables.get("question", "")
            record_shadow(
                prompt_key=prompt_key,
                primary_result=primary_result,
                shadow_result=shadow_result,
                query=query,
            )
        except Exception as e:
            logger.debug(f"影子测试执行失败: {e}")

    def enable_shadow(self, enabled: bool = True):
        self._shadow_enabled = enabled

    def _resolve_variables(self, **overrides) -> dict:
        variables = {
            "enterprise_name": get_business_config("enterprise_name", "ETC"),
            "brand_keywords": get_business_config("brand_keywords", ["ETC"]),
            "must_preserve_kws": get_business_config("must_preserve_kws", []),
            "forbidden_new_kws": get_business_config("forbidden_new_kws", []),
        }
        variables["brand_keywords_str"] = "、".join(variables["brand_keywords"])
        variables["must_preserve_kws_str"] = "、".join(variables["must_preserve_kws"])
        variables["forbidden_new_kws_str"] = "、".join(variables["forbidden_new_kws"])
        variables.update(overrides)
        return variables

    @staticmethod
    def invalidate_cache(prompt_key: str = None):
        with _cache_lock:
            if prompt_key:
                _template_cache.pop(prompt_key, None)
            else:
                _template_cache.clear()


_prompt_engine = None


def get_prompt_engine() -> PromptEngine:
    global _prompt_engine
    if _prompt_engine is None:
        _prompt_engine = PromptEngine()
    return _prompt_engine
