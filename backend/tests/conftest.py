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
