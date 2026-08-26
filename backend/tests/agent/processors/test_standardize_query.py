import json
from unittest.mock import MagicMock, patch

from agent.output_schemas import StandardizeOutput
from agent.processors.standardize_query import (
    _is_already_standard,
    _parse_json,
    _preserves_keywords,
    standardize_query,
)
from tests.conftest import _make_state


def _mock_business_config():
    return lambda k, d=None: {
        "filler_patterns": [r"我想问一下", r"啊$"],
        "core_patterns": [{"pattern": r"咋整", "replacement": "如何处理"}],
        "brand_keywords": ["ETC", "解悠"],
        "subject_keywords": ["扣费", "注销"],
        "question_words": ["怎么", "如何", "为什么", "多少", "能不能"],
        "preserve_question_words": ["怎么", "如何", "为什么"],
        "enterprise_name": "ETC",
        "judge_no_rewrite_examples": "",
        "judge_rewrite_examples": "",
    }.get(k, d)


def _mock_config():
    cfg = MagicMock()
    cfg.get.side_effect = lambda k, d=None: {
        "prompts": {"standardize": {"min_length": 5, "max_length": 30, "rewrite_min_length": 3}},
        "rewrite_confidence": {"accept": 0.5, "fallback": 0.5},
    }.get(k, d)
    return cfg


class TestStandardizeQuery:
    def test_rule_based_removes_filler(self):
        state = _make_state(raw_question="我想问一下ETC扣费异常怎么处理啊")
        state.question = "我想问一下ETC扣费异常怎么处理啊"
        result = standardize_query(state)
        assert "我想问" not in result["question"]
        assert "啊" not in result["question"]
        assert result["current_step"] == "standardize_query"

    def test_already_standard_skips_llm(self):
        state = _make_state(raw_question="ETC扣费异常如何处理？")
        state.question = "ETC扣费异常如何处理？"
        with patch("agent.processors.standardize_query.get_llm") as mock_llm:
            result = standardize_query(state)
            mock_llm.assert_not_called()
            assert result["question"] == "ETC扣费异常如何处理"
            assert result["rewrite_confidence"] == 1.0

    def test_rule_handles_colloquial_without_llm(self):
        state = _make_state(raw_question="那个ETC扣多了咋整")
        state.question = "那个ETC扣多了咋整"
        with patch("agent.processors.standardize_query.get_llm") as mock_llm:
            result = standardize_query(state)
            mock_llm.assert_not_called()
            assert "ETC" in result["question"]
            assert "如何处理" in result["question"]
            assert result["rewrite_confidence"] == 1.0

    def test_llm_error_fallback(self):
        state = _make_state(raw_question="ETC扣费异常")
        state.question = "ETC扣费异常"
        with patch("agent.processors.standardize_query.get_llm", side_effect=Exception("LLM error")):
            result = standardize_query(state)
            assert "ETC" in result["question"]
            assert result["rewrite_confidence"] == 0.5

    def test_short_llm_result_keeps_original(self):
        state = _make_state(raw_question="ETC扣费异常怎么处理")
        state.question = "ETC扣费异常怎么处理"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="AB")
        with patch("agent.processors.standardize_query.get_llm", return_value=mock_llm):
            result = standardize_query(state)
            assert result["question"] != "AB"


class TestStructuredLLMBranches:
    def test_structured_llm_no_rewrite_needed(self):
        state = _make_state(raw_question="我想问一下ETC注销流程是什么呢")
        state.question = "我想问一下ETC注销流程是什么呢"
        mock_result = StandardizeOutput(need_rewrite=False, reason="已简洁", rewritten="", rewrite_confidence=1.0)
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert result["rewrite_confidence"] == 1.0

    def test_structured_llm_rewrite_accepted(self):
        state = _make_state(raw_question="我想问一下ETC注销的流程是什么呢")
        state.question = "我想问一下ETC注销的流程是什么呢"
        mock_result = StandardizeOutput(
            need_rewrite=True, reason="冗余", rewritten="ETC注销流程是什么", rewrite_confidence=0.9
        )
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert result["question"] == "ETC注销流程是什么"
        assert result["rewrite_confidence"] == 0.9

    def test_structured_llm_rewrite_confidence_too_low(self):
        state = _make_state(raw_question="我想问一下ETC注销的流程是什么呢")
        state.question = "我想问一下ETC注销的流程是什么呢"
        mock_result = StandardizeOutput(
            need_rewrite=True, reason="冗余", rewritten="ETC注销流程是什么", rewrite_confidence=0.2
        )
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert "ETC注销" not in result["question"] or result["rewrite_confidence"] == 0.2

    def test_structured_llm_exception_degrades_to_plain_llm(self):
        state = _make_state(raw_question="我想问一下ETC注销的流程是什么呢")
        state.question = "我想问一下ETC注销的流程是什么呢"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.side_effect = Exception("structured error")
        mock_llm = MagicMock()
        llm_json = json.dumps({"need_rewrite": True, "rewritten": "ETC注销流程是什么", "rewrite_confidence": 0.8})
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_llm", return_value=mock_llm),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert result["current_step"] == "standardize_query"


