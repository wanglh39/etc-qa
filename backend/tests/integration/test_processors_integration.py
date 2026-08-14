from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestL3ProcessorsWithLLM:
    def test_standardize_oral_question(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(raw_question="鎴戞兂闂竴涓婨TC鎵ｈ垂鎵ｅ浜嗘€庝箞鍔炲晩锛屼笂涓湀鍦ㄩ珮閫熷彛琚鎵ｄ簡")
        result = standardize_query(state)
        assert "question" in result
        assert result["question"] != ""
        assert "ETC" in result["question"] or "etc" in result["question"].lower()

    def test_standardize_already_standard(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(raw_question="ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊")
        result = standardize_query(state)
        assert "ETC" in result["question"]
        assert "鎵ｈ垂寮傚父" in result["question"]

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
            raw_question="瀹㈡埛鎵撶數璇濇潵璇翠粬涓婁釜鏈堝湪鍚屼竴涓珮閫熷嚭鍙ｈETC鎵ｄ簡涓ゆ璐规兂鐭ラ亾杩欎釜澶氭墸鐨勯挶浠€涔堟椂鍊欒兘閫€鍥炴潵鍟?
        )
        result = standardize_query(state)
        assert "question" in result
        assert result["question"] != ""
        assert len(result["question"]) < len(state.raw_question)
        assert result["current_step"] == "standardize_query"

    def test_standardize_no_brand_keyword(self):
        from agent.processors.standardize_query import standardize_query
        from agent.state import AgentState

        state = AgentState(
            raw_question="鎴戞兂闂竴涓嬮噸澶嶆墸璐逛簡鎬庝箞鐢宠閫€娆惧晩杩欎釜閽辫兘閫€鍥炴潵鍚?
        )
        result = standardize_query(state)
        assert "question" in result
        assert result["current_step"] == "standardize_query"

    def test_structure_ingest_normal(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="ETC閲嶅鎵ｈ垂鎬庝箞閫€娆?,
            raw_answer="鏍稿疄鎵ｈ垂璁板綍鍚?涓伐浣滄棩閫€娆惧埌鍘熸敮浠樿处鎴?,
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
            raw_question="鎴戜笂涓湀鍦ㄥ悓涓€涓珮閫熷彛琚墸浜嗕袱娆¤垂鎬庝箞鍔炲晩锛屽鎵ｇ殑閭ｆ鑳介€€鍚?,
            raw_answer="缁忔牳瀹炵‘灞為噸澶嶆墸璐癸紝灏嗗湪3涓伐浣滄棩鍐呭皢澶氭墸娆鹃」閫€鍥炲師鏀粯璐︽埛锛岃鍏虫敞璐︽埛鍙樺姩",
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "category_l1" in result

    def test_structure_ingest_with_context(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="ETC璁惧OBU鏄剧ず寮傚父",
            raw_answer="鏇存崲OBU璁惧锛岃垂鐢?0鍏?,
            work_order_context="娴佽浆鑷宠澶囪繍缁撮儴澶勭悊",
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "internal_process" in result or "feedback_dept" in result

    def test_structure_ingest_ambiguous(self):
        from agent.processors.structure_ingest import invalidate_category_cache, structure_ingest
        from agent.state import AgentState

        invalidate_category_cache()
        state = AgentState(
            raw_question="杩欎釜涓嶇煡閬撴€庝箞寮?,
            raw_answer="宸插鐞?,
        )
        result = structure_ingest(state)
        assert "question" in result
        assert "category_l1" in result

    def test_hyde_rewrite_long_question_triggers_llm(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(
            raw_question="瀹㈡埛鎵撶數璇濇潵璇翠粬涓婁釜鏈堝湪鍚屼竴涓珮閫熷嚭鍙ｈETC鎵ｄ簡涓ゆ璐规兂鐭ラ亾杩欎釜澶氭墸鐨勯挶浠€涔堟椂鍊欒兘閫€鍥炴潵鍟?,
            raw_answer="鏍稿疄鎵ｈ垂璁板綍鍚?涓伐浣滄棩閫€娆惧埌鍘熸敮浠樿处鎴凤紝濡傞渶甯姪璇锋嫧鎵?5022",
        )
        result = hyde_rewrite(state)
        assert "hyde_questions" in result
        assert result["current_step"] == "hyde_rewrite"

    def test_hyde_rewrite_standard_question_skips(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(
            raw_question="ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊",
            raw_answer="璇锋鏌ユ墸璐硅褰曪紝濡傜‘璁ゅ紓甯稿彲鐢宠閫€娆?,
        )
        result = hyde_rewrite(state)
        assert "hyde_questions" in result
        assert result["current_step"] == "hyde_rewrite"

    def test_hyde_rewrite_no_answer(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(raw_question="ETC鎵ｈ垂寮傚父", raw_answer="")
        result = hyde_rewrite(state)
        assert result["hyde_questions"] == []

    def test_hyde_rewrite_no_brand_keyword(self):
        from agent.processors.hyde_rewrite import hyde_rewrite
        from agent.state import AgentState

        state = AgentState(
            raw_question="閲嶅鎵ｈ垂浜嗘€庝箞鐢宠閫€娆捐繖涓挶鑳介€€鍥炴潵鍚椾粈涔堟椂鍊欏埌璐﹀憿",
            raw_answer="鏍稿疄鍚?涓伐浣滄棩閫€娆惧埌鍘熸敮浠樿处鎴?,
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

        hallucination, lost = _validate_rewrite("ETC鎵ｈ垂寮傚父", "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊")
        assert isinstance(hallucination, list)
        assert isinstance(lost, list)

    def test_apply_confidence_action(self):
        from agent.processors.structure_ingest import _apply_confidence_action

        l1, l2, needs = _apply_confidence_action(0.9, "鍞悗涓氬姟", "鎵ｈ垂寮傚父", "鍞悗涓氬姟", "鎵ｈ垂寮傚父", [])
        assert needs is False

        l1, l2, needs = _apply_confidence_action(0.6, "鍞悗涓氬姟", "鎵ｈ垂寮傚父", "鍞悗涓氬姟", "鎵ｈ垂寮傚父", [])
        assert needs is True

        l1, l2, needs = _apply_confidence_action(0.2, "鍞悗涓氬姟", "鎵ｈ垂寮傚父", "鍞悗涓氬姟", "鎵ｈ垂寮傚父", [])
        assert needs is True
        assert l1 == "鍞悗涓氬姟"

    def test_apply_confidence_action_highlight(self):
        from agent.processors.structure_ingest import _apply_confidence_action

        highlights = []
        l1, l2, needs = _apply_confidence_action(0.35, "鍞悗涓氬姟", "鎵ｈ垂寮傚父", "鍞悗涓氬姟", "鎵ｈ垂寮傚父", highlights)
        assert needs is True
        assert len(highlights) > 0

    def test_category_tree_with_empty_l2(self, mysql_conn):
        from agent.processors.structure_ingest import get_category_tree, invalidate_category_cache

        qa_id = mysql_conn.insert_qa(question="闆嗘垚娴嬭瘯绌簂2鍒嗙被", answer="绛旀", category_l1="娴嬭瘯鍒嗙被L1", category_l2="")
        mysql_conn.update_qa_status(qa_id, "active")
        invalidate_category_cache()
        tree = get_category_tree()
        assert "娴嬭瘯鍒嗙被L1" in tree
        mysql_conn.delete_qa(qa_id)
        invalidate_category_cache()
        assert "娴嬭瘯鍒嗙被L1" in tree
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

        state = AgentState(raw_question="娴嬭瘯", raw_answer="绛旀")
        parsed = {
            "question": "ETC娴嬭瘯闂",
            "answer": "娴嬭瘯绛旀",
            "category_l1": "涓嶅瓨鍦ㄧ殑鍒嗙被",
            "category_l2": "涓嶅瓨鍦ㄧ殑瀛愬垎绫?,
            "category_confidence": 0.8,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "娴嬭瘯", "绛旀", tree, default_l1, default_l2, state)
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

        state = AgentState(raw_question="ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊", raw_answer="绛旀")
        parsed = {
            "question": "E",
            "answer": "娴嬭瘯绛旀",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊", "绛旀", tree, default_l1, default_l2, state)
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

        state = AgentState(raw_question="ETC鎵ｈ垂寮傚父", raw_answer="绛旀")
        parsed = {
            "question": "淇＄敤鍗＄洍鍒锋€庝箞澶勭悊",
            "answer": "娴嬭瘯绛旀",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC鎵ｈ垂寮傚父", "绛旀", tree, default_l1, default_l2, state)
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
        result = _parse_json('{"question": "ETC鎵ｈ垂", "category_l1": "鍞悗"}')
        assert result is not None
        assert result["question"] == "ETC鎵ｈ垂"

    def test_parse_json_standardize(self):
        from agent.processors.standardize_query import _parse_json
        result = _parse_json('{"need_rewrite": true, "rewritten": "ETC閫€娆?}')
        assert result is not None

    def test_preserves_keywords(self):
        from agent.processors.standardize_query import _preserves_keywords
        assert _preserves_keywords("ETC鎵ｈ垂寮傚父", "ETC鎵ｈ垂寮傚父鎬庝箞澶勭悊") is True
        assert _preserves_keywords("ETC鎵ｈ垂寮傚父", "鎵ｈ垂寮傚父鎬庝箞澶勭悊") is False

    def test_parse_json_nested_failure(self):
        from agent.processors.structure_ingest import _parse_json
        result = _parse_json('{invalid json content}')
        assert result is None

    def test_parse_json_standardize_fallback(self):
        from agent.processors.standardize_query import _parse_json
        result = _parse_json('text {"bad": } json')
        assert result is None

    def test_parse_json_hyde_nested_failure(self):
        from agent.processors.hyde_rewrite import _parse_json
        result = _parse_json('{broken')
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

        state = AgentState(raw_question="ETC鎵ｈ垂寮傚父", raw_answer="绛旀")
        parsed = {
            "question": "鎵ｈ垂寮傚父鎬庝箞澶勭悊",
            "answer": "娴嬭瘯绛旀",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC鎵ｈ垂寮傚父", "绛旀", tree, default_l1, default_l2, state)
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

        state = AgentState(raw_question="ETC娴嬭瘯", raw_answer="绛旀")
        parsed = {
            "question": "ETC娴嬭瘯闂",
            "answer": "娴嬭瘯绛旀",
            "category_l1": default_l1,
            "category_l2": default_l2,
            "category_confidence": "not_a_number",
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC娴嬭瘯", "绛旀", tree, default_l1, default_l2, state)
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

        state = AgentState(raw_question="ETC娴嬭瘯", raw_answer="绛旀")
        parsed = {
            "question": "ETC娴嬭瘯闂",
            "answer": "娴嬭瘯绛旀",
            "category_l1": default_l1,
            "category_l2": "涓嶅瓨鍦ㄧ殑瀛愬垎绫?,
            "category_confidence": 0.9,
            "internal_process": "",
            "feedback_dept": "",
        }
        result = _process_parsed_result(parsed, "ETC娴嬭瘯", "绛旀", tree, default_l1, default_l2, state)
        assert "category_l2" in result


@pytest.mark.integration
class TestL2StructureIngestStructuredResult:
    def test_process_structured_result_invalid_l1(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC璁惧鏁呴殰",
            answer="璇锋鏌BU璁惧",
            category_l1="涓嶅瓨鍦ㄧ殑鍒嗙被",
            category_l2="瀛愬垎绫?,
            category_confidence=0.8,
            internal_process="妫€鏌ヨ澶?,
            feedback_dept="杩愮淮閮?,
        )
        state = AgentState(raw_question="ETC璁惧鏁呴殰", raw_answer="璇锋鏌BU璁惧")
        tree = {"鍞悗涓氬姟": ["璁惧寮傚父", "璐﹀崟闂"]}
        result = _process_structured_result(mock_result, "ETC璁惧鏁呴殰", "璇锋鏌BU璁惧", tree, "鍞悗涓氬姟", "璁惧寮傚父", state)
        assert result["category_l1"] == "鍞悗涓氬姟"
        assert result["category_l2"] == "璁惧寮傚父"

    def test_process_structured_result_invalid_l2(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC鎵ｈ垂寮傚父",
            answer="璇锋煡鐪嬭处鍗?,
            category_l1="鍞悗涓氬姟",
            category_l2="涓嶅瓨鍦ㄧ殑瀛愬垎绫?,
            category_confidence=0.8,
            internal_process="鏌ョ湅璐﹀崟",
            feedback_dept="瀹㈡湇閮?,
        )
        state = AgentState(raw_question="ETC鎵ｈ垂寮傚父", raw_answer="璇锋煡鐪嬭处鍗?)
        tree = {"鍞悗涓氬姟": ["璁惧寮傚父", "璐﹀崟闂"]}
        result = _process_structured_result(mock_result, "ETC鎵ｈ垂寮傚父", "璇锋煡鐪嬭处鍗?, tree, "鍞悗涓氬姟", "璁惧寮傚父", state)
        assert result["category_l1"] == "鍞悗涓氬姟"
        assert result["category_l2"] == "璁惧寮傚父"

    def test_process_structured_result_hallucination(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC璁惧鏁呴殰閾惰鍗￠€€娆?,
            answer="璇锋鏌BU璁惧",
            category_l1="鍞悗涓氬姟",
            category_l2="璁惧寮傚父",
            category_confidence=0.8,
            internal_process="妫€鏌ヨ澶?,
            feedback_dept="杩愮淮閮?,
        )
        state = AgentState(raw_question="ETC璁惧鏁呴殰", raw_answer="璇锋鏌BU璁惧")
        tree = {"鍞悗涓氬姟": ["璁惧寮傚父"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["閾惰鍗?, "閫€娆?], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC璁惧鏁呴殰", "璇锋鏌BU璁惧", tree, "鍞悗涓氬姟", "璁惧寮傚父", state)
        assert result["question"] == "ETC璁惧鏁呴殰"
        assert result["needs_review"] is True

    def test_process_structured_result_lost_keywords(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="璁惧鏁呴殰",
            answer="璇锋鏌BU璁惧",
            category_l1="鍞悗涓氬姟",
            category_l2="璁惧寮傚父",
            category_confidence=0.8,
            internal_process="妫€鏌ヨ澶?,
            feedback_dept="杩愮淮閮?,
        )
        state = AgentState(raw_question="ETC璁惧鏁呴殰", raw_answer="璇锋鏌BU璁惧")
        tree = {"鍞悗涓氬姟": ["璁惧寮傚父"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["閾惰鍗?], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC璁惧鏁呴殰", "璇锋鏌BU璁惧", tree, "鍞悗涓氬姟", "璁惧寮傚父", state)
        assert result["needs_review"] is True

    def test_process_structured_result_short_rewrite(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="E",
            answer="璇锋鏌BU璁惧",
            category_l1="鍞悗涓氬姟",
            category_l2="璁惧寮傚父",
            category_confidence=0.8,
            internal_process="妫€鏌ヨ澶?,
            feedback_dept="杩愮淮閮?,
        )
        state = AgentState(raw_question="ETC璁惧鏁呴殰", raw_answer="璇锋鏌BU璁惧")
        tree = {"鍞悗涓氬姟": ["璁惧寮傚父"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["閾惰鍗?], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC璁惧鏁呴殰", "璇锋鏌BU璁惧", tree, "鍞悗涓氬姟", "璁惧寮傚父", state)
        assert result["question"] == "ETC璁惧鏁呴殰"
        assert result["needs_review"] is True

    def test_process_structured_result_low_confidence(self):
        from agent.output_schemas import StructureIngestOutput
        from agent.processors.structure_ingest import _process_structured_result
        from agent.state import AgentState

        mock_result = StructureIngestOutput(
            question="ETC璁惧鏁呴殰",
            answer="璇锋鏌BU璁惧",
            category_l1="鍞悗涓氬姟",
            category_l2="璁惧寮傚父",
            category_confidence=0.2,
            internal_process="妫€鏌ヨ澶?,
            feedback_dept="杩愮淮閮?,
        )
        state = AgentState(raw_question="ETC璁惧鏁呴殰", raw_answer="璇锋鏌BU璁惧")
        tree = {"鍞悗涓氬姟": ["璁惧寮傚父"]}
        with patch('agent.processors.structure_ingest._get_kw_lists', return_value=(["閾惰鍗?], ["ETC"])):
            result = _process_structured_result(mock_result, "ETC璁惧鏁呴殰", "璇锋鏌BU璁惧", tree, "鍞悗涓氬姟", "璁惧寮傚父", state)
        assert result["needs_review"] is True