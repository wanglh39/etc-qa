from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestL3ProcessorsWithLLM:
    def test_standardize_oral_question(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(raw_question="我想问一下ETC扣费扣多了怎么办啊，上个月在高速口被多扣了")
        result = standardize_query(state)
        assert "question" in result
        assert result["question"] != ""
        assert "ETC" in result["question"] or "etc" in result["question"].lower()

    def test_standardize_already_standard(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(raw_question="ETC扣费异常怎么处理")
        result = standardize_query(state)
        assert "ETC" in result["question"]
        assert "扣费异常" in result["question"]

    def test_standardize_very_short(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(raw_question="ETC")
        result = standardize_query(state)
        assert "question" in result

    def test_standardize_long_oral_triggers_llm(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(
            raw_question="客户打电话来说他上个月在同一个高速出口被ETC扣了两次费想知道这个多扣的钱什么时候能退回来啊"
        )
        result = standardize_query(state)
        assert "question" in result
        assert result["question"] != ""
        assert len(result["question"]) < len(state.raw_question)
        assert result["current_step"] == "standardize_query"

    def test_standardize_no_brand_keyword(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(raw_question="我想问一下重复扣费了怎么申请退款啊这个钱能退回来吗")
        result = standardize_query(state)
        assert "question" in result
        assert result["current_step"] == "standardize_query"

    def test_structure_ingest_normal(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="ETC重复扣费怎么退款",
            raw_answer="核实扣费记录后3个工作日退款到原支付账户",
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "category_l1" in result
        assert "category_confidence" in result
        assert result["current_step"] == "structure_ingest"

    def test_structure_ingest_oral(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="我上个月在同一个高速口被扣了两次费怎么办啊，多扣的那次能退吗",
            raw_answer="经核实确属重复扣费，将在3个工作日内将多扣款项退回原支付账户，请关注账户变动",
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "category_l1" in result

    def test_structure_ingest_with_context(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="ETC设备OBU显示异常",
            raw_answer="更换OBU设备，费用50元",
            work_order_context="流转至设备运维部处理",
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "internal_process" in result or "feedback_dept" in result

    def test_structure_ingest_ambiguous(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="这个不知道怎么弄",
            raw_answer="已处理",
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "category_l1" in result

    def test_hyde_rewrite_long_question_triggers_llm(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(
            raw_question="客户打电话来说他上个月在同一个高速出口被ETC扣了两次费想知道这个多扣的钱什么时候能退回来啊",
            raw_answer="核实扣费记录后3个工作日退款到原支付账户，如需帮助请拨打95022",
        )
        result = hyde_rewrite(state)
        assert "hyde_questions" in result
        assert result["current_step"] == "hyde_rewrite"

    def test_hyde_rewrite_standard_question_skips(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(
            raw_question="ETC扣费异常怎么处理",
            raw_answer="请检查扣费记录，如确认异常可申请退款",
        )
        result = hyde_rewrite(state)
        assert "hyde_questions" in result
        assert result["current_step"] == "hyde_rewrite"

    def test_hyde_rewrite_no_answer(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(raw_question="ETC扣费异常", raw_answer="")
        result = hyde_rewrite(state)
        assert result["hyde_questions"] == []

    def test_hyde_rewrite_no_brand_keyword(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(
            raw_question="重复扣费了怎么申请退款这个钱能退回来吗什么时候到账呢",
            raw_answer="核实后3个工作日退款到原支付账户",
        )
        result = hyde_rewrite(state)
        assert "hyde_questions" in result
        assert result["current_step"] == "hyde_rewrite"

    def test_category_tree_loading(self):
        from agent.processors.structure_ingest import (
            get_category_tree,
            get_category_tree_str,
            invalidate_category_cache,
        )

        invalidate_category_cache()
        tree = get_category_tree()
        assert isinstance(tree, dict)
        if tree:
            tree_str = get_category_tree_str()
            assert isinstance(tree_str, str)
            assert len(tree_str) > 0

    def test_reference_examples(self):
        from agent.processors.structure_ingest import get_reference_examples, invalidate_example_cache

        invalidate_example_cache()
        examples = get_reference_examples(5)
        assert isinstance(examples, list)

    def test_validate_rewrite(self):
        from agent.processors.structure_ingest import _validate_rewrite

        hallucination, lost = _validate_rewrite("ETC扣费异常", "ETC扣费异常怎么处理")
        assert isinstance(hallucination, list)
        assert isinstance(lost, list)

    def test_apply_confidence_action(self):
        from agent.processors.structure_ingest import _apply_confidence_action

        l1, l2, needs = _apply_confidence_action(0.9, "售后业务", "扣费异常", "售后业务", "扣费异常", [])
        assert needs is False

        l1, l2, needs = _apply_confidence_action(0.6, "售后业务", "扣费异常", "售后业务", "扣费异常", [])
        assert needs is True

        l1, l2, needs = _apply_confidence_action(0.2, "售后业务", "扣费异常", "售后业务", "扣费异常", [])
        assert needs is True
        assert l1 == "售后业务"

    def test_apply_confidence_action_highlight(self):
        from agent.processors.structure_ingest import _apply_confidence_action

        highlights = []
        l1, l2, needs = _apply_confidence_action(0.35, "售后业务", "扣费异常", "售后业务", "扣费异常", highlights)
        assert needs is True
        assert len(highlights) > 0

    def test_category_tree_with_empty_l2(self, mysql_conn):
        from agent.processors.structure_ingest import get_category_tree, invalidate_category_cache

        qa_id = mysql_conn.insert_qa(
            question="集成测试空l2分类", answer="答案", category_l1="测试分类L1", category_l2=""
        )
        mysql_conn.update_qa_status(qa_id, "active")
        invalidate_category_cache()
        tree = get_category_tree()
        assert "测试分类L1" in tree
        mysql_conn.delete_qa(qa_id)
        invalidate_category_cache()
        assert "测试分类L1" in tree
        mysql_conn.delete_qa(qa_id)
        invalidate_category_cache()

    def test_process_parsed_result_invalid_category(self, mysql_conn):
        from agent.processors.structure_ingest import (
            _process_parsed_result,
            get_category_tree,
            invalidate_category_cache,
        )
        from agent.state import AgentState

        invalidate_category_cache()
        tree = get_category_tree()
        default_l1 = next(iter(tree)) if tree else ""
        default_l2 = tree[default_l1][0] if tree and tree.get(default_l1) else ""

        state = AgentState(raw_question="测试", raw_answer="答案")
        parsed = {
            "question": "ETC测试问题",
            "answer": "测试答案",
            "category_l1": "不存在的分类",
            "category_l2": "不存在的子分类",
            "category_confidence": 0.8,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "测试", "答案", tree, default_l1, default_l2, state)
        assert result["category_l1"] == default_l1

    def test_process_parsed_result_short_rewrite(self, mysql_conn):
        from agent.processors.structure_ingest import (
            _process_parsed_result,
            get_category_tree,
            invalidate_category_cache,
        )
        from agent.state import AgentState

        invalidate_category_cache()
        tree = get_category_tree()
        default_l1 = next(iter(tree)) if tree else ""
        default_l2 = tree[default_l1][0] if tree and tree.get(default_l1) else ""

        state = AgentState(raw_question="ETC扣费异常怎么处理", raw_answer="答案")
        parsed = {
            "question": "E",
            "answer": "测试答案",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC扣费异常怎么处理", "答案", tree, default_l1, default_l2, state)
        assert result["needs_review"] is True

    def test_process_parsed_result_hallucination(self, mysql_conn):
        from agent.processors.structure_ingest import (
            _process_parsed_result,
            get_category_tree,
            invalidate_category_cache,
        )
        from agent.state import AgentState

        invalidate_category_cache()
        tree = get_category_tree()
        default_l1 = next(iter(tree)) if tree else ""
        default_l2 = tree[default_l1][0] if tree and tree.get(default_l1) else ""

        state = AgentState(raw_question="ETC扣费异常", raw_answer="答案")
        parsed = {
            "question": "信用卡盗刷怎么处理",
            "answer": "测试答案",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC扣费异常", "答案", tree, default_l1, default_l2, state)
        assert "question" in result

    def test_parse_json_valid(self):
        from agent.processors.hyde_rewrite import _parse_json

        result = _parse_json('{"need_rewrite": true, "reason": "test"}')
        assert result is not None
        assert result["need_rewrite"] is True

    def test_parse_json_with_surrounding_text(self):
        from agent.processors.hyde_rewrite import _parse_json

        result = _parse_json('some text {"need_rewrite": false} more text')
        assert result is not None
        assert result["need_rewrite"] is False

    def test_parse_json_invalid(self):
        from agent.processors.hyde_rewrite import _parse_json

        result = _parse_json("not json at all")
        assert result is None

    def test_parse_json_structure_ingest(self):
        from agent.processors.structure_ingest import _parse_json

        result = _parse_json('{"question": "ETC扣费", "category_l1": "售后"}')
        assert result is not None
        assert result["question"] == "ETC扣费"

    def test_parse_json_standardize(self):
        from agent.processors.standardize_query import _parse_json

        result = _parse_json('{"need_rewrite": true, "rewritten": "ETC退款"}')
        assert result is not None

    def test_preserves_keywords(self):
        from agent.processors.standardize_query import _preserves_keywords

        assert _preserves_keywords("ETC扣费异常", "ETC扣费异常怎么处理") is True
        assert _preserves_keywords("ETC扣费异常", "扣费异常怎么处理") is False

    def test_parse_json_nested_failure(self):
        from agent.processors.structure_ingest import _parse_json

        result = _parse_json("{invalid json content}")
        assert result is None

    def test_parse_json_standardize_fallback(self):
        from agent.processors.standardize_query import _parse_json

        result = _parse_json('text {"bad": } json')
        assert result is None

    def test_parse_json_hyde_nested_failure(self):
        from agent.processors.hyde_rewrite import _parse_json

        result = _parse_json("{broken")
        assert result is None

    def test_process_parsed_result_lost_keywords(self, mysql_conn):
        from agent.processors.structure_ingest import (
            _process_parsed_result,
            get_category_tree,
            invalidate_category_cache,
        )
        from agent.state import AgentState

        invalidate_category_cache()
        tree = get_category_tree()
        default_l1 = next(iter(tree)) if tree else ""
        default_l2 = tree[default_l1][0] if tree and tree.get(default_l1) else ""

        state = AgentState(raw_question="ETC扣费异常", raw_answer="答案")
        parsed = {
            "question": "扣费异常怎么处理",
            "answer": "测试答案",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC扣费异常", "答案", tree, default_l1, default_l2, state)
        assert result["needs_review"] is True

    def test_process_parsed_result_invalid_confidence(self, mysql_conn):
        from agent.processors.structure_ingest import (
            _process_parsed_result,
            get_category_tree,
            invalidate_category_cache,
        )
        from agent.state import AgentState

        invalidate_category_cache()
        tree = get_category_tree()
        default_l1 = next(iter(tree)) if tree else ""
        default_l2 = tree[default_l1][0] if tree and tree.get(default_l1) else ""

        state = AgentState(raw_question="ETC测试", raw_answer="答案")
        parsed = {
            "question": "ETC测试问题",
            "answer": "测试答案",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": "not_a_number",
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC测试", "答案", tree, default_l1, default_l2, state)
        assert "category_confidence" in result

    def test_process_parsed_result_invalid_l2(self, mysql_conn):
        from agent.processors.structure_ingest import (
            _process_parsed_result,
            get_category_tree,
            invalidate_category_cache,
        )
        from agent.state import AgentState

        invalidate_category_cache()
        tree = get_category_tree()
        default_l1 = next(iter(tree)) if tree else ""
        default_l2 = tree[default_l1][0] if tree and tree.get(default_l1) else ""

        state = AgentState(raw_question="ETC测试", raw_answer="答案")
        parsed = {
            "question": "ETC测试问题",
            "answer": "测试答案",
            "category_l1": default_l1,
            "category_l2": "不存在的子分类",
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC测试", "答案", tree, default_l1, default_l2, state)
        assert "category_l2" in result


@pytest.mark.integration
class TestL2StructureIngestStructuredResult:
    def test_process_structured_result_invalid_l1(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC设备故障",
            answer="请检查OBU设备",
            category_l1="不存在的分类",
            category_l2="子分类",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常", "账单问题"]}
        result = _process_structured_result(
            mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state
        )
        assert result["category_l1"] == "售后业务"
        assert result["category_l2"] == "设备异常"

    def test_process_structured_result_invalid_l2(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC扣费异常",
            answer="请查看账单",
            category_l1="售后业务",
            category_l2="不存在的子分类",
            category_confidence=0.8,
            internal_process="查看账单",
            feedback_dept="客服部",
        )
        state = AgentState(raw_question="ETC扣费异常", raw_answer="请查看账单")
        tree = {"售后业务": ["设备异常", "账单问题"]}
        result = _process_structured_result(
            mock_result, "ETC扣费异常", "请查看账单", tree, "售后业务", "设备异常", state
        )
        assert result["category_l1"] == "售后业务"
        assert result["category_l2"] == "设备异常"

    def test_process_structured_result_hallucination(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC设备故障银行卡退款",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch("agent.processors.structure_ingest._get_kw_lists", return_value=(["银行卡", "退款"], ["ETC"])):
            result = _process_structured_result(
                mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state
            )
        assert result["question"] == "ETC设备故障"
        assert result["needs_review"] is True

    def test_process_structured_result_lost_keywords(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="设备故障",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch("agent.processors.structure_ingest._get_kw_lists", return_value=(["银行卡"], ["ETC"])):
            result = _process_structured_result(
                mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state
            )
        assert result["needs_review"] is True

    def test_process_structured_result_short_rewrite(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="E",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.8,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch("agent.processors.structure_ingest._get_kw_lists", return_value=(["银行卡"], ["ETC"])):
            result = _process_structured_result(
                mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state
            )
        assert result["question"] == "ETC设备故障"
        assert result["needs_review"] is True

    def test_process_structured_result_low_confidence(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC设备故障",
            answer="请检查OBU设备",
            category_l1="售后业务",
            category_l2="设备异常",
            category_confidence=0.2,
            internal_process="检查设备",
            feedback_dept="运维部",
        )
        state = AgentState(raw_question="ETC设备故障", raw_answer="请检查OBU设备")
        tree = {"售后业务": ["设备异常"]}
        with patch("agent.processors.structure_ingest._get_kw_lists", return_value=(["银行卡"], ["ETC"])):
            result = _process_structured_result(
                mock_result, "ETC设备故障", "请检查OBU设备", tree, "售后业务", "设备异常", state
            )
        assert result["needs_review"] is True
