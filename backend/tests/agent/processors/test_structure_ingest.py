import json
from unittest.mock import MagicMock, patch

import pytest

from agent.output_schemas import StructureIngestOutput
from agent.processors.structure_ingest import (
    _apply_confidence_action,
    _parse_json,
    _process_parsed_result,
    _process_structured_result,
    get_category_tree,
    get_category_tree_str,
    get_reference_examples,
    invalidate_category_cache,
    invalidate_example_cache,
    structure_ingest,
)
from tests.conftest import _make_state

MOCK_TREE = {
    "售前业务": ["新办实名报错", "咨询类"],
    "售后业务": ["售后业务类", "账单类", "更换设备类", "黑名单类", "注销类", "发票类", "车队类"],
}


def _mock_tree():
    from agent.processors import structure_ingest as si_module

    si_module._category_cache["tree"] = MOCK_TREE
    si_module._category_cache["default_l1"] = "售后业务"
    si_module._category_cache["default_l2"] = "售后业务类"
    si_module._category_cache["tree_str"] = "\n".join(
        f"- {l1}: {', '.join(l2_list)}" for l1, l2_list in MOCK_TREE.items()
    )
    return MOCK_TREE


def _reset_caches():
    from agent.processors import structure_ingest as si_module

    si_module._category_cache = {"tree": None, "tree_str": None, "default_l1": None, "default_l2": None}
    si_module._example_cache = {"examples": None}


