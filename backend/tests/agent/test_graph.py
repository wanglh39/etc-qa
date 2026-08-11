import json
from unittest.mock import MagicMock, patch

from agent.graph import build_ingest_graph, build_preprocess_graph
from agent.state import AgentState


class TestPreprocessAgent:
    def test_full_preprocess_pipeline(self):
        graph = build_preprocess_graph()
        state = AgentState(raw_question="我ETC扣费扣多了怎么办啊")

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="ETC扣费异常如何处理")

        with patch("agent.processors.standardize_query.get_llm", return_value=mock_llm):
            result = graph.invoke(state.model_dump())
            assert "ETC" in result["question"]
            assert result["current_step"] == "standardize_query"

    def test_preprocess_preserves_core_info(self):
        graph = build_preprocess_graph()
        state = AgentState(raw_question="ETC黑名单怎么解除")

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="ETC黑名单如何解除")

        with patch("agent.processors.standardize_query.get_llm", return_value=mock_llm):
            result = graph.invoke(state.model_dump())
            assert "黑名单" in result["question"]


class TestIngestAgent:
    def test_full_ingest_pipeline(self):
        graph = build_ingest_graph()
        state = AgentState(
            raw_question="我ETC卡扣费扣多了就是上个月跑高速扣了两次钱",
            raw_answer="核实后退款3个工作日到账",
        )

        llm_json = json.dumps({
            "question": "ETC重复扣费如何处理",
            "answer": "核实后退款3个工作日到账",
            "category_l1": "售后业务",
            "category_l2": "账单类",
            "internal_process": "核实扣费记录并处理退款",
            "feedback_dept": "账单组",
        })
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=llm_json)

        with patch("agent.processors.structure_ingest.get_llm", return_value=mock_llm), \
             patch("agent.processors.hyde_rewrite.get_llm", return_value=mock_llm):
            result = graph.invoke(state.model_dump())
            assert result["question"] == "ETC重复扣费如何处理"
            assert result["category_l1"] == "售后业务"
