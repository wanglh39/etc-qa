from models.schemas import AgentProcessRequest, CandidateResult, QueryRequest, QueryResponse


class TestQueryRequest:
    def test_required_field(self):
        req = QueryRequest(question="ETC扣费异常")
        assert req.question == "ETC扣费异常"
        assert req.category_l1 is None

    def test_optional_category(self):
        req = QueryRequest(question="ETC扣费异常", category_l1="账单问题")
        assert req.category_l1 == "账单问题"


class TestQueryResponse:
    def test_response_fields(self):
        resp = QueryResponse(
            query="ETC扣费异常",
            standardized_query="ETC扣费异常如何处理",
            confidence="high",
            candidates=[],
            total_candidates=0,
        )
        assert resp.standardized_query == "ETC扣费异常如何处理"
        assert resp.confidence == "high"


class TestAgentProcessRequest:
    def test_required_and_optional(self):
        req = AgentProcessRequest(question="ETC扣费异常")
        assert req.question == "ETC扣费异常"
        assert req.answer == ""
        assert req.context == ""

    def test_all_fields(self):
        req = AgentProcessRequest(
            question="ETC扣费异常",
            answer="核实后退款",
            context="用户来电咨询",
            user_id="user001",
        )
        assert req.answer == "核实后退款"
        assert req.user_id == "user001"


class TestCandidateResult:
    def test_candidate_fields(self):
        c = CandidateResult(
            qa_id=1,
            question="ETC扣费异常",
            answer="核实后退款",
            score=0.95,
        )
        assert c.qa_id == 1
        assert c.score == 0.95
        assert c.category_l1 is None
