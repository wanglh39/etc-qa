from agent.state import AgentState


class TestAgentState:
    def test_default_values(self):
        state = AgentState(raw_question="ETC扣费异常")
        assert state.question == ""
        assert state.is_duplicate is False
        assert state.needs_review is False
        assert state.review_highlights == []
        assert state.current_step == "start"

    def test_custom_values(self):
        state = AgentState(
            raw_question="ETC扣费异常",
            raw_answer="核实后退款",
            raw_context="用户来电咨询",
            user_id="user001",
        )
        assert state.raw_answer == "核实后退款"
        assert state.raw_context == "用户来电咨询"
        assert state.user_id == "user001"

    def test_mutable_defaults_isolated(self):
        state1 = AgentState(raw_question="test1")
        state2 = AgentState(raw_question="test2")
        state1.review_highlights.append("test")
        assert state2.review_highlights == []
