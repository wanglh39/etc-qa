import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ETC_QA_ENV", "test")

if "langsmith" in sys.modules:
    sys.modules.pop("langsmith", None)


def _noop_decorator(name=None, run_type=None):
    def decorator(func):
        return func
    return decorator


_langsmith_mock = MagicMock()
_langsmith_mock.traceable = _noop_decorator
sys.modules["langsmith"] = _langsmith_mock


from agent.state import AgentState


def _make_state(**kwargs):
    defaults = {
        "raw_question": "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊",
        "raw_answer": "",
        "raw_context": "",
        "user_id": None,
    }
    defaults.update(kwargs)
    return AgentState(**defaults)