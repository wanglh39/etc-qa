import json
from unittest.mock import MagicMock, patch

from agent.output_schemas import HydeJudgeOutput, HydeRewriteOutput
from agent.processors.hyde_rewrite import (
    _judge_need_rewrite,
    _parse_json,
    hyde_rewrite,
)
from tests.conftest import _make_state


def _mock_config():
    cfg = MagicMock()
    cfg.get.side_effect = lambda k, d=None: {
        "hyde": {
            "conditional": True,
            "num_questions": 3,
            "max_questions_per_qa": 3,
            "answer_summary_max_len": 150,
        },
    }.get(k, d)
    return cfg


def _mock_business_config():
    return lambda k, d=None: {
        "standardize": {"min_length": 5, "max_length": 30},
        "brand_keywords": ["ETC", "解悠"],
        "subject_keywords": ["扣费", "注销"],
        "question_words": ["怎么", "如何", "为什么"],
        "enterprise_name": "ETC",
        "hyde_judge_no_rewrite_examples": "",
        "hyde_judge_rewrite_examples": "",
        "hyde_examples": "",
    }.get(k, d)


class TestJudgeNeedRewrite:
    def test_conditional_false(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": False}}.get(k, d)
        with patch("agent.processors.hyde_rewrite.get_config", return_value=cfg):
            need, reason = _judge_need_rewrite("any question", "any answer")
        assert need is True
        assert "conditional" in reason

    def test_standard_question_skips(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
        ):
            need, reason = _judge_need_rewrite("ETC扣费异常怎么处理", "答案")
        assert need is False
        assert "跳过" in reason

    def test_structured_llm_needs_rewrite(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        mock_result = HydeJudgeOutput(need_rewrite=True, reason="问题冗长")
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
        ):
            need, reason = _judge_need_rewrite("我上个月在同一个高速口被扣了两次费", "答案")
        assert need is True
        assert "冗长" in reason

    def test_structured_llm_no_rewrite(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        mock_result = HydeJudgeOutput(need_rewrite=False, reason="已简洁")
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
        ):
            need, reason = _judge_need_rewrite("非标准问题但也不太长", "答案")
        assert need is False

    def test_structured_llm_exception_degrades_to_plain(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.side_effect = Exception("structured error")
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=json.dumps({"need_rewrite": True, "reason": "降级判断"}))
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.hyde_rewrite.get_llm", return_value=mock_llm),
        ):
            need, reason = _judge_need_rewrite("非标准问题", "答案")
        assert need is True

    def test_overall_exception_defaults_to_rewrite(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        mock_pe = MagicMock()
        mock_pe.return_value.render.side_effect = Exception("render error")
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
        ):
            need, reason = _judge_need_rewrite("非标准问题", "答案")
        assert need is True
        assert "默认" in reason


class TestHydeRewriteStructuredDegradation:
    def test_structured_llm_rewrite_exception_degrades(self):
        mock_result = HydeRewriteOutput(questions=["问法1", "问法2", "问法3"])
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.side_effect = Exception("structured rewrite error")
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="问法A\n问法B\n问法C")
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=_mock_config()),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite._judge_need_rewrite", return_value=(True, "需要改写")),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.hyde_rewrite.get_llm", return_value=mock_llm),
        ):
            state = _make_state(question="ETC扣费异常", answer="核实退款")
            result = hyde_rewrite(state)
        assert len(result["hyde_questions"]) == 3

    def test_structured_llm_success_returns_questions_slice(self):
        mock_result = HydeRewriteOutput(questions=["问法1", "问法2", "问法3", "问法4"])
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=_mock_config()),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite._judge_need_rewrite", return_value=(True, "需要改写")),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
        ):
            state = _make_state(question="ETC扣费异常", answer="核实退款")
            result = hyde_rewrite(state)
        assert result["hyde_questions"] == ["问法1", "问法2", "问法3"]
        assert result["current_step"] == "hyde_rewrite"


class TestHydeRewriteMainBranches:
    def test_empty_question_skips(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        with patch("agent.processors.hyde_rewrite.get_config", return_value=cfg):
            state = _make_state(raw_question="", question="", answer="有答案")
            result = hyde_rewrite(state)
        assert result["hyde_questions"] == []

    def test_empty_answer_skips(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        with patch("agent.processors.hyde_rewrite.get_config", return_value=cfg):
            state = _make_state(question="有问题", answer="")
            result = hyde_rewrite(state)
        assert result["hyde_questions"] == []

    def test_judge_skip_rewrite(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite._judge_need_rewrite", return_value=(False, "问题简洁标准，跳过HyDE")),
        ):
            state = _make_state(question="ETC怎么注销", answer="注销流程说明")
            result = hyde_rewrite(state)
        assert result["hyde_questions"] == []

    def test_structured_llm_not_hyde_output_type_degrades(self):
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not HydeRewriteOutput"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="问法A\n问法B\n问法C")
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=_mock_config()),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite._judge_need_rewrite", return_value=(True, "需要改写")),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.hyde_rewrite.get_llm", return_value=mock_llm),
        ):
            state = _make_state(question="ETC扣费异常", answer="核实退款")
            result = hyde_rewrite(state)
        assert len(result["hyde_questions"]) == 3

    def test_full_exception_returns_error(self):
        mock_pe = MagicMock()
        mock_pe.render.side_effect = Exception("render error")
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=_mock_config()),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite._judge_need_rewrite", return_value=(True, "需要改写")),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
        ):
            state = _make_state(question="ETC扣费异常", answer="核实退款")
            result = hyde_rewrite(state)
        assert result["hyde_questions"] == []
        assert "HyDE改写失败" in result["error"]

    def test_judge_need_rewrite_plain_llm_parsed_returns(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not HydeJudgeOutput"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=json.dumps({"need_rewrite": False, "reason": "已简洁"}))
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.hyde_rewrite.get_llm", return_value=mock_llm),
        ):
            need, reason = _judge_need_rewrite("非标准问题", "答案")
        assert need is False
        assert "已简洁" in reason

    def test_judge_need_rewrite_plain_llm_no_parse_defaults(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda k, d=None: {"hyde": {"conditional": True}}.get(k, d)
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.side_effect = Exception("err")
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="not json")
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.hyde_rewrite.get_config", return_value=cfg),
            patch("agent.processors.hyde_rewrite.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.hyde_rewrite.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.hyde_rewrite.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.hyde_rewrite.get_llm", return_value=mock_llm),
        ):
            need, reason = _judge_need_rewrite("非标准问题", "答案")
        assert need is True
        assert "默认" in reason


class TestParseJson:
    def test_valid_json(self):
        assert _parse_json('{"key": "value"}') == {"key": "value"}

    def test_extract_json_from_text(self):
        text = 'Result: {"need_rewrite": true} done'
        assert _parse_json(text) == {"need_rewrite": True}

    def test_completely_invalid(self):
        assert _parse_json("no json here") is None

    def test_extract_still_invalid(self):
        assert _parse_json("prefix {broken} suffix") is None