class TestPlainLLMBranches:
    def test_plain_llm_no_rewrite_needed(self):
        state = _make_state(raw_question="我想问一下ETC注销的流程是什么呢")
        state.question = "我想问一下ETC注销的流程是什么呢"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not StandardizeOutput"
        mock_llm = MagicMock()
        llm_json = json.dumps({"need_rewrite": False, "rewritten": "", "rewrite_confidence": 1.0})
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_llm", return_value=mock_llm),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert result["rewrite_confidence"] == 1.0

    def test_plain_llm_confidence_type_error(self):
        state = _make_state(raw_question="我想问一下ETC注销的流程是什么呢")
        state.question = "我想问一下ETC注销的流程是什么呢"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not StandardizeOutput"
        mock_llm = MagicMock()
        llm_json = json.dumps({"need_rewrite": True, "rewritten": "ETC注销流程", "rewrite_confidence": "bad"})
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_llm", return_value=mock_llm),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert result["rewrite_confidence"] == 0.5

    def test_plain_llm_keyword_not_preserved_rejects_rewrite(self):
        state = _make_state(raw_question="ETC扣费异常怎么处理")
        state.question = "ETC扣费异常怎么处理"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not StandardizeOutput"
        mock_llm = MagicMock()
        llm_json = json.dumps({"need_rewrite": True, "rewritten": "扣费异常如何处理", "rewrite_confidence": 0.9})
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_llm", return_value=mock_llm),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert "ETC" in result["question"]

    def test_plain_llm_confidence_too_low_rejects_rewrite(self):
        state = _make_state(raw_question="我想问一下ETC注销的流程是什么呢")
        state.question = "我想问一下ETC注销的流程是什么呢"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not StandardizeOutput"
        mock_llm = MagicMock()
        llm_json = json.dumps({"need_rewrite": True, "rewritten": "ETC注销流程是什么", "rewrite_confidence": 0.2})
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.standardize_query.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.standardize_query.get_llm", return_value=mock_llm),
            patch("agent.processors.standardize_query.get_prompt_engine", return_value=mock_pe),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
        ):
            result = standardize_query(state)
        assert result["question"] == "ETC注销的流程是什么呢"
        assert result["rewrite_confidence"] == 0.2


class TestIsAlreadyStandard:
    def test_length_out_of_range(self):
        with (
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
        ):
            assert _is_already_standard("短") is False
            assert _is_already_standard("A" * 50) is False

    def test_no_subject_keyword(self):
        with (
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
        ):
            assert _is_already_standard("这个问题怎么处理") is False

    def test_standard_question(self):
        with (
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
        ):
            assert _is_already_standard("ETC扣费异常怎么处理") is True

    def test_multi_sentence_not_standard(self):
        with (
            patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()),
            patch("agent.processors.standardize_query.get_config", return_value=_mock_config()),
        ):
            assert _is_already_standard("啊。ETC扣费异常怎么处理") is False
            assert _is_already_standard("ETC扣费异常。怎么处理") is False
            assert _is_already_standard("ETC扣费异常;怎么处理") is False


class TestPreservesKeywords:
    def test_brand_keyword_lost(self):
        with patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()):
            assert _preserves_keywords("ETC扣费异常", "扣费异常如何处理") is False

    def test_question_word_lost(self):
        with patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()):
            assert _preserves_keywords("ETC怎么注销", "ETC注销流程") is False

    def test_all_preserved(self):
        with patch("agent.processors.standardize_query.get_business_config", side_effect=_mock_business_config()):
            assert _preserves_keywords("ETC怎么注销", "ETC怎么注销流程") is True


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
