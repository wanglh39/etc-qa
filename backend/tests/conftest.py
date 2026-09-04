import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ETC_QA_ENV", "test")
os.environ.setdefault("ETC_QA_JWT_SECRET", "test-secret-key")
os.environ.setdefault("ETC_QA_SUPERADMIN_PASSWORD", "test-superadmin-pass")
os.environ.setdefault("ETC_QA_ADMIN_PASSWORD", "test-admin-pass")
os.environ.setdefault("ETC_QA_SERVICE_PASSWORD", "test-service-pass")
os.environ.setdefault("ETC_QA_DEPT_PASSWORD", "test-dept-pass")
os.environ.setdefault("ETC_QA_OPS_PASSWORD", "test-ops-pass")


def _noop_decorator(name=None, run_type=None):
    def decorator(func):
        return func

    return decorator


_langsmith_mock = MagicMock()
_langsmith_mock.traceable = _noop_decorator
sys.modules["langsmith"] = _langsmith_mock

_st_mock = MagicMock()
sys.modules["sentence_transformers"] = _st_mock

_pymilvus_mock = MagicMock()
sys.modules["pymilvus"] = _pymilvus_mock


_lc_openai_mock = MagicMock()
sys.modules["langchain_openai"] = _lc_openai_mock


from agent.state import AgentState


def _make_state(**kwargs):
    defaults = {
        "raw_question": "ETC扣费异常怎么处理",
        "raw_answer": "",
        "raw_context": "",
        "user_id": None,
    }
    defaults.update(kwargs)
    return AgentState(**defaults)
