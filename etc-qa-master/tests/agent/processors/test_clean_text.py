from agent.processors.clean_text import clean_text
from tests.conftest import _make_state


class TestCleanText:
    def test_normalizes_spaces(self):
        state = _make_state(raw_question="ETC  扣费   异常")
        state.question = "ETC  扣费   异常"
        result = clean_text(state)
        assert "  " not in result["question"]

    def test_skips_if_duplicate(self):
        state = _make_state(raw_question="test")
        state.is_duplicate = True
        result = clean_text(state)
        assert result["current_step"] == "clean_text"

    def test_cleans_answer_too(self):
        state = _make_state(raw_question="ETC扣费异常", raw_answer="核实后  退款")
        state.question = "ETC扣费异常"
        state.answer = "核实后  退款"
        result = clean_text(state)
        assert "  " not in result["answer"]

    def test_strips_work_order_prefix(self):
        state = _make_state(raw_question="客户刘伟（电话：13533218196）反馈：客户周卡账单逾期，已对公结清")
        state.question = "客户刘伟（电话：13533218196）反馈：客户周卡账单逾期，已对公结清"
        result = clean_text(state)
        assert "刘伟" not in result["question"]
        assert "13533218196" not in result["question"]
        assert "周卡账单逾期" in result["question"]

    def test_strips_work_order_prefix_half_width(self):
        state = _make_state(raw_question="客户张三(电话:13800001111)反馈:ETC不抬杆")
        state.question = "客户张三(电话:13800001111)反馈:ETC不抬杆"
        result = clean_text(state)
        assert "张三" not in result["question"]
        assert "ETC不抬杆" in result["question"]