class TestStructureIngest:
    def setup_method(self):
        _reset_caches()

    def test_llm_structure_ingest(self):
        _mock_tree()
        state = _make_state(raw_question="我那个ETC扣费扣多了怎么办啊")
        state.question = "我那个ETC扣费扣多了怎么办啊"
        state.raw_answer = "请核实扣费记录后处理"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "ETC扣费异常如何处理",
                "answer": "请核实扣费记录",
                "internal_process": "核实扣费记录",
                "feedback_dept": "账单组",
                "category_l1": "售后业务",
                "category_l2": "账单类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["question"] == "ETC扣费异常如何处理"
            assert result["internal_process"] == "核实扣费记录"
            assert result["feedback_dept"] == "账单组"
            assert result["current_step"] == "structure_ingest"

    def test_already_standard_stays_same(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常如何处理")
        state.question = "ETC扣费异常如何处理"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "ETC扣费异常如何处理",
                "answer": "",
                "internal_process": "",
                "feedback_dept": "",
                "category_l1": "售后业务",
                "category_l2": "账单类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["question"] == "ETC扣费异常如何处理"

    def test_short_question_marks_review(self):
        _mock_tree()
        state = _make_state(raw_question="ETC问题")
        state.question = "ETC问题"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "AB",
                "answer": "",
                "internal_process": "",
                "feedback_dept": "",
                "category_l1": "售后业务",
                "category_l2": "售后业务类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["needs_review"] is True

    def test_llm_error_fallback(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常")
        state.question = "ETC扣费异常"
        with patch("agent.processors.structure_ingest.get_llm", side_effect=Exception("LLM error")):
            result = structure_ingest(state)
            assert result["question"] == "ETC扣费异常"
            assert result["error"] is not None

    def test_no_answer_uses_raw_answer(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常", raw_answer="原始答案")
        state.question = "ETC扣费异常"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "ETC扣费异常如何处理",
                "answer": "标准答案",
                "internal_process": "",
                "feedback_dept": "",
                "category_l1": "售后业务",
                "category_l2": "账单类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["answer"] == "标准答案"

    def test_work_order_context_in_prompt(self):
        _mock_tree()
        state = _make_state(raw_question="周卡账单逾期已对公结清", raw_answer="待支持岗核实到账并手动结清")
        state.question = "周卡账单逾期已对公结清"
        state.work_order_context = "工单类型=收款对账-划扣，流转至=支持岗，车牌号=津A13389"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "周卡逾期对公结清如何处理",
                "answer": "已收到您的对公转账，核实后将为您结清账单并恢复ETC使用",
                "internal_process": "核实对公账户到账→手动结清账单→手动解黑",
                "feedback_dept": "支持岗",
                "category_l1": "售后业务",
                "category_l2": "账单类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["feedback_dept"] == "支持岗"
            mock_llm.invoke.assert_called_once()
            call_content = mock_llm.invoke.call_args[0][0][0].content
            assert "收款对账-划扣" in call_content

    def test_hallucination_rollback(self):
        _mock_tree()
        state = _make_state(raw_question="申请开通车队权限")
        state.question = "申请开通车队权限"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "解悠ETC实名认证如何更换？",
                "answer": "在解悠小程序中操作",
                "internal_process": "",
                "feedback_dept": "",
                "category_l1": "售后业务",
                "category_l2": "更换设备类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["question"] == "申请开通车队权限"
            assert result["needs_review"] is True

    def test_lost_keyword_marks_review(self):
        _mock_tree()
        state = _make_state(raw_question="ETC设备不存电，申请更换新设备，已支付押金")
        state.question = "ETC设备不存电，申请更换新设备，已支付押金"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "ETC设备更换如何办理？",
                "answer": "安排寄出新设备",
                "internal_process": "核实押金到账→寄出新设备",
                "feedback_dept": "支持岗",
                "category_l1": "售后业务",
                "category_l2": "更换设备类",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["needs_review"] is True

    def test_category_from_db(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常")
        state.question = "ETC扣费异常"
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "ETC扣费异常如何处理",
                "answer": "核实扣费记录",
                "internal_process": "",
                "feedback_dept": "",
                "category_l1": "售前业务",
                "category_l2": "新办实名报错",
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm):
            result = structure_ingest(state)
            assert result["category_l1"] == "售前业务"
            assert result["category_l2"] == "新办实名报错"


class TestGetCategoryTree:
    def setup_method(self):
        _reset_caches()

    def test_loads_from_db_success(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = [
            {"category_l1": "售后业务", "category_l2": "账单类"},
            {"category_l1": "售后业务", "category_l2": "黑名单类"},
            {"category_l1": "售前业务", "category_l2": "咨询类"},
        ]
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            tree = get_category_tree()
        assert "售后业务" in tree
        assert "账单类" in tree["售后业务"]
        assert "黑名单类" in tree["售后业务"]
        assert "售前业务" in tree

    def test_db_returns_empty(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = []
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            tree = get_category_tree()
        assert tree == {}
        from agent.processors import structure_ingest as si_module

        assert si_module._category_cache["default_l1"] == ""
        assert si_module._category_cache["default_l2"] == ""

    def test_db_exception_fallback(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.side_effect = Exception("DB down")
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            tree = get_category_tree()
        assert tree == {}

    def test_l1_only_no_l2(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = [
            {"category_l1": "售后业务", "category_l2": ""},
        ]
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            tree = get_category_tree()
        assert "售后业务" in tree
        assert "售后业务" in tree["售后业务"]

    def test_uses_cache_on_second_call(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = [
            {"category_l1": "售后业务", "category_l2": "账单类"},
        ]
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            get_category_tree()
            get_category_tree()
        mock_mysql.get_all_questions.assert_called_once()


class TestGetCategoryTreeStr:
    def setup_method(self):
        _reset_caches()

    def test_builds_from_tree(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = [
            {"category_l1": "售后业务", "category_l2": "账单类"},
            {"category_l1": "售后业务", "category_l2": "黑名单类"},
        ]
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            tree_str = get_category_tree_str()
        assert "- 售后业务: 账单类, 黑名单类" in tree_str

    def test_empty_tree_returns_empty(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = []
        with patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql):
            tree_str = get_category_tree_str()
        assert tree_str == ""

    def test_uses_cached_tree_str(self):
        from agent.processors import structure_ingest as si_module

        si_module._category_cache["tree_str"] = "cached"
        tree_str = get_category_tree_str()
        assert tree_str == "cached"


class TestInvalidateCaches:
    def setup_method(self):
        _reset_caches()

    def test_invalidate_category_cache(self):
        from agent.processors import structure_ingest as si_module

        si_module._category_cache["tree"] = {"x": ["y"]}
        si_module._category_cache["tree_str"] = "x: y"
        si_module._category_cache["default_l1"] = "x"
        si_module._category_cache["default_l2"] = "y"
        invalidate_category_cache()
        assert si_module._category_cache["tree"] is None
        assert si_module._category_cache["tree_str"] is None
        assert si_module._category_cache["default_l1"] is None
        assert si_module._category_cache["default_l2"] is None

    def test_invalidate_example_cache(self):
        from agent.processors import structure_ingest as si_module

        si_module._example_cache["examples"] = ["q1", "q2"]
        invalidate_example_cache()
        assert si_module._example_cache["examples"] is None


class TestGetReferenceExamples:
    def setup_method(self):
        _reset_caches()

    def test_questions_insufficient_no_sampling(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.return_value = [
            {"question": "短"},
            {"question": "ETC扣费异常怎么处理"},
        ]
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"min_length": 5, "max_length": 30}
        with (
            patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql),
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
        ):
            examples = get_reference_examples(10)
        assert len(examples) == 1

    def test_db_exception_returns_empty(self):
        mock_mysql = MagicMock()
        mock_mysql.get_all_questions.side_effect = Exception("DB error")
        with (
            patch("agent.processors.structure_ingest._get_mysql", return_value=mock_mysql),
            patch("agent.processors.structure_ingest.get_config", return_value={}),
        ):
            examples = get_reference_examples(10)
        assert examples == []

    def test_uses_cached_examples(self):
        from agent.processors import structure_ingest as si_module

        si_module._example_cache["examples"] = ["q1", "q2", "q3"]
        examples = get_reference_examples(2)
        assert examples == ["q1", "q2"]


class TestApplyConfidenceAction:
    @pytest.mark.parametrize(
        "cat_conf,expected_review,expected_default,expected_highlight",
        [
            (0.9, False, False, False),
            (0.6, True, False, False),
            (0.35, True, False, True),
            (0.1, True, True, True),
        ],
    )
    def test_confidence_thresholds(self, cat_conf, expected_review, expected_default, expected_highlight):
        highlights = []
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg):
            cat_l1, cat_l2, needs_review = _apply_confidence_action(
                cat_conf, "售后业务", "账单类", "默认L1", "默认L2", highlights
            )
        assert needs_review == expected_review
        if expected_default:
            assert cat_l1 == "默认L1"
            assert cat_l2 == "默认L2"
        else:
            assert cat_l1 == "售后业务"
            assert cat_l2 == "账单类"
        if expected_highlight:
            assert len(highlights) > 0


class TestStructureIngestStructuredLLM:
    def setup_method(self):
        _reset_caches()

    def test_structured_llm_success_path(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常")
        state.question = "ETC扣费异常"
        state.raw_answer = "核实退款"
        mock_result = StructureIngestOutput(
            question="ETC扣费异常如何处理",
            answer="核实扣费记录后退款",
            category_l1="售后业务",
            category_l2="账单类",
            internal_process="核实→退款",
            feedback_dept="账单组",
            category_confidence=0.9,
        )
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = mock_result
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.structure_ingest.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.structure_ingest.get_prompt_engine", return_value=mock_pe),
            patch(
                "agent.processors.structure_ingest.get_config",
                return_value={"ingest_confidence": {"auto": 0.8, "review": 0.5, "highlight": 0.3}},
            ),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "reference_sample_count": 0,
                    "classify_examples": "示例",
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            result = structure_ingest(state)
        assert result["question"] == "ETC扣费异常如何处理"
        assert result["answer"] == "核实扣费记录后退款"
        assert result["category_confidence"] == 0.9

    def test_structured_llm_exception_degrades_to_plain_llm(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常")
        state.question = "ETC扣费异常"
        state.raw_answer = "核实退款"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.side_effect = Exception("structured error")
        mock_llm = MagicMock()
        llm_json = json.dumps(
            {
                "question": "ETC扣费异常如何处理",
                "answer": "核实退款",
                "category_l1": "售后业务",
                "category_l2": "账单类",
                "internal_process": "",
                "feedback_dept": "",
                "category_confidence": 0.8,
            }
        )
        mock_llm.invoke.return_value = MagicMock(content=llm_json)
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.structure_ingest.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm),
            patch("agent.processors.structure_ingest.get_prompt_engine", return_value=mock_pe),
            patch(
                "agent.processors.structure_ingest.get_config",
                return_value={"ingest_confidence": {"auto": 0.8, "review": 0.5, "highlight": 0.3}},
            ),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "reference_sample_count": 0,
                    "classify_examples": "示例",
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            result = structure_ingest(state)
        assert result["question"] == "ETC扣费异常如何处理"

    def test_llm_unparseable_content_returns_default(self):
        _mock_tree()
        state = _make_state(raw_question="ETC扣费异常")
        state.question = "ETC扣费异常"
        state.raw_answer = "核实退款"
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = "not a StructureIngestOutput"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="not json at all")
        mock_pe = MagicMock()
        mock_pe.return_value.render.return_value = "prompt"
        with (
            patch("agent.processors.structure_ingest.get_structured_llm", return_value=(mock_structured_llm, True)),
            patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm),
            patch("agent.processors.structure_ingest.get_prompt_engine", return_value=mock_pe),
            patch(
                "agent.processors.structure_ingest.get_config",
                return_value={"ingest_confidence": {"auto": 0.8, "review": 0.5, "highlight": 0.3}},
            ),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "reference_sample_count": 0,
                    "classify_examples": "示例",
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            result = structure_ingest(state)
        assert result["question"] == "ETC扣费异常"
        assert result["category_confidence"] == 0.3


class TestProcessStructuredResult:
    def setup_method(self):
        _reset_caches()

    def test_hallucination_plus_short_plus_default_category(self):
        _mock_tree()
        result = StructureIngestOutput(
            question="AB",
            answer="答案",
            category_l1="不存在的分类",
            category_l2="不存在的二级",
            internal_process="流程",
            feedback_dept="部门",
            category_confidence=0.1,
        )
        state = _make_state(raw_question="ETC扣费异常怎么处理")
        state.question = "ETC扣费异常怎么处理"
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": ["实名认证"],
                    "must_preserve_kws": ["ETC"],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_structured_result(
                result, "ETC扣费异常怎么处理", "答案", MOCK_TREE, "售后业务", "售后业务类", state
            )
        assert out["question"] == "ETC扣费异常怎么处理"
        assert out["needs_review"] is True
        assert out["category_l1"] == "售后业务"
        assert out["category_l2"] == "售后业务类"

    def test_category_l1_not_in_tree(self):
        _mock_tree()
        result = StructureIngestOutput(
            question="ETC问题",
            answer="答案",
            category_l1="不存在的L1",
            category_l2="任意",
            internal_process="",
            feedback_dept="",
            category_confidence=0.9,
        )
        state = _make_state(raw_question="ETC问题")
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_structured_result(result, "ETC问题", "答案", MOCK_TREE, "售后业务", "售后业务类", state)
        assert out["category_l1"] == "售后业务"
        assert out["category_l2"] == "售后业务类"

    def test_category_l2_not_in_tree_takes_first(self):
        _mock_tree()
        result = StructureIngestOutput(
            question="ETC问题",
            answer="答案",
            category_l1="售后业务",
            category_l2="不存在的L2",
            internal_process="",
            feedback_dept="",
            category_confidence=0.9,
        )
        state = _make_state(raw_question="ETC问题")
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_structured_result(result, "ETC问题", "答案", MOCK_TREE, "售后业务", "售后业务类", state)
        assert out["category_l2"] == "售后业务类"

    def test_hallucination_kws_rollback_to_original(self):
        _mock_tree()
        result = StructureIngestOutput(
            question="ETC实名认证怎么办理",
            answer="答案",
            category_l1="售后业务",
            category_l2="账单类",
            internal_process="",
            feedback_dept="",
            category_confidence=0.9,
        )
        state = _make_state(raw_question="ETC怎么办理")
        state.question = "ETC怎么办理"
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": ["实名认证"],
                    "must_preserve_kws": [],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_structured_result(result, "ETC怎么办理", "答案", MOCK_TREE, "售后业务", "售后业务类", state)
        assert out["question"] == "ETC怎么办理"
        assert out["needs_review"] is True
        assert any("改写引入不存在" in h for h in out["review_highlights"])


class TestProcessParsedResult:
    def setup_method(self):
        _reset_caches()

    def test_l2_not_in_tree(self):
        _mock_tree()
        parsed = {
            "question": "ETC问题",
            "answer": "答案",
            "category_l1": "售后业务",
            "category_l2": "不存在的L2",
            "internal_process": "",
            "feedback_dept": "",
            "category_confidence": 0.9,
        }
        state = _make_state(raw_question="ETC问题")
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_parsed_result(parsed, "ETC问题", "答案", MOCK_TREE, "售后业务", "售后业务类", state)
        assert out["category_l2"] == "售后业务类"

    def test_confidence_type_error(self):
        _mock_tree()
        parsed = {
            "question": "ETC问题",
            "answer": "答案",
            "category_l1": "售后业务",
            "category_l2": "账单类",
            "category_confidence": "not_a_number",
        }
        state = _make_state(raw_question="ETC问题")
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_parsed_result(parsed, "ETC问题", "答案", MOCK_TREE, "售后业务", "售后业务类", state)
        assert out["category_confidence"] == 0.3

    def test_l1_not_in_tree_falls_back_to_default(self):
        _mock_tree()
        parsed = {
            "question": "ETC问题",
            "answer": "答案",
            "category_l1": "不存在的L1",
            "category_l2": "任意",
            "internal_process": "",
            "feedback_dept": "",
            "category_confidence": 0.9,
        }
        state = _make_state(raw_question="ETC问题")
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {"auto": 0.8, "review": 0.5, "highlight": 0.3}
        with (
            patch("agent.processors.structure_ingest.get_config", return_value=mock_cfg),
            patch(
                "agent.processors.structure_ingest.get_business_config",
                side_effect=lambda k, d=None: {
                    "forbidden_new_kws": [],
                    "must_preserve_kws": [],
                    "standardize": {},
                }.get(k, d),
            ),
        ):
            out = _process_parsed_result(parsed, "ETC问题", "答案", MOCK_TREE, "售后业务", "售后业务类", state)
        assert out["category_l1"] == "售后业务"
        assert out["category_l2"] == "售后业务类"


class TestParseJson:
    def test_valid_json(self):
        assert _parse_json('{"key": "value"}') == {"key": "value"}

    def test_extract_json_from_text(self):
        text = 'Here is the result: {"key": "value"} end'
        assert _parse_json(text) == {"key": "value"}

    def test_completely_invalid(self):
        assert _parse_json("no json here") is None

    def test_extract_still_invalid(self):
        assert _parse_json("prefix {broken json} suffix") is None
